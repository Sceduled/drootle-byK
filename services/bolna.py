import logging
import httpx
from core.config import settings
from core.database import AsyncSessionLocal
from sqlalchemy import select
from core.models import Lead

logger = logging.getLogger(__name__)

async def trigger_outbound_call(lead: Lead) -> bool:
    if not settings.VOICE_ENABLED:
        logger.info("voice disabled")
        return False
        
    if settings.VOICE_PROVIDER != "bolna":
        return False
        
    url = "https://api.bolna.dev/call"
    headers = {
        "Authorization": f"Bearer {settings.BOLNA_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "agent_id": settings.BOLNA_AGENT_ID,
        "recipient_phone_number": lead.phone,
        "user_data": {
            "lead_name": lead.name,
            "company": lead.company_name,
            "source_ad": lead.source_ad,
            "industry": lead.industry,
            "known_budget": lead.monthly_ad_budget,
            "known_pain": lead.pain_point,
            "lead_score": lead.lead_score
        }
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=10.0)
            if response.status_code in (200, 201):
                async with AsyncSessionLocal() as db:
                    db_lead = await db.execute(select(Lead).where(Lead.id == lead.id))
                    db_lead = db_lead.scalars().first()
                    if db_lead:
                        from sqlalchemy.sql import func
                        db_lead.last_call_at = func.now()
                        db_lead.call_count += 1
                        await db.commit()
                return True
            else:
                logger.error(f"Bolna call failed: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        logger.error(f"Bolna call exception: {e}")
        return False
