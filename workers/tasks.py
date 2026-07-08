"""
Background tasks (e.g. using arq) for async processing.
"""
import logging
import asyncio
import functools
import traceback
from datetime import datetime, timedelta, timezone
from client_config import SEQUENCE_MESSAGES
from arq.connections import RedisSettings
from arq.cron import cron
from sqlalchemy import select, text
from sqlalchemy.sql import func
import httpx
import zoneinfo

from core.config import settings
from core.database import AsyncSessionLocal
from core.models import Lead, Conversation, NotificationLog, SequenceTiming, CampaignContext
from core.job_guard import can_send_message
from prompts.agent import get_sequence_message
from services.whatsapp import send_message
from services.gpt import process_message, call_gpt_mini, generate_summary_from_history_text
from services.sheets import update_lead_row
from services.notifications import notify_sales_qualification, notify_sales_stalled, notify_sales_escalation, notify_sales_opt_out, notify_close_intent, notify_cold_reengaged, notify_archived_reengaged
from utils.job_guard import can_send_message
from utils.stage_logger import log_stage_change
from services.bolna import trigger_outbound_call as _trigger_outbound_bolna
from services.pipecat_client import trigger_pipecat_call as _trigger_pipecat_call

logger = logging.getLogger(__name__)

async def get_sequence_timing(sequence_number: int, db) -> dict:
    """Fetch timing config for a sequence from DB. Returns dict keyed by message_key."""
    result = await db.execute(
        select(SequenceTiming).where(SequenceTiming.sequence_number == sequence_number)
    )
    rows = result.scalars().all()
    return {
        row.message_key: {"value": row.delay_value, "unit": row.delay_unit}
        for row in rows
    }

async def get_campaign_context_dict(db, project_key=None) -> dict:
    """Fetch campaign context from DB. Returns dict keyed by context_key."""
    stmt = select(CampaignContext)
    if project_key:
        stmt = stmt.where(CampaignContext.project_key == project_key)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return {row.context_key: row.context_value for row in rows}

def _td(timing: dict, key: str, default_value: int, default_unit: str) -> timedelta:
    """Get a timedelta from timing dict with a hardcoded fallback."""
    if key in timing:
        t = timing[key]
        return timedelta(**{t["unit"]: t["value"]})
    return timedelta(**{default_unit: default_value})

def safe_task(func):
    @functools.wraps(func)
    async def wrapper(ctx, *args, **kwargs):
        try:
            return await func(ctx, *args, **kwargs)
        except Exception as e:
            job_try = ctx.get('job_try', 1) if ctx else 1
            if job_try < 3:
                logger.warning(f"Task {func.__name__} failed on try {job_try}. Retrying... Error: {e}")
                raise  # Re-raise to trigger ARQ retry
            else:
                logger.critical(f"Task {func.__name__} PERMANENTLY failed after 3 tries: {e}\n{traceback.format_exc()}")
                # Do NOT re-raise to prevent infinite retries by ARQ
    return wrapper


async def get_project_for_lead(lead, db):
    from core.models import Project
    if lead.project_key and lead.project_key != "unknown":
        result = await db.execute(select(Project).where(Project.project_key == lead.project_key))
        return result.scalars().first()
    return None

def is_within_calling_hours() -> bool:
    ist = zoneinfo.ZoneInfo("Asia/Kolkata")
    now = datetime.now(ist)
    return 7 <= now.hour < 22

@safe_task
async def fire_outbound_call(ctx, lead_id: str):
    logger.info(f"[{lead_id}] Starting fire_outbound_call task")
    if not settings.BOLNA_API_KEY or not settings.BOLNA_AGENT_ID:
        logger.error(f"[{lead_id}] Bolna API key or Agent ID missing. Cannot fire call.")
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        if not lead:
            return
        
        if lead.opted_out or lead.call_attempted:
            logger.info(f"[{lead_id}] Lead opted out or call already attempted. Skipping.")
            return

        # Fire Bolna call
        headers = {
            "Authorization": f"Bearer {settings.BOLNA_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "agent_id": settings.BOLNA_AGENT_ID,
            "recipient_phone_number": lead.phone,
            "user_data": {
                "lead_id": str(lead.id),
                "lead_name": lead.name or ""
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post("https://api.bolna.dev/call", json=payload, headers=headers, timeout=10.0)
                if resp.status_code not in (200, 201):
                    logger.error(f"[{lead_id}] Bolna API error: {resp.status_code} - {resp.text}")
                    return
                logger.info(f"[{lead_id}] Bolna call fired successfully: {resp.text}")
        except Exception as e:
            logger.error(f"[{lead_id}] Error calling Bolna API: {e}")
            return
        
        # Update DB
        lead.call_attempted = True
        lead.call_attempted_at = datetime.now(timezone.utc)
        lead.conv_status = "call_attempted"
        await db.commit()
        
        # Schedule check_call_outcome
        arq_pool = ctx.get('redis')
        await arq_pool.enqueue_job(
            "check_call_outcome",
            lead_id,
            _defer_by=timedelta(minutes=3),
            _job_id=f"call_check_{lead_id}"
        )

@safe_task
async def check_call_outcome(ctx, lead_id: str):
    logger.info(f"[{lead_id}] Running fallback check_call_outcome")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        if not lead:
            return
            
        if lead.call_attempted and not lead.call_outcome:
            logger.warning(f"[{lead_id}] Fallback check: call_outcome is still null. Bolna webhook may have failed or delayed.")

@safe_task
async def send_no_pickup_whatsapp(ctx, lead_id: str):
    logger.info(f"[{lead_id}] Sending no pickup whatsapp")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        if not lead:
            return

        # Guard: if lead already replied via WhatsApp, skip the no-pickup message
        existing_msgs = await db.execute(
            select(Conversation).where(
                Conversation.lead_id == lead.id,
                Conversation.role == "user"
            ).limit(1)
        )
        if existing_msgs.scalar():
            logger.info(f"[{lead_id}] Lead already has user conversation — skipping no pickup message")
            return

        name = lead.name or "there"
        msg = f"Hi {name}, I tried calling you just now but couldn't get through. I am here to ask you few questions regarding your requirement  can I take two minutes of your time?"

        success = await send_message(lead.phone, msg)
        if success:
            db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
            lead.conv_status = "qualifying"
            await db.commit()
            await log_stage_change(str(lead.id), "call_attempted", "qualifying", "system", "Sent no pickup message", db)

@safe_task
async def send_dropped_call_whatsapp(ctx, lead_id: str):
    """For calls < 30s (dropped before any real conversation)."""
    logger.info(f"[{lead_id}] Sending dropped call whatsapp")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        if not lead:
            return

        name = lead.name or "there"
        msg = f"Hi {name}, we got disconnected just now. Happy to continue here over chat whenever you're ready."

        success = await send_message(lead.phone, msg)
        if success:
            db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
            lead.conv_status = "qualifying"
            await db.commit()
            await log_stage_change(str(lead.id), "call_attempted", "qualifying", "system", "Sent dropped call message", db)

@safe_task
async def send_partial_call_whatsapp(ctx, lead_id: str):
    """For completed calls >= 30s where not all 5 fields were captured."""
    logger.info(f"[{lead_id}] Sending partial call whatsapp")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        if not lead:
            return

        name = lead.name or "there"
        msg = (
            f"Hi {name}, thanks for speaking with me earlier. "
            f"I wanted to follow up here so we can finish up — "
            f"just a couple more quick questions and I can share the full project details with you."
        )

        success = await send_message(lead.phone, msg)
        if success:
            db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
            lead.conv_status = "qualifying"
            await db.commit()
            await log_stage_change(str(lead.id), "call_attempted", "qualifying", "system", "Sent partial call follow-up message", db)

@safe_task
async def dispatch_voice_call(ctx, lead_id: str):
    if not settings.VOICE_ENABLED:
        logger.info(f"[{lead_id}] voice disabled, skipping call")
        return
        
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        if not lead: return
        
    provider = settings.VOICE_PROVIDER
    if provider == "bolna":
        await _trigger_outbound_bolna(lead)
    elif provider == "pipecat":
        await _trigger_pipecat_call(lead)
    else:
        logger.error(f"[{lead_id}] unknown voice provider: {provider}")

@safe_task
async def send_opening_message(ctx, lead_id: str):
    logger.info(f"[{lead_id}] Starting send_opening_message task")
    
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "new", 1, db)
        if not can_send:
            logger.info(f"[{lead_id}] Skipping send_opening_message: {reason}")
            return
            
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        
        if not lead:
            logger.error(f"[{lead_id}] Lead not found")
            return
            
        display_name = lead.name if lead.name else "there"
        project = await get_project_for_lead(lead, db)
        context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)
        opening_message = get_sequence_message("first_touch", project=project, name=display_name, pain_point=lead.pain_point, **context)
        
        success = await send_message(lead.phone, opening_message)
        
        if success:
            db.add(Conversation(lead_id=lead.id, role="assistant", content=opening_message))
            old_status = lead.conv_status
            lead.conv_status = "in_progress"
            await db.commit()
            await log_stage_change(lead_id, old_status, "in_progress", "system", "Opening message sent", db)
            logger.info(f"[{lead_id}] Opening message sent successfully to phone: {lead.phone}")
            # Schedule qualification nudge 24h later if lead hasn't replied
            arq_pool = ctx.get('redis')
            await arq_pool.enqueue_job(
                'send_qual_nudge', lead_id,
                _defer_by=timedelta(hours=24),
                _job_id=f"qual_nudge_{lead_id}"
            )
        else:
            logger.error(f"[{lead_id}] Failed to send opening message to phone: {lead.phone}")

@safe_task
async def send_qual_nudge(ctx, lead_id: str):
    """Sequence 2: 24h nudge if lead hasn't replied after opening message."""
    logger.info(f"[{lead_id}] Checking if qual nudge should be sent")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        if not lead:
            return

        # Only send if lead has not replied at all (still in_progress, no user messages)
        if lead.conv_status not in ("new", "in_progress"):
            logger.info(f"[{lead_id}] Skipping qual nudge: status is {lead.conv_status}")
            return

        conv_result = await db.execute(
            select(Conversation)
            .where(Conversation.lead_id == lead.id, Conversation.role == "user")
        )
        user_messages = conv_result.scalars().all()
        if user_messages:
            logger.info(f"[{lead_id}] Skipping qual nudge: lead has already replied")
            return

        if lead.opted_out:
            return

        display_name = lead.name if lead.name else "there"
        project = await get_project_for_lead(lead, db)
        context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)
        msg = get_sequence_message("qual_nudge_24h", project=project, name=display_name, pain_point=lead.pain_point, **context)
        success = await send_message(lead.phone, msg)
        if success:
            db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
            await db.commit()
            logger.info(f"[{lead_id}] Qual nudge sent")
        else:
            logger.error(f"[{lead_id}] Failed to send qual nudge")

@safe_task
async def process_buffered_message(ctx, phone: str):
    logger.info(f"Processing buffered messages for {phone}")
    from core.redis import get_redis
    redis = get_redis()
    buffer_key = f"buffer:{phone}"
    
    messages = await redis.lrange(buffer_key, 0, -1)
    await redis.delete(buffer_key)
    
    if not messages:
        await redis.delete(f"processing:{phone}")
        return
        
    combined = "\n".join(messages)
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Lead).where(Lead.phone == phone))
        lead = result.scalars().first()
        
        if not lead:
            await redis.delete(f"processing:{phone}")
            return
            
        result = await db.execute(
            select(Conversation)
            .where(Conversation.lead_id == lead.id)
            .order_by(Conversation.created_at.asc())
        )
        history = result.scalars().all()
        
        language_instruction = ""
        try:
            from langdetect import detect, DetectorFactory
            DetectorFactory.seed = 0
            
            lead_messages = [msg.content for msg in history if msg.role == 'user']
            if combined:
                lead_messages.append(combined)
                
            text_to_detect = " ".join(lead_messages[-5:])
            
            try:
                lang_code = detect(text_to_detect)
            except:
                lang_code = "en"
                
            lang_map = {
                "hi": "Hindi",
                "ta": "Tamil", 
                "kn": "Kannada",
                "te": "Telugu",
                "en": "English"
            }
            detected_lang = lang_map.get(lang_code, "English")
            
            logger.info(f"Lead messages sample: {text_to_detect[:100]}")
            logger.info(f"Detected: {lang_code} -> {detected_lang}")
            
            language_instruction = f"""LANGUAGE INSTRUCTION - HIGHEST PRIORITY:
The lead is writing in {detected_lang}.
You MUST reply in {detected_lang} from now.
Do not use English if detected language is not English.
Match their exact style and mix if they mix.
This overrides all other instructions."""
            
        except Exception as e:
            logger.warning(f"Language detection failed for phone {phone}: {e}")
            
        if len(history) > 0:
            context_rule = "IMPORTANT: Conversation history already exists. You are mid-conversation. DO NOT re-introduce yourself. If the lead says 'hi', just continue naturally from where you left off and DO NOT reset the conversation."
            language_instruction = f"{language_instruction}\n\n{context_rule}".strip()
        
        reply, extraction = await process_message(lead, db, history, combined, language_instruction=language_instruction)
        
        if extraction.get("opted_out"):
            lead.opted_out = True
            old_status = lead.conv_status
            lead.conv_status = "lost"
            await db.commit()
            await log_stage_change(str(lead.id), old_status, "lost", "ai", "Opt-out detected", db)
            await notify_sales_opt_out(lead)
            await redis.delete(f"processing:{phone}")
            return
            
        if extraction.get("escalate"):
            lead.escalated = True
            await db.commit()
            await log_stage_change(str(lead.id), lead.conv_status, lead.conv_status, "ai", "Escalation requested", db)
            arq_pool = ctx.get('redis')
            await arq_pool.enqueue_job('escalate_to_sales', str(lead.id))
        
        db.add(Conversation(lead_id=lead.id, role="user", content=combined))
        db.add(Conversation(lead_id=lead.id, role="assistant", content=reply))
        
        if extraction.get('industry') is not None: lead.industry = extraction['industry']
        if extraction.get('target_markets') is not None: lead.target_markets = extraction['target_markets']
        if extraction.get('monthly_ad_budget') is not None: lead.monthly_ad_budget = extraction['monthly_ad_budget']
        if extraction.get('ads_experience') is not None: lead.ads_experience = extraction['ads_experience']
        if extraction.get('pain_point') is not None: lead.pain_point = extraction['pain_point']
        if extraction.get('urgency') is not None: lead.urgency = extraction['urgency']
        if extraction.get('preferred_call_time') is not None: lead.preferred_call_time = extraction['preferred_call_time']
        
        if extraction.get('lead_score') is not None: 
            lead.lead_score = extraction['lead_score']
        else:
            lead.lead_score = "WARM"
            logger.warning(f"[{lead.id}] lead_score missing, defaulting to WARM")
        
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
            
        if just_qualified:
            old_status = lead.conv_status
            lead.conv_status = "awaiting_call"
            await log_stage_change(str(lead.id), old_status, "awaiting_call", "ai", "All qualification fields present", db)
            
        elif lead.conv_status == "stalled" and new_status in ["qualifying", "in_progress", "awaiting_call"]:
            old_status = lead.conv_status
            lead.conv_status = new_status
            await log_stage_change(str(lead.id), old_status, new_status, "ai", "Resumed from stalled", db)
            
        elif extraction.get("close_intent") and lead.conv_status == "post_call":
            old_status = lead.conv_status
            lead.conv_status = "awaiting_close"
            await log_stage_change(str(lead.id), old_status, "awaiting_close", "ai", "Close intent detected", db)
            await notify_close_intent(lead)
            
        elif lead.conv_status == "fomo" and new_status in ["qualifying", "in_progress", "awaiting_call"]:
            old_status = lead.conv_status
            lead.conv_status = new_status
            await log_stage_change(str(lead.id), old_status, new_status, "ai", "Re-engaged during FOMO", db)
            await notify_cold_reengaged(lead)
            
        elif lead.conv_status == "cold" and new_status in ["qualifying", "in_progress", "awaiting_call"]:
            old_status = lead.conv_status
            lead.conv_status = new_status
            await log_stage_change(str(lead.id), old_status, new_status, "ai", "Re-engaged from cold", db)
            await notify_archived_reengaged(lead)
            
        elif new_status and new_status != lead.conv_status:
            prevent_downgrade = lead.conv_status in ["awaiting_call", "post_call", "closed", "upsell", "lost"] and new_status in ["qualifying", "in_progress", "stalled", "new", "cold"]
            if not prevent_downgrade:
                old_status = lead.conv_status
                lead.conv_status = new_status
                await log_stage_change(str(lead.id), old_status, new_status, "ai", "Status updated by extraction", db)
        
        if extraction.get("referral_detected"):
            ref_name = extraction.get("referral_name") or "Friend"
            ref_phone = extraction.get("referral_phone")
            if ref_phone:
                new_lead = Lead(
                    name=ref_name,
                    phone=ref_phone,
                    conv_status="new",
                    source_ad=f"Referral from {lead.name}",
                )
                db.add(new_lead)
                await db.commit()
                await db.refresh(new_lead)
                arq_pool = ctx.get('redis')
                await arq_pool.enqueue_job('send_opening_message', str(new_lead.id))
                logger.info(f"Referral created from closed client {lead.name}")
        
        if extraction.get("upsell_signal") and lead.conv_status == "closed":
            old_status = lead.conv_status
            lead.conv_status = "upsell"
            await log_stage_change(str(lead.id), old_status, "upsell", "ai", "Upsell signal detected", db)
            arq_pool = ctx.get('redis')
            await arq_pool.enqueue_job('start_upsell_sequence', str(lead.id))
        
        await db.commit()
        await send_message(phone, reply)
        await redis.delete(f"processing:{phone}")
        
        arq_pool = ctx.get('redis')
        if just_qualified:
            await arq_pool.enqueue_job('post_qualification_actions', str(lead.id))
        elif new_status == "qualified" and lead.conv_status == "qualified":
            await arq_pool.enqueue_job('post_qualification_actions', str(lead.id))
        elif new_status == "escalate" and lead.conv_status == "escalate":
            await arq_pool.enqueue_job('escalate_to_sales', str(lead.id))
                
        logger.info(f"[{lead.id}] Exchange summary: Received {len(messages)} messages. Replied and updated lead.")

@safe_task
async def ask_for_reschedule(ctx, lead_id: str):
    logger.info(f"[{lead_id}] Executing ask_for_reschedule")
    async with AsyncSessionLocal() as db:
        # Since it's a sequence 2 (qualification) fallback, we check if seq 2 is active
        can_send, reason = await can_send_message(lead_id, "qualifying", 2, db)
        if not can_send: return
        
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        if not lead: return
        
        project = await get_project_for_lead(lead, db)
        context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)
        msg = get_sequence_message("reschedule_ask", project=project, name=lead.name or "there", pain_point=lead.pain_point, **context)
        if not msg:
            logger.error(f"[{lead_id}] reschedule_ask message not found in config")
            return
            
        await send_message(lead.phone, msg)
        db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
        await db.commit()

@safe_task
async def check_stalled_leads(ctx):
    logger.info("Running check_stalled_leads cron job")
    arq_pool = ctx.get('redis')
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Lead)
            .where(Lead.conv_status.in_(['in_progress', 'qualifying']))
            .where(Lead.updated_at < text("NOW() - INTERVAL '6 hours'"))
        )
        stalled_leads = result.scalars().all()
        
        for lead in stalled_leads:
            check_res = await db.execute(
                select(Conversation)
                .where(Conversation.lead_id == lead.id)
                .where(Conversation.role == 'assistant')
                .where(Conversation.created_at > text("NOW() - INTERVAL '6 hours'"))
            )
            already_sent = check_res.scalars().first()
            if already_sent: continue
                
            name = lead.name if lead.name else "there"
            project = await get_project_for_lead(lead, db)
            context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)
            msg = get_sequence_message("qual_nudge_24h", project=project, name=name, pain_point=lead.pain_point, **context)
            
            await send_message(lead.phone, msg)
            db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
            await db.commit()
            logger.info(f"[{lead.id}] Sent 6h stalled checking in message")
            
        result_48h = await db.execute(
            select(Lead)
            .where(Lead.conv_status.in_(['in_progress', 'qualifying']))
            .where(Lead.updated_at < text("NOW() - INTERVAL '12 hours'"))
        )
        abandoned_leads = result_48h.scalars().all()
        
        for lead in abandoned_leads:
            await arq_pool.enqueue_job('start_dnp_recovery', str(lead.id))
            logger.info(f"[{lead.id}] Triggered start_dnp_recovery after 12h")
            
        result_2h = await db.execute(
            select(Lead)
            .where(Lead.conv_status.in_(['in_progress', 'qualifying']))
            .where(Lead.updated_at < text("NOW() - INTERVAL '2 hours'"))
            .where(Lead.updated_at > text("NOW() - INTERVAL '6 hours'"))
        )
        stalled_2h_leads = result_2h.scalars().all()
        for lead in stalled_2h_leads:
            if settings.VOICE_ENABLED and settings.VOICE_TRIGGER == "no_reply_2h":
                if lead.call_count == 0:
                    await arq_pool.enqueue_job('dispatch_voice_call', str(lead.id))
                    logger.info(f"[{lead.id}] Dispatched voice call after 2h no-reply")

@safe_task
async def post_qualification_actions(ctx, lead_id: str):
    logger.info(f"[{lead_id}] Starting post_qualification_actions")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        if not lead: return
        
    async def safe_run(coro):
        try:
            await coro
        except Exception as e:
            logger.error(f"[{lead_id}] Error in post_qualification_actions sub-task: {e}\n{traceback.format_exc()}")
            
    await asyncio.gather(
        safe_run(update_lead_row(lead)),
        safe_run(notify_sales_qualification(lead)),
        safe_run(ctx['redis'].enqueue_job('schedule_call_reminder', str(lead.id)))
    )
    logger.info(f"[{lead_id}] post qualification actions complete")

@safe_task
async def schedule_call_reminder(ctx, lead_id: str):
    logger.info(f"[{lead_id}] Starting schedule_call_reminder")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        if not lead: return
        
        if not lead.preferred_call_time:
            logger.info(f"[{lead_id}] No preferred_call_time, skipping reminder")
            return
            
        ist = timezone(timedelta(hours=5, minutes=30))
        now_ist = datetime.now(ist).strftime('%A %d %B %Y')
        prompt = f"""
Today is {now_ist}.
The lead said their preferred call time is: 
"{lead.preferred_call_time}"
Return ONLY a datetime string in ISO 8601 format with 
timezone offset +05:30. Nothing else.
Example output: 2024-01-15T18:00:00+05:30
If you cannot parse it, return: UNABLE_TO_PARSE
"""
        response = await call_gpt_mini(prompt)
        if response == "UNABLE_TO_PARSE":
            logger.warning(f"[{lead_id}] Unable to parse preferred call time: {lead.preferred_call_time}")
            return
            
        try:
            parsed_datetime = datetime.fromisoformat(response)
        except ValueError:
            logger.warning(f"[{lead_id}] Invalid ISO format from GPT: {response}")
            return
            
        reminder_time = parsed_datetime - timedelta(minutes=30)
        arq_pool = ctx.get('redis')
        
        if reminder_time < datetime.now(parsed_datetime.tzinfo):
            logger.info(f"[{lead_id}] Reminder time {reminder_time} is in the past, skipping immediate reminder to avoid duplicate alerts.")
        else:
            await arq_pool.enqueue_job('send_call_reminder', str(lead.id), _defer_until=reminder_time)
            
        lead.call_booked_at = parsed_datetime
        await db.commit()
        logger.info(f"[{lead_id}] reminder scheduled for {reminder_time}")

@safe_task
async def send_call_reminder(ctx, lead_id: str):
    logger.info(f"[{lead_id}] Starting send_call_reminder")
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "awaiting_call", 4, db)
        if not can_send:
            logger.info(f"[{lead_id}] Skipping send_call_reminder: {reason}")
            return
            
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        if not lead or lead.call_reminder_sent:
            return
            
        name = lead.name if lead.name else "there"
        project = await get_project_for_lead(lead, db)
        context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)
        msg_lead = get_sequence_message(
            "call_reminder_lead",
            name=name,
            time=lead.preferred_call_time
        , pain_point=lead.pain_point, **context)
        await send_message(lead.phone, msg_lead)
        db.add(Conversation(lead_id=lead.id, role="assistant", content=msg_lead))
        
        score_emoji = {"HOT": "🔴", "WARM": "🟡", "COLD": "🔵"}.get(lead.lead_score, "⚪")
        project = await get_project_for_lead(lead, db)
        context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)
        msg_sales = get_sequence_message(
            "call_reminder_sales",
            name=name,
            score=f"{score_emoji} {lead.lead_score or 'UNSCORED'}",
            industry=lead.industry or "Unknown",
            budget=lead.monthly_ad_budget or "Unknown",
            phone=lead.phone
        , pain_point=lead.pain_point, **context)

        numbers = settings.sales_team_numbers
        for number in numbers:
            success = await send_message(number, msg_sales)
            status = "sent" if success else "failed"
            db.add(NotificationLog(lead_id=lead_id, type="call_reminder_lead", recipient=number, message_preview=msg_sales[:100], status=status))
            db.add(NotificationLog(lead_id=lead_id, type="call_reminder_sales", recipient=number, message_preview=msg_sales[:100], status=status))
            
        lead.call_reminder_sent = True
        await db.commit()
        logger.info(f"[{lead_id}] Call reminders sent")
        
    if settings.VOICE_ENABLED and settings.VOICE_TRIGGER == "reminder":
        arq_pool = ctx.get('redis')
        await arq_pool.enqueue_job('dispatch_voice_call', lead_id)
        logger.info(f"[{lead_id}] Dispatched voice call for reminder")

@safe_task
async def notify_sales_stalled_task(ctx, lead_id: str):
    logger.info(f"[{lead_id}] Executing notify_sales_stalled_task")
    await notify_sales_stalled(lead_id)

@safe_task
async def notify_sales_qualification_task(ctx, lead_id: str):
    logger.info(f"[{lead_id}] Executing notify_sales_qualification_task")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        if not lead: return
        await notify_sales_qualification(lead)

@safe_task
async def escalate_to_sales(ctx, lead_id: str):
    logger.info(f"[{lead_id}] Executing escalate_to_sales")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        if not lead: return
        
        await notify_sales_escalation(lead_id)
        old_status = lead.conv_status
        lead.conv_status = "escalated"
        await db.commit()
        await log_stage_change(lead_id, old_status, "escalated", "ai", "Escalated to sales", db)

@safe_task
async def start_dnp_recovery(ctx, lead_id: str):
    logger.info(f"[{lead_id}] Executing start_dnp_recovery")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        if not lead: return
        
        # Accept stalled (from dashboard) or in_progress/qualifying (from cron)
        if lead.conv_status not in ["stalled", "in_progress", "qualifying"]:
            logger.info(f"[{lead_id}] Skipping start_dnp_recovery: status_changed_{lead.conv_status}")
            return
            
        # Check sequence is enabled
        seq_result = await db.execute(select(SequenceConfig).where(SequenceConfig.sequence_number == 3))
        seq_config = seq_result.scalars().first()
        if not seq_config or not seq_config.enabled:
            logger.info(f"[{lead_id}] Skipping start_dnp_recovery: sequence_3_disabled")
            return
        
        old_status = lead.conv_status
        lead.conv_status = "stalled"
        await db.commit()
        await log_stage_change(lead_id, old_status, "stalled", "system", "Triggered DNP Recovery", db)
        
    arq_pool = ctx.get('redis')
    async with AsyncSessionLocal() as db:
        timing = await get_sequence_timing(3, db)
    await arq_pool.enqueue_job('dnp_message_1', lead_id, _defer_by=_td(timing,'dnp_message_1',2,'hours'), _job_id=f"dnp_1_{lead_id}")
    await arq_pool.enqueue_job('dnp_message_2', lead_id, _defer_by=_td(timing,'dnp_message_2',24,'hours'), _job_id=f"dnp_2_{lead_id}")
    await arq_pool.enqueue_job('dnp_message_3', lead_id, _defer_by=_td(timing,'dnp_message_3',48,'hours'), _job_id=f"dnp_3_{lead_id}")
    await arq_pool.enqueue_job('dnp_message_4', lead_id, _defer_by=_td(timing,'dnp_message_4',72,'hours'), _job_id=f"dnp_4_{lead_id}")

@safe_task
async def dnp_message_1(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "stalled", 3, db)
        if not can_send: return
        
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        project = await get_project_for_lead(lead, db)
        context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)
        msg = get_sequence_message("dnp_day1", project=project, name=lead.name or "there", pain_point=lead.pain_point, **context)
        await send_message(lead.phone, msg)
        db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
        await db.commit()

@safe_task
async def dnp_message_2(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "stalled", 3, db)
        if not can_send: return
        
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        project = await get_project_for_lead(lead, db)
        context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)
        msg = get_sequence_message("dnp_day2", project=project, name=lead.name or "there", pain_point=lead.pain_point, **context)
        await send_message(lead.phone, msg)
        db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
        await db.commit()

@safe_task
async def dnp_message_3(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "stalled", 3, db)
        if not can_send: return
        
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        project = await get_project_for_lead(lead, db)
        context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)
        msg = get_sequence_message("dnp_day3", project=project, name=lead.name or "there", pain_point=lead.pain_point, **context)
        await send_message(lead.phone, msg)
        db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
        await db.commit()

@safe_task
async def dnp_message_4(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "stalled", 3, db)
        if not can_send: return
        
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        project = await get_project_for_lead(lead, db)
        context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)
        msg = get_sequence_message("dnp_day5", project=project, name=lead.name or "there", pain_point=lead.pain_point, **context)
        await send_message(lead.phone, msg)
        db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
        await db.commit()
        
    arq_pool = ctx.get('redis')
    await arq_pool.enqueue_job('check_dnp_exhausted', lead_id, _defer_by=timedelta(hours=24))

@safe_task
async def check_dnp_exhausted(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        if not lead or lead.conv_status != "stalled": return
        
        old_status = lead.conv_status
        lead.conv_status = "cold"
        await db.commit()
        await log_stage_change(lead_id, old_status, "cold", "timeout", "DNP Exhausted", db)
        
    arq_pool = ctx.get('redis')
    await arq_pool.enqueue_job('start_reactivation', lead_id, _defer_by=timedelta(days=14))

@safe_task
async def start_reactivation(ctx, lead_id: str):
    logger.info(f"[{lead_id}] Executing start_reactivation")
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "cold", 7, db)
        if not can_send: return
        
    arq_pool = ctx.get('redis')
    async with AsyncSessionLocal() as db:
        timing = await get_sequence_timing(7, db)
    await arq_pool.enqueue_job('reactivation_1', lead_id, _job_id=f"re_1_{lead_id}")
    await arq_pool.enqueue_job('reactivation_2', lead_id, _defer_by=_td(timing,'reactivation_2',14,'days'), _job_id=f"re_2_{lead_id}")
    await arq_pool.enqueue_job('reactivation_3', lead_id, _defer_by=_td(timing,'reactivation_3',28,'days'), _job_id=f"re_3_{lead_id}")
    await arq_pool.enqueue_job('reactivation_4', lead_id, _defer_by=_td(timing,'reactivation_4',42,'days'), _job_id=f"re_4_{lead_id}")
    await arq_pool.enqueue_job('reactivation_5', lead_id, _defer_by=_td(timing,'reactivation_5',70,'days'), _job_id=f"re_5_{lead_id}")
    await arq_pool.enqueue_job('check_reactivation_complete', lead_id, _defer_by=_td(timing,'check_reactivation_complete',84,'days'), _job_id=f"re_check_{lead_id}")

@safe_task
async def reactivation_1(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "cold", 7, db)
        if not can_send: return
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        project = await get_project_for_lead(lead, db)
        context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)
        msg = get_sequence_message("reactivation_week2", project=project, pain_point=lead.pain_point, **context)
        await send_message(lead.phone, msg)
        db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
        await db.commit()

@safe_task
async def reactivation_2(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "cold", 7, db)
        if not can_send: return
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        project = await get_project_for_lead(lead, db)
        context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)
        msg = get_sequence_message("reactivation_week4", project=project, pain_point=lead.pain_point, **context)
        await send_message(lead.phone, msg)
        db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
        await db.commit()

@safe_task
async def reactivation_3(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "cold", 7, db)
        if not can_send: return
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        project = await get_project_for_lead(lead, db)
        context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)
        msg = get_sequence_message("reactivation_week6", project=project, pain_point=lead.pain_point, **context)
        await send_message(lead.phone, msg)
        db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
        await db.commit()

@safe_task
async def reactivation_4(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "cold", 7, db)
        if not can_send: return
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        project = await get_project_for_lead(lead, db)
        context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)
        msg = get_sequence_message("reactivation_week8", project=project, pain_point=lead.pain_point, **context)
        await send_message(lead.phone, msg)
        db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
        await db.commit()

@safe_task
async def reactivation_5(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "cold", 7, db)
        if not can_send: return
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        project = await get_project_for_lead(lead, db)
        context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)
        msg = get_sequence_message("reactivation_week12", project=project, pain_point=lead.pain_point, **context)
        await send_message(lead.phone, msg)
        db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
        await db.commit()

@safe_task
async def check_reactivation_complete(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        if not lead or lead.conv_status != "cold": return
        old_status = lead.conv_status
        lead.conv_status = "archived"
        await db.commit()
        await log_stage_change(lead_id, old_status, "archived", "timeout", "12-week reactivation exhausted", db)

@safe_task
async def start_closed_sequence(ctx, lead_id: str):
    logger.info(f"[{lead_id}] Executing start_closed_sequence")
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "closed", 8, db)
        if not can_send: return
        
    arq_pool = ctx.get('redis')
    async with AsyncSessionLocal() as db:
        timing = await get_sequence_timing(8, db)
    await arq_pool.enqueue_job('closed_message_1', lead_id, _defer_by=_td(timing,'closed_message_1',3,'days'), _job_id=f"closed_1_{lead_id}")
    await arq_pool.enqueue_job('closed_message_2', lead_id, _defer_by=_td(timing,'closed_message_2',14,'days'), _job_id=f"closed_2_{lead_id}")
    await arq_pool.enqueue_job('closed_message_3', lead_id, _defer_by=_td(timing,'closed_message_3',30,'days'), _job_id=f"closed_3_{lead_id}")
    await arq_pool.enqueue_job('closed_message_4', lead_id, _defer_by=_td(timing,'closed_message_4',35,'days'), _job_id=f"closed_4_{lead_id}")

@safe_task
async def closed_message_1(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "closed", 8, db)
        if not can_send: return
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        project = await get_project_for_lead(lead, db)
        context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)
        msg = get_sequence_message("closed_day3", project=project, pain_point=lead.pain_point, **context)
        await send_message(lead.phone, msg)
        db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
        await db.commit()

@safe_task
async def closed_message_2(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "closed", 8, db)
        if not can_send: return
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        project = await get_project_for_lead(lead, db)
        context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)
        msg = get_sequence_message("closed_day14", project=project, pain_point=lead.pain_point, **context)
        await send_message(lead.phone, msg)
        db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
        await db.commit()

@safe_task
async def closed_message_3(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "closed", 8, db)
        if not can_send: return
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        project = await get_project_for_lead(lead, db)
        context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)
        msg = get_sequence_message("closed_day30", project=project, pain_point=lead.pain_point, **context)
        await send_message(lead.phone, msg)
        db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
        await db.commit()

@safe_task
async def closed_message_4(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "closed", 8, db)
        if not can_send: return
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        project = await get_project_for_lead(lead, db)
        context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)
        msg = get_sequence_message("closed_day35", project=project, pain_point=lead.pain_point, **context)
        await send_message(lead.phone, msg)
        db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
        await db.commit()

@safe_task
async def start_upsell_sequence(ctx, lead_id: str):
    logger.info(f"[{lead_id}] Executing start_upsell_sequence")
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "upsell", 9, db)
        if not can_send: return
        
    arq_pool = ctx.get('redis')
    async with AsyncSessionLocal() as db:
        timing = await get_sequence_timing(9, db)
    await arq_pool.enqueue_job('upsell_message_1', lead_id, _job_id=f"up_1_{lead_id}")
    await arq_pool.enqueue_job('upsell_message_2', lead_id, _defer_by=_td(timing,'upsell_message_2',4,'days'), _job_id=f"up_2_{lead_id}")
    await arq_pool.enqueue_job('upsell_message_3', lead_id, _defer_by=_td(timing,'upsell_message_3',7,'days'), _job_id=f"up_3_{lead_id}")

@safe_task
async def upsell_message_1(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "upsell", 9, db)
        if not can_send: return
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        project = await get_project_for_lead(lead, db)
        context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)
        msg = get_sequence_message("upsell_day1", project=project, pain_point=lead.pain_point, **context)
        await send_message(lead.phone, msg)
        db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
        await db.commit()

@safe_task
async def upsell_message_2(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "upsell", 9, db)
        if not can_send: return
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        project = await get_project_for_lead(lead, db)
        context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)
        msg = get_sequence_message("upsell_day4", project=project, pain_point=lead.pain_point, **context)
        await send_message(lead.phone, msg)
        db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
        await db.commit()

@safe_task
async def upsell_message_3(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "upsell", 9, db)
        if not can_send: return
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        project = await get_project_for_lead(lead, db)
        context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)
        msg = get_sequence_message("upsell_day7", project=project, pain_point=lead.pain_point, **context)
        await send_message(lead.phone, msg)
        db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
        await db.commit()

@safe_task
async def start_post_call_sequence(ctx, lead_id: str):
    logger.info(f"[{lead_id}] Executing start_post_call_sequence")
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "post_call", 5, db)
        if not can_send: return
        
    arq_pool = ctx.get('redis')
    async with AsyncSessionLocal() as db:
        timing = await get_sequence_timing(5, db)
    await arq_pool.enqueue_job('post_call_message_1', lead_id, _job_id=f"pc_1_{lead_id}")
    await arq_pool.enqueue_job('post_call_message_2', lead_id, _defer_by=_td(timing,'post_call_message_2',1,'days'), _job_id=f"pc_2_{lead_id}")
    await arq_pool.enqueue_job('post_call_message_3', lead_id, _defer_by=_td(timing,'post_call_message_3',2,'days'), _job_id=f"pc_3_{lead_id}")
    await arq_pool.enqueue_job('post_call_message_4', lead_id, _defer_by=_td(timing,'post_call_message_4',4,'days'), _job_id=f"pc_4_{lead_id}")
    await arq_pool.enqueue_job('post_call_message_5', lead_id, _defer_by=_td(timing,'post_call_message_5',6,'days'), _job_id=f"pc_5_{lead_id}")
    await arq_pool.enqueue_job('check_post_call_complete', lead_id, _defer_by=_td(timing,'check_post_call_complete',7,'days'), _job_id=f"pc_check_{lead_id}")

@safe_task
async def post_call_message_1(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "post_call", 5, db)
        if not can_send: return
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        
        # Build context for the AI
        notes_context = f"Sales Call Notes: {lead.call_notes}\n" if lead.call_notes else ""
        qual_context = f"Industry: {lead.industry}\nPain Point: {lead.pain_point}\nBudget: {lead.monthly_ad_budget}\n"
        
        prompt = f"""
Write a short, friendly WhatsApp message (under 30 words) from Maya to {lead.name or 'there'}.
Acknowledge that they just had a great phone call with Darshaan's team.
Use the following context to make it highly personalized. Mention their specific business or pain point if possible.
{notes_context}
{qual_context}

End the message by saying Darshaan's team is putting together the details for them.
Do not use emojis except maybe one at the end. Do not sound like a robot.
"""
        from services.gpt import call_gpt_mini
        msg = await call_gpt_mini(prompt)
        
        if not msg or "error" in msg.lower():
            # Fallback if GPT fails or is down
            msg = f"Great speaking today {lead.name or 'there'}! Loved discussing how we can help you solve {lead.pain_point or 'your challenges'} in the {lead.industry or 'your'} space. Darshaan's team is putting together the details for you now 🙌"
            
        await send_message(lead.phone, msg)
        db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
        await db.commit()

@safe_task
async def post_call_message_2(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "post_call", 5, db)
        if not can_send: return
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        project = await get_project_for_lead(lead, db)
        context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)
        msg = get_sequence_message("post_call_day2", project=project, industry=lead.industry or "your industry", pain_point=lead.pain_point, **context)
        await send_message(lead.phone, msg)
        db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
        await db.commit()

@safe_task
async def post_call_message_3(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "post_call", 5, db)
        if not can_send: return
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        project = await get_project_for_lead(lead, db)
        context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)
        msg = get_sequence_message("post_call_day3", project=project, pain_point=lead.pain_point, **context)
        await send_message(lead.phone, msg)
        db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
        await db.commit()

@safe_task
async def post_call_message_4(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "post_call", 5, db)
        if not can_send: return
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        project = await get_project_for_lead(lead, db)
        context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)
        msg = get_sequence_message("post_call_day5", project=project, pain_point=lead.pain_point, **context)
        await send_message(lead.phone, msg)
        db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
        await db.commit()

@safe_task
async def post_call_message_5(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "post_call", 5, db)
        if not can_send: return
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        project = await get_project_for_lead(lead, db)
        context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)
        msg = get_sequence_message("post_call_day7", project=project, name=lead.name or "there", pain_point=lead.pain_point, **context)
        await send_message(lead.phone, msg)
        db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
        await db.commit()

@safe_task
async def check_post_call_complete(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        if not lead or lead.conv_status != "post_call": return
        
        old_status = lead.conv_status
        lead.conv_status = "fomo"
        await db.commit()
        await log_stage_change(lead_id, old_status, "fomo", "timeout", "Post-Call sequence completed", db)
        
    arq_pool = ctx.get('redis')
    await arq_pool.enqueue_job('start_fomo_sequence', lead_id)

@safe_task
async def start_fomo_sequence(ctx, lead_id: str):
    logger.info(f"[{lead_id}] Executing start_fomo_sequence")
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "fomo", 6, db)
        if not can_send: return
        
    arq_pool = ctx.get('redis')
    async with AsyncSessionLocal() as db:
        timing = await get_sequence_timing(6, db)
    await arq_pool.enqueue_job('fomo_message_1', lead_id, _job_id=f"fomo_1_{lead_id}")
    await arq_pool.enqueue_job('fomo_message_2', lead_id, _defer_by=_td(timing,'fomo_message_2',1,'days'), _job_id=f"fomo_2_{lead_id}")
    await arq_pool.enqueue_job('fomo_message_3', lead_id, _defer_by=_td(timing,'fomo_message_3',2,'days'), _job_id=f"fomo_3_{lead_id}")
    await arq_pool.enqueue_job('check_fomo_complete', lead_id, _defer_by=_td(timing,'check_fomo_complete',3,'days'), _job_id=f"fomo_check_{lead_id}")

@safe_task
async def fomo_message_1(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "fomo", 6, db)
        if not can_send: return
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        project = await get_project_for_lead(lead, db)
        context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)
        msg = get_sequence_message("fomo_day1", project=project, name=lead.name or "there", pain_point=lead.pain_point, **context)
        await send_message(lead.phone, msg)
        db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
        await db.commit()

@safe_task
async def fomo_message_2(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "fomo", 6, db)
        if not can_send: return
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        project = await get_project_for_lead(lead, db)
        context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)
        msg = get_sequence_message("fomo_day2", project=project, pain_point=lead.pain_point, **context)
        await send_message(lead.phone, msg)
        db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
        await db.commit()

@safe_task
async def fomo_message_3(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "fomo", 6, db)
        if not can_send: return
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        project = await get_project_for_lead(lead, db)
        context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)
        msg = get_sequence_message("fomo_day3", project=project, pain_point=lead.pain_point, **context)
        await send_message(lead.phone, msg)
        db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
        await db.commit()

@safe_task
async def check_fomo_complete(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        if not lead or lead.conv_status != "fomo": return
        
        old_status = lead.conv_status
        lead.conv_status = "cold"
        await db.commit()
        await log_stage_change(lead_id, old_status, "cold", "timeout", "FOMO sequence completed", db)
        
    arq_pool = ctx.get('redis')
    await arq_pool.enqueue_job('start_reactivation', lead_id, _defer_by=timedelta(days=14))

@safe_task
async def generate_lead_summary(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        if not lead: return
        
        conv_res = await db.execute(
            select(Conversation).where(Conversation.lead_id == lead_id).order_by(Conversation.created_at)
        )
        conversations = conv_res.scalars().all()
        
        if not conversations: return
        
        history_text = "\n".join([f"{msg.role}: {msg.content}" for msg in conversations])
        summary = await generate_summary_from_history_text(history_text)
        if summary and summary != "UNABLE_TO_PARSE":
            lead.ai_summary = summary
            await db.commit()
            logger.info(f"[{lead_id}] Generated AI summary.")

class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    functions = [
        # Call-first flow tasks
        fire_outbound_call,
        check_call_outcome,
        send_no_pickup_whatsapp,
        send_dropped_call_whatsapp,
        send_partial_call_whatsapp,
        # Core tasks
        send_opening_message,
        send_qual_nudge,
        process_buffered_message,
        ask_for_reschedule,
        post_qualification_actions,
        generate_lead_summary,
        schedule_call_reminder,
        send_call_reminder,
        escalate_to_sales,
        notify_sales_stalled_task,
        notify_sales_qualification_task,
        dispatch_voice_call,
        start_dnp_recovery,
        dnp_message_1,
        dnp_message_2,
        dnp_message_3,
        dnp_message_4,
        check_dnp_exhausted,
        start_reactivation,
        reactivation_1,
        reactivation_2,
        reactivation_3,
        reactivation_4,
        reactivation_5,
        check_reactivation_complete,
        start_post_call_sequence,
        post_call_message_1,
        post_call_message_2,
        post_call_message_3,
        post_call_message_4,
        post_call_message_5,
        check_post_call_complete,
        start_fomo_sequence,
        fomo_message_1,
        fomo_message_2,
        fomo_message_3,
        check_fomo_complete,
        start_closed_sequence,
        closed_message_1,
        closed_message_2,
        closed_message_3,
        closed_message_4,
        start_upsell_sequence,
        upsell_message_1,
        upsell_message_2,
        upsell_message_3
    ]
    cron_jobs = [
        cron(check_stalled_leads, hour={0, 6, 12, 18})
    ]
    max_jobs = 10
    job_timeout = 60
