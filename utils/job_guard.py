import logging
from sqlalchemy import select
from core.models import Lead, SequenceConfig

logger = logging.getLogger(__name__)

async def can_send_message(
    lead_id: str, 
    expected_status: str,
    sequence_number: int,
    db
) -> tuple[bool, str]:
    """
    Returns (can_send, reason)
    Call this at the TOP of every ARQ sequence task.
    If returns False → skip silently, log reason, return early.
    """
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalars().first()
    
    if not lead:
        return False, "lead_not_found"
    
    if lead.opted_out:
        return False, "lead_opted_out"
    
    if lead.conv_status != expected_status:
        return False, f"status_changed_{lead.conv_status}"
    
    # Check sequence is enabled
    seq_result = await db.execute(select(SequenceConfig).where(SequenceConfig.sequence_number == sequence_number))
    seq_config = seq_result.scalars().first()
    
    if not seq_config or not seq_config.enabled:
        return False, f"sequence_{sequence_number}_disabled"
    
    return True, "ok"
