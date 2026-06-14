from sqlalchemy import select
from core.models import Lead, SequenceConfig

async def can_send_message(lead_id: str, required_status: str, sequence_number: int, db) -> tuple[bool, str]:
    """
    Central safety gate for all outbound ARQ sequence messages.
    Returns (bool, str) -> (can_send, reason).
    """
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalars().first()
    
    if not lead:
        return False, "Lead not found"
        
    if lead.opted_out:
        return False, "Lead opted out"
        
    if lead.conv_status != required_status:
        return False, f"Status mismatch (expected {required_status}, got {lead.conv_status})"
        
    seq_result = await db.execute(select(SequenceConfig).where(SequenceConfig.sequence_number == sequence_number))
    seq_config = seq_result.scalars().first()
    
    if not seq_config or not seq_config.enabled:
        return False, f"Sequence {sequence_number} is disabled"
        
    return True, "OK"
