from sqlalchemy import insert
from core.models import StageHistory

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
