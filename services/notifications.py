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
    cd = lead.call_partial_data or {}

    def _get(lead_field, call_key: str) -> str:
        """Return lead field if set, else fall back to call_partial_data, else 'Not specified'."""
        if lead_field:
            if isinstance(lead_field, list):
                return ", ".join(lead_field)
            return str(lead_field)
        val = cd.get(call_key)
        return str(val) if val else "Not specified"

    budget    = _get(lead.monthly_ad_budget, "budget")
    location  = _get(None, "location")  # no direct Lead field for location
    bhk       = _get(None, "bhk")
    timeline  = _get(lead.urgency, "timeline")
    purpose   = _get(None, "purpose")
    markets   = _get(lead.target_markets, "location")

    # Build source label
    call_badge = " [via call]" if cd else ""

    message = f"""{score_emoji} {lead.lead_score or 'UNSCORED'} LEAD{call_badge} — {lead.name or 'Unknown'} | {lead.company_name or 'Unknown'}

Budget:    {budget}
Location:  {location}
BHK/Size:  {bhk}
Timeline:  {timeline}
Purpose:   {purpose}
Markets:   {markets}
Pain:      {lead.pain_point or 'Not specified'}
📞 Call at: {lead.preferred_call_time or 'No time given'}
Phone: {lead.phone}""".strip()

    await _send_to_sales_team(str(lead.id), message, "sales_alert")
    logger.info(f"sales team notified for lead {lead.id}")

async def notify_sales_unmatched_project(lead) -> None:
    message = (
        f"⚠ Could not auto-match project for this lead — please assign manually in dashboard.\n"
        f"Name: {lead.name or 'Unknown'}\n"
        f"Phone: {lead.phone}\n"
        f"Ad Source: {lead.source_ad or 'Unknown'}"
    )
    await _send_to_sales_team(str(lead.id), message, "unmatched_project_alert")

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

async def notify_close_intent(lead) -> None:
    message = (
        f"🏆 READY TO CLOSE\n"
        f"{lead.name} | {lead.company_name}\n"
        f"They just said YES — call them now!\n"
        f"Phone: {lead.phone}"
    )
    await _send_to_sales_team(str(lead.id), message, "close_intent")

async def notify_cold_reengaged(lead) -> None:
    message = (
        f"💡 COLD LEAD RE-ENGAGED\n"
        f"{lead.name} replied during FOMO sequence\n"
        f"Score: {lead.lead_score}\n"
        f"Phone: {lead.phone}"
    )
    await _send_to_sales_team(str(lead.id), message, "reengaged_alert")

async def notify_archived_reengaged(lead) -> None:
    message = (
        f"🔄 ARCHIVED LEAD RE-ENGAGED\n"
        f"{lead.name} just replied from the cold archives!\n"
        f"Score: {lead.lead_score}\n"
        f"Phone: {lead.phone}"
    )
    await _send_to_sales_team(str(lead.id), message, "archived_reengaged_alert")

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
