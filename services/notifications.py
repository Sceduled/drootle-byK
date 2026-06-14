"""
Service for sending notifications to the sales team.
"""
import logging
from sqlalchemy import select
from core.config import settings
from core.database import AsyncSessionLocal
from core.models import Lead, NotificationLog
from services.whatsapp import send_message

logger = logging.getLogger(__name__)

async def notify_sales_qualification(lead) -> None:
    score_emoji = {"HOT": "🔴", "WARM": "🟡", "COLD": "🔵"}.get(lead.lead_score, "⚪")
    markets_str = ", ".join(lead.target_markets or []) if lead.target_markets else "Not specified"
    
    message = f"""{score_emoji} {lead.lead_score or 'UNSCORED'} LEAD — {lead.name or 'Unknown'} | {lead.company_name or 'Unknown'}

Industry: {lead.industry or 'Not specified'}
Markets: {markets_str}
Budget: {lead.monthly_ad_budget or 'Not specified'}
Pain: {lead.pain_point or 'Not specified'}
Urgency: {lead.urgency or 'Not specified'}
📞 Call at: {lead.preferred_call_time or 'No time given'}
Phone: {lead.phone}""".strip()

    await _send_to_sales_team(str(lead.id), message, "sales_alert")
    logger.info(f"sales team notified for lead {lead.id}")

async def notify_sales_stalled(lead_id: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        if not lead: return
        
    message = f"⚠️ STALLED LEAD — {lead.name or 'Unknown'} | {lead.phone}\nWent quiet after {lead.conv_status}. May need manual outreach."
    await _send_to_sales_team(lead_id, message, "stalled_alert")

async def notify_sales_escalation(lead_id: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()
        if not lead: return
        
    message = f"🚨 ESCALATION — {lead.name or 'Unknown'} asked to speak to a human NOW\nPhone: {lead.phone}\nCompany: {lead.company_name or 'Unknown'}\nScore so far: {lead.lead_score or 'Unknown'}"
    await _send_to_sales_team(lead_id, message, "escalation")

async def notify_sales_opt_out(lead) -> None:
    message = f"❌ OPT OUT — {lead.name or 'Unknown'} asked to stop messaging.\nPhone: {lead.phone}"
    await _send_to_sales_team(str(lead.id), message, "opt_out")

async def _send_to_sales_team(lead_id: str, message: str, notif_type: str):
    numbers = settings.sales_team_numbers
    if not numbers:
        logger.warning("No sales team numbers configured for notifications")
        return
        
    async with AsyncSessionLocal() as db:
        for number in numbers:
            success = await send_message(number, message)
            status = "sent" if success else "failed"
            log_entry = NotificationLog(
                lead_id=lead_id,
                type=notif_type,
                recipient=number,
                message_preview=message[:100],
                status=status
            )
            db.add(log_entry)
        await db.commit()
