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

from core.config import settings
from core.database import AsyncSessionLocal
from core.models import Lead, Conversation, NotificationLog
from core.job_guard import can_send_message
from prompts.agent import get_sequence_message
from services.whatsapp import send_message
from services.gpt import process_message, call_gpt_mini
from services.sheets import update_lead_row
from services.notifications import notify_sales_qualification, notify_sales_stalled, notify_sales_escalation, notify_sales_opt_out, notify_close_intent, notify_cold_reengaged, notify_archived_reengaged
from utils.job_guard import can_send_message
from utils.stage_logger import log_stage_change
from services.bolna import trigger_outbound_call as _trigger_outbound_bolna
from services.pipecat_client import trigger_pipecat_call as _trigger_pipecat_call

logger = logging.getLogger(__name__)

def safe_task(func):
    @functools.wraps(func)
    async def wrapper(ctx, *args, **kwargs):
        try:
            return await func(ctx, *args, **kwargs)
        except Exception as e:
            logger.error(f"Task {func.__name__} failed: {e}\n{traceback.format_exc()}")
            # Do NOT re-raise to prevent infinite retries by ARQ
    return wrapper

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
        opening_message = SEQUENCE_MESSAGES["first_touch"].format(name=display_name)
        
        success = await send_message(lead.phone, opening_message)
        
        if success:
            db.add(Conversation(lead_id=lead.id, role="assistant", content=opening_message))
            old_status = lead.conv_status
            lead.conv_status = "in_progress"
            await db.commit()
            await log_stage_change(lead_id, old_status, "in_progress", "system", "Opening message sent", db)
            logger.info(f"[{lead_id}] Opening message sent successfully to phone: {lead.phone}")
        else:
            logger.error(f"[{lead_id}] Failed to send opening message to phone: {lead.phone}")

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
        
        reply, extraction = await process_message(lead, history, combined)
        
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
        if lead.conv_status == "stalled" and new_status in ["qualifying", "in_progress", "awaiting_call"]:
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
            if lead.conv_status not in ["qualified", "closed"]:
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
        if new_status == "qualified" and lead.conv_status == "qualified":
            await arq_pool.enqueue_job('post_qualification_actions', str(lead.id))
        elif new_status == "escalate" and lead.conv_status == "escalate":
            await arq_pool.enqueue_job('escalate_to_sales', str(lead.id))
                
        logger.info(f"[{lead.id}] Exchange summary: Received {len(messages)} messages. Replied and updated lead.")

@safe_task
async def check_stalled_leads(ctx):
    logger.info("Running check_stalled_leads cron job")
    arq_pool = ctx.get('redis')
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Lead)
            .where(Lead.conv_status == 'in_progress')
            .where(Lead.updated_at < text("NOW() - INTERVAL '24 hours'"))
        )
        stalled_leads = result.scalars().all()
        
        for lead in stalled_leads:
            check_res = await db.execute(
                select(Conversation)
                .where(Conversation.lead_id == lead.id)
                .where(Conversation.role == 'assistant')
                .where(Conversation.created_at > text("NOW() - INTERVAL '24 hours'"))
            )
            already_sent = check_res.scalars().first()
            if already_sent: continue
                
            name = lead.name if lead.name else "there"
            msg = get_sequence_message("qual_nudge_24h", name=name)
            
            await send_message(lead.phone, msg)
            db.add(Conversation(lead_id=lead.id, role="assistant", content=msg))
            await db.commit()
            logger.info(f"[{lead.id}] Sent 24h stalled checking in message")
            
        result_48h = await db.execute(
            select(Lead)
            .where(Lead.conv_status == 'in_progress')
            .where(Lead.updated_at < text("NOW() - INTERVAL '48 hours'"))
        )
        abandoned_leads = result_48h.scalars().all()
        
        for lead in abandoned_leads:
            await arq_pool.enqueue_job('start_dnp_recovery', str(lead.id))
            logger.info(f"[{lead.id}] Triggered start_dnp_recovery after 48h")
            
        result_2h = await db.execute(
            select(Lead)
            .where(Lead.conv_status == 'in_progress')
            .where(Lead.updated_at < text("NOW() - INTERVAL '2 hours'"))
            .where(Lead.updated_at > text("NOW() - INTERVAL '24 hours'"))
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
            await arq_pool.enqueue_job('send_call_reminder', str(lead.id))
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
        msg_lead = get_sequence_message(
            "call_reminder_lead",
            name=name,
            time=lead.preferred_call_time
        )
        await send_message(lead.phone, msg_lead)
        db.add(Conversation(lead_id=lead.id, role="assistant", content=msg_lead))
        
        score_emoji = {"HOT": "🔴", "WARM": "🟡", "COLD": "🔵"}.get(lead.lead_score, "⚪")
        msg_sales = get_sequence_message(
            "call_reminder_sales",
            name=name,
            score=f"{score_emoji} {lead.lead_score or 'UNSCORED'}",
            industry=lead.industry or "Unknown",
            budget=lead.monthly_ad_budget or "Unknown",
            pain_point=lead.pain_point or "Unknown",
            phone=lead.phone
        )

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
        can_send, reason = await can_send_message(lead_id, "stalled", 3, db)
        if not can_send:
            logger.info(f"[{lead_id}] Skipping start_dnp_recovery: {reason}")
            return
            
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        if not lead: return
        
        old_status = lead.conv_status
        lead.conv_status = "stalled"
        await db.commit()
        await log_stage_change(lead_id, old_status, "stalled", "system", "Triggered DNP Recovery", db)
        
    arq_pool = ctx.get('redis')
    await arq_pool.enqueue_job('dnp_message_1', lead_id, _defer_by=timedelta(hours=2))
    await arq_pool.enqueue_job('dnp_message_2', lead_id, _defer_by=timedelta(hours=24))
    await arq_pool.enqueue_job('dnp_message_3', lead_id, _defer_by=timedelta(hours=48))
    await arq_pool.enqueue_job('dnp_message_4', lead_id, _defer_by=timedelta(hours=72))

@safe_task
async def dnp_message_1(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "stalled", 3, db)
        if not can_send: return
        
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        msg = get_sequence_message("dnp_day1", name=lead.name or "there")
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
        msg = get_sequence_message("dnp_day2", name=lead.name or "there")
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
        msg = get_sequence_message("dnp_day3", name=lead.name or "there")
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
        msg = get_sequence_message("dnp_day5", name=lead.name or "there")
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
    await arq_pool.enqueue_job('reactivation_1', lead_id)
    await arq_pool.enqueue_job('reactivation_2', lead_id, _defer_by=timedelta(days=14))
    await arq_pool.enqueue_job('reactivation_3', lead_id, _defer_by=timedelta(days=28))
    await arq_pool.enqueue_job('reactivation_4', lead_id, _defer_by=timedelta(days=42))
    await arq_pool.enqueue_job('reactivation_5', lead_id, _defer_by=timedelta(days=70))
    await arq_pool.enqueue_job('check_reactivation_complete', lead_id, _defer_by=timedelta(days=84))

@safe_task
async def reactivation_1(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "cold", 7, db)
        if not can_send: return
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        msg = get_sequence_message("reactivation_wk2")
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
        msg = get_sequence_message("reactivation_wk4")
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
        msg = get_sequence_message("reactivation_wk6")
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
        msg = get_sequence_message("reactivation_wk8")
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
        msg = get_sequence_message("reactivation_wk12")
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
    await arq_pool.enqueue_job('closed_message_1', lead_id, _defer_by=timedelta(days=3))
    await arq_pool.enqueue_job('closed_message_2', lead_id, _defer_by=timedelta(days=14))
    await arq_pool.enqueue_job('closed_message_3', lead_id, _defer_by=timedelta(days=30))
    await arq_pool.enqueue_job('closed_message_4', lead_id, _defer_by=timedelta(days=35))

@safe_task
async def closed_message_1(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "closed", 8, db)
        if not can_send: return
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        msg = get_sequence_message("closed_day3")
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
        msg = get_sequence_message("closed_wk2")
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
        msg = get_sequence_message("closed_mo1")
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
        msg = get_sequence_message("closed_mo1_fup")
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
    await arq_pool.enqueue_job('upsell_message_1', lead_id)
    await arq_pool.enqueue_job('upsell_message_2', lead_id, _defer_by=timedelta(days=4))
    await arq_pool.enqueue_job('upsell_message_3', lead_id, _defer_by=timedelta(days=7))

@safe_task
async def upsell_message_1(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "upsell", 9, db)
        if not can_send: return
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        msg = get_sequence_message("upsell_day1")
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
        msg = get_sequence_message("upsell_day4")
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
        msg = get_sequence_message("upsell_day7")
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
    await arq_pool.enqueue_job('post_call_message_1', lead_id)
    await arq_pool.enqueue_job('post_call_message_2', lead_id, _defer_by=timedelta(days=1))
    await arq_pool.enqueue_job('post_call_message_3', lead_id, _defer_by=timedelta(days=2))
    await arq_pool.enqueue_job('post_call_message_4', lead_id, _defer_by=timedelta(days=4))
    await arq_pool.enqueue_job('post_call_message_5', lead_id, _defer_by=timedelta(days=6))
    await arq_pool.enqueue_job('check_post_call_complete', lead_id, _defer_by=timedelta(days=7))

@safe_task
async def post_call_message_1(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "post_call", 5, db)
        if not can_send: return
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        msg = get_sequence_message("post_call_day1", name=lead.name or "there")
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
        msg = get_sequence_message("post_call_day2", industry=lead.industry or "your industry")
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
        msg = get_sequence_message("post_call_day3")
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
        msg = get_sequence_message("post_call_day5", pain_point=lead.pain_point or "your current challenges")
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
        msg = get_sequence_message("post_call_day7", name=lead.name or "there")
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
    await arq_pool.enqueue_job('fomo_message_1', lead_id)
    await arq_pool.enqueue_job('fomo_message_2', lead_id, _defer_by=timedelta(days=1))
    await arq_pool.enqueue_job('fomo_message_3', lead_id, _defer_by=timedelta(days=2))
    await arq_pool.enqueue_job('check_fomo_complete', lead_id, _defer_by=timedelta(days=3))

@safe_task
async def fomo_message_1(ctx, lead_id: str):
    async with AsyncSessionLocal() as db:
        can_send, reason = await can_send_message(lead_id, "fomo", 6, db)
        if not can_send: return
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        msg = get_sequence_message("fomo_day1")
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
        msg = get_sequence_message("fomo_day2")
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
        msg = get_sequence_message("fomo_day3")
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

class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    functions = [
        send_opening_message,
        process_buffered_message,
        post_qualification_actions,
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
