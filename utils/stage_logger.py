from sqlalchemy import insert
from core.models import StageHistory
from services.admin_reporter import push_event

async def log_stage_change(
    lead_id: str,
    from_status: str,
    to_status: str,
    triggered_by: str,  # "ai" / "sales" / "system" / "timeout"
    notes: str = None,
    db = None
):
    await db.execute(
        insert(StageHistory).values(
            lead_id=lead_id,
            from_status=from_status,
            to_status=to_status,
            triggered_by=triggered_by,
            notes=notes
        )
    )
    await push_event("stage_changed", str(lead_id), {
        "from_status": from_status,
        "to_status": to_status,
        "triggered_by": triggered_by
    })
    
    if to_status == "qualified":
        await push_event("qualified", str(lead_id))
    elif to_status == "awaiting_call":
        await push_event("call_booked", str(lead_id))
    elif to_status == "closed":
        await push_event("closed", str(lead_id))
    elif to_status == "lost":
        await push_event("opted_out", str(lead_id))
