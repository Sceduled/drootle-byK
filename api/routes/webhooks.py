"""
API routes for handling webhooks (e.g. from Make.com, WhatsApp, Voice Providers).
"""
from fastapi import APIRouter, Header, HTTPException, Depends, Request, Response, Query
from pydantic import BaseModel
from typing import Optional
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from arq import create_pool
from arq.connections import RedisSettings
import hmac
import hashlib

from core.config import settings
from core.database import get_db
from core.models import Lead, Conversation
from core.redis import get_redis
from utils.phone import normalize_phone
from services.gpt import call_gpt_mini
from services.admin_reporter import push_event
from utils.project_matcher import match_project
from services.notifications import notify_sales_unmatched_project

router = APIRouter()
logger = logging.getLogger(__name__)

class NewLeadPayload(BaseModel):
    name: Optional[str] = None
    phone: str
    email: Optional[str] = None
    company: Optional[str] = None
    source_ad: Optional[str] = None
    sheet_row: Optional[int] = None

_arq_pool = None

async def get_arq_pool():
    global _arq_pool
    if _arq_pool is None:
        _arq_pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    return _arq_pool

from core.limiter import limiter

@router.post("/new-lead")
@limiter.limit("100/minute")
async def new_lead(
    request: Request,
    payload: NewLeadPayload,
    x_webhook_secret: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    if not x_webhook_secret or x_webhook_secret != settings.WEBHOOK_SECRET:
        logger.warning("Unauthorized webhook access attempt")
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        norm_phone = normalize_phone(payload.phone)
    except ValueError as e:
        logger.warning(f"Invalid phone number '{payload.phone}': {e}")
        raise HTTPException(status_code=400, detail="Invalid phone number")

    result = await db.execute(select(Lead).where(Lead.phone == norm_phone))
    lead = result.scalars().first()

    is_new = False
    if lead:
        logger.info(f"Existing lead found, resuming. lead_id: {lead.id}")
    else:
        is_new = True
        
        project_key = await match_project(payload.source_ad, db)
        needs_assignment = project_key == "unknown"

        lead = Lead(
            name=payload.name,
            phone=norm_phone,
            email=payload.email,
            company_name=payload.company,
            source_ad=payload.source_ad,
            sheet_row_index=payload.sheet_row,
            project_key=project_key if not needs_assignment else None,
            needs_project_assignment=needs_assignment
        )
        db.add(lead)
        await db.commit()
        await db.refresh(lead)

        alert_msg = "⚠ Could not auto-match project for this lead — please assign manually in dashboard." if needs_assignment else None

        await push_event("lead_created", str(lead.id), {
            "source": "webhook", 
            "needs_project_assignment": needs_assignment,
            "alert": alert_msg
        })
        
        if needs_assignment:
            await notify_sales_unmatched_project(lead)

        logger.info(f"New lead created. lead_id: {lead.id}")

    if is_new:
        try:
            arq_pool = await get_arq_pool()
            from workers.tasks import is_within_calling_hours
            from datetime import datetime, timedelta
            import zoneinfo
            
            if is_within_calling_hours():
                await arq_pool.enqueue_job(
                    "fire_outbound_call",
                    str(lead.id),
                    _job_id=f"call_{lead.id}"
                )
            else:
                ist = zoneinfo.ZoneInfo("Asia/Kolkata")
                now = datetime.now(ist)
                tomorrow_7am = (now + timedelta(days=1)).replace(
                    hour=7, minute=0, second=0, microsecond=0
                )
                delay = tomorrow_7am - now
                await arq_pool.enqueue_job(
                    "fire_outbound_call",
                    str(lead.id),
                    _defer_by=delay,
                    _job_id=f"call_{lead.id}"
                )
        except Exception as e:
            logger.error(f"Failed to enqueue ARQ job for lead_id: {lead.id}. Error: {e}")

    return {"status": "received", "lead_id": str(lead.id)}


@router.post("/bolna-call-outcome")
async def receive_bolna_outcome(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    signature = request.headers.get("X-Bolna-Signature", "")
    body = await request.body()

    # Allow bypass when no secret configured (local dev / testing)
    if settings.BOLNA_WEBHOOK_SECRET:
        # Strip sha256= prefix if Bolna sends it
        if signature.startswith("sha256="):
            signature = signature[7:]

        if not signature:
            raise HTTPException(status_code=401, detail="Missing signature")

        expected_sig = hmac.new(
            settings.BOLNA_WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature.lower(), expected_sig.lower()):
            logger.warning("Invalid Bolna webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
    else:
        logger.warning("BOLNA_WEBHOOK_SECRET not set — skipping signature verification")

    payload = await request.json()
    call_id = payload.get("call_id")
    status = payload.get("status")
    duration = payload.get("duration_seconds", 0)
    user_data = payload.get("user_data", {})
    lead_id = user_data.get("lead_id")
    transcript = payload.get("transcript", "")
    
    if not lead_id:
        return {"status": "ignored", "reason": "no lead_id"}
        
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalars().first()
    if not lead:
        return {"status": "ignored", "reason": "lead not found"}
        
    arq_pool = await get_arq_pool()

    # Always store duration
    if duration:
        lead.call_duration_seconds = int(duration)

    if status in ("no-answer", "busy", "failed"):
        lead.call_outcome = "no_pickup"
        lead.conv_status = "call_attempted"
        await db.commit()
        await arq_pool.enqueue_job("send_no_pickup_whatsapp", lead_id)

    elif status == "completed":
        if duration < 30:
            lead.call_outcome = "dropped_early"
            lead.conv_status = "qualifying"
            await db.commit()
            await arq_pool.enqueue_job("send_dropped_call_whatsapp", lead_id)
        else:
            # Extract qualification data from transcript
            from services.gpt import extract_call_transcript_data
            from services.notifications import notify_sales_qualification

            extracted = await extract_call_transcript_data(transcript)
            lead.call_partial_data = extracted

            # Check if fully qualified (all 5 fields present)
            is_qualified = bool(
                extracted.get("location") and
                extracted.get("budget") and
                extracted.get("bhk") and
                extracted.get("timeline") and
                extracted.get("purpose")
            )

            if is_qualified:
                lead.call_outcome = "qualified"
                lead.call_qualified = True
                lead.conv_status = "awaiting_call"
                await db.commit()
                await notify_sales_qualification(lead)
            else:
                lead.call_outcome = "partial"
                lead.conv_status = "qualifying"
                await db.commit()
                await arq_pool.enqueue_job("send_partial_call_whatsapp", lead_id)

    return {"status": "processed"}


@router.get("/whatsapp")
async def verify_whatsapp(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge")
):
    if hub_mode == "subscribe" and hub_verify_token == settings.META_WEBHOOK_VERIFY_TOKEN:
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")

@router.post("/whatsapp")
async def receive_whatsapp(request: Request, db: AsyncSession = Depends(get_db)):
    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        raise HTTPException(status_code=403, detail="Missing signature")
        
    body = await request.body()
    expected_sig = hmac.new(
        settings.META_APP_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    received_sig = signature.replace("sha256=", "")
    if not hmac.compare_digest(expected_sig, received_sig):
        logger.warning("Invalid Meta webhook signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload = await request.json()
    try:
        entry = payload.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])
        
        if not messages:
            return {"status": "ok"}
            
        message = messages[0]
        phone = message.get("from")
        text_body = message.get("text", {}).get("body", "")
        
        if phone and text_body:
            await handle_inbound_message(phone, text_body, db)
    except Exception as e:
        logger.error(f"Error processing Meta webhook: {e}")
        
    return {"status": "ok"}

import asyncio
from fastapi import BackgroundTasks
from core.database import AsyncSessionLocal
from services.gpt import process_message
from services.whatsapp import send_message as wa_send

async def process_waha_message(payload: dict):
    try:
        logger.info(f"Processing WAHA payload: {payload}")

        # Parse phone + text from WAHA's various event formats
        phone = payload.get("from") or payload.get("sender")
        if not phone and "payload" in payload:
            phone = payload["payload"].get("from")

        original_jid = phone

        # WAHA NOWEB sometimes uses @lid, the real phone is in remoteJidAlt
        if "payload" in payload:
            alt_phone = payload["payload"].get("_data", {}).get("key", {}).get("remoteJidAlt")
            if alt_phone:
                phone = alt_phone

        message_text = payload.get("body") or payload.get("text", "")
        if not message_text and "payload" in payload:
            message_text = payload["payload"].get("body", "")

        # Skip if this is an outgoing (fromMe) message
        if payload.get("fromMe") or (payload.get("payload") or {}).get("fromMe"):
            logger.info("Skipping outgoing (fromMe) message")
            return

        if phone and isinstance(phone, str) and '@' in phone:
            phone = phone.split('@')[0]

        msg_type = payload.get("type")
        if not msg_type and "payload" in payload:
            msg_type = payload["payload"].get("type")

        if not phone:
            logger.warning("Missing phone")
            return

        if not message_text:
            message_text = "[System Note: The user sent a media attachment, location pin, or an empty message. You cannot view or listen to it. Please politely inform them that you are a text-only AI and ask them to type out their message.]"

        logger.info(f"Inbound from {phone} (JID: {original_jid}): {message_text!r}")
        await handle_inbound_message(phone, message_text, reply_to_jid=original_jid)

    except Exception as e:
        logger.error(f"Error processing WAHA message: {e}", exc_info=True)
        raise

last_payloads = []

@router.post("/waha")
async def waha_webhook(request: Request):
    global last_payloads
    try:
        payload = await request.json()
        logger.info(f"WAHA webhook received: {payload}")
        last_payloads.insert(0, payload)
        if len(last_payloads) > 10:
            last_payloads.pop()
            
        await process_waha_message(payload)
        return {"status": "ok", "message": "processed"}
    except Exception as e:
        logger.error(f"WAHA webhook error: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}

@router.get("/waha/debug")
async def debug_waha():
    return {"last_payloads": last_payloads}


async def handle_inbound_message(phone: str, message_text: str, reply_to_jid: str = None):
    """Process inbound message directly — no ARQ worker needed."""
    try:
        norm_phone = normalize_phone(phone)
    except ValueError as e:
        logger.warning(f"Invalid inbound phone {phone}: {e}")
        return

    redis = get_redis()
    buffer_key = f"buffer:{norm_phone}"
    processing_key = f"processing:{norm_phone}"

    # Push to buffer
    await redis.rpush(buffer_key, message_text)
    await redis.expire(buffer_key, 10)

    # Acquire processing lock atomically
    # If the key already exists (nx=True fails), another request is processing
    acquired = await redis.set(processing_key, "1", ex=30, nx=True)
    if not acquired:
        logger.info(f"Already processing {norm_phone}, buffered message")
        return

    try:
        # Wait for rapid-fire messages to accumulate
        await asyncio.sleep(4)

        # Drain buffer
        messages = await redis.lrange(buffer_key, 0, -1)
        await redis.delete(buffer_key)

        if not messages:
            return

        # Deduplicate identical consecutive messages (caused by WAHA duplicate webhooks)
        unique_messages = []
        for m in messages:
            decoded = m if isinstance(m, str) else m.decode()
            if not unique_messages or unique_messages[-1] != decoded:
                unique_messages.append(decoded)

        combined = "\n".join(unique_messages)
        logger.info(f"Processing {len(unique_messages)} unique buffered message(s) for {norm_phone}: {combined!r}")

        async with AsyncSessionLocal() as db:
            # Find or create lead
            result = await db.execute(select(Lead).where(Lead.phone == norm_phone))
            lead = result.scalars().first()

            if not lead:
                logger.info(f"Unknown inbound number {norm_phone}, ignoring.")
                return

            if combined.strip().lower() in ["stop", "stop.", "unsubscribe"]:
                logger.info(f"[{lead.id}] User requested opt-out.")
                from utils.stage_logger import log_stage_change
                old_status = lead.conv_status
                lead.conv_status = "lost"
                await log_stage_change(str(lead.id), old_status, "lost", "system", "User opted out (STOP)", db)
                await db.commit()
                target_jid = reply_to_jid or norm_phone
                await wa_send(target_jid, "You have been unsubscribed. You will not receive any further messages.")
                return

            # Fetch history
            result = await db.execute(
                select(Conversation)
                .where(Conversation.lead_id == lead.id)
                .order_by(Conversation.created_at.asc())
            )
            history = result.scalars().all()

            # Mark sequence metrics
            from core.models import NotificationLog
            last_notification = await db.execute(
                select(NotificationLog)
                .where(NotificationLog.lead_id == lead.id)
                .where(NotificationLog.sequence_step.is_not(None))
                .order_by(NotificationLog.sent_at.desc())
                .limit(1)
            )
            last_notif = last_notification.scalars().first()
            if last_notif and not last_notif.replied:
                last_notif.replied = True

            # GPT reply
            reply, extraction = await process_message(lead, db, history, combined)
            logger.info(f"[{lead.id}] GPT reply: {reply!r}")

            # Persist conversation
            db.add(Conversation(lead_id=lead.id, role="user", content=combined))
            db.add(Conversation(lead_id=lead.id, role="assistant", content=reply))

            # Update lead fields
            for field in ['industry','target_markets','monthly_ad_budget','ads_experience','pain_point','urgency','preferred_call_time','lead_score']:
                val = extraction.get(field)
                if val is not None:
                    setattr(lead, field, val)

            new_status = extraction.get('conv_status')
            
            # Qualification completion check
            qual_fields = [
                lead.industry, lead.target_markets, lead.monthly_ad_budget, 
                lead.ads_experience, lead.pain_point, lead.urgency, lead.preferred_call_time
            ]
            just_qualified = False
            if all(f is not None for f in qual_fields) and lead.conv_status in ["qualifying", "in_progress"]:
                new_status = "awaiting_call"
                just_qualified = True
                
            from utils.stage_logger import log_stage_change
            if just_qualified:
                old_status = lead.conv_status
                lead.conv_status = "awaiting_call"
                await log_stage_change(str(lead.id), old_status, "awaiting_call", "ai", "All qualification fields present", db)
            elif new_status and new_status != lead.conv_status:
                prevent_downgrade = lead.conv_status in ["awaiting_call", "post_call", "closed", "upsell", "lost"] and new_status in ["qualifying", "in_progress", "stalled", "new", "cold"]
                if not prevent_downgrade:
                    old_status = lead.conv_status
                    lead.conv_status = new_status
                    await log_stage_change(str(lead.id), old_status, new_status, "ai", "Status updated by extraction", db)

            await db.commit()

        # Send reply via WhatsApp
        target_jid = reply_to_jid or norm_phone
        success = await wa_send(target_jid, reply)
        logger.info(f"[{lead.id}] Reply sent: {success}")
        
        arq_pool = await get_arq_pool()
        if just_qualified:
            await arq_pool.enqueue_job('post_qualification_actions', str(lead.id))
            await arq_pool.enqueue_job('generate_lead_summary', str(lead.id))
        elif new_status == "qualified" and lead.conv_status == "qualified":
            await arq_pool.enqueue_job('post_qualification_actions', str(lead.id))
        elif new_status == "escalate" and lead.conv_status == "escalate":
            await arq_pool.enqueue_job('escalate_to_sales', str(lead.id))

    except Exception as e:
        logger.error(f"Error in handle_inbound_message for {norm_phone}: {e}", exc_info=True)
    finally:
        await redis.delete(processing_key)

# --- VOICE WEBHOOKS ---

class VoiceCallbackPayload(BaseModel):
    call_id: Optional[str] = None
    phone: str
    transcript: str
    duration: Optional[int] = None
    duration_seconds: Optional[int] = None
    extracted_data: Optional[dict] = None

@router.post("/bolna")
async def bolna_callback(payload: VoiceCallbackPayload, db: AsyncSession = Depends(get_db)):
    await handle_voice_callback(payload, db)
    return {"status": "ok"}

@router.post("/pipecat")
async def pipecat_callback(payload: VoiceCallbackPayload, db: AsyncSession = Depends(get_db)):
    await handle_voice_callback(payload, db)
    return {"status": "ok"}

async def handle_voice_callback(payload: VoiceCallbackPayload, db: AsyncSession):
    try:
        norm_phone = normalize_phone(payload.phone)
    except ValueError:
        return
        
    result = await db.execute(select(Lead).where(Lead.phone == norm_phone))
    lead = result.scalars().first()
    if not lead: return
    
    transcript_msg = f"[VOICE CALL TRANSCRIPT]\n{payload.transcript}"
    db.add(Conversation(lead_id=lead.id, role="system", content=transcript_msg))
    await db.commit()
    
    result = await db.execute(
        select(Conversation)
        .where(Conversation.lead_id == lead.id)
        .order_by(Conversation.created_at.asc())
    )
    history = result.scalars().all()
    
    from services.gpt import process_message
    _, extraction = await process_message(lead, db, history, "", is_voice=True)
    
    if extraction.get('industry') is not None: lead.industry = extraction['industry']
    if extraction.get('target_markets') is not None: lead.target_markets = extraction['target_markets']
    if extraction.get('monthly_ad_budget') is not None: lead.monthly_ad_budget = extraction['monthly_ad_budget']
    if extraction.get('ads_experience') is not None: lead.ads_experience = extraction['ads_experience']
    if extraction.get('pain_point') is not None: lead.pain_point = extraction['pain_point']
    if extraction.get('urgency') is not None: lead.urgency = extraction['urgency']
    if extraction.get('preferred_call_time') is not None: lead.preferred_call_time = extraction['preferred_call_time']
    if extraction.get('lead_score') is not None: lead.lead_score = extraction['lead_score']
    
    new_status = extraction.get('conv_status')
    if new_status:
        if lead.conv_status not in ["qualified", "closed"]:
            lead.conv_status = new_status
            
    await db.commit()
    
    arq_pool = await get_arq_pool()
    if new_status == "qualified" and lead.conv_status == "qualified":
        await arq_pool.enqueue_job('post_qualification_actions', str(lead.id))
    elif new_status == "escalate" and lead.conv_status == "escalate":
        await arq_pool.enqueue_job('escalate_to_sales', str(lead.id))
