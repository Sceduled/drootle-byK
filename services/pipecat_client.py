import logging
import httpx
from core.config import settings
from core.database import AsyncSessionLocal
from sqlalchemy import select
from core.models import Lead

logger = logging.getLogger(__name__)

async def trigger_pipecat_call(lead: Lead) -> bool:
    if not settings.VOICE_ENABLED:
        logger.info("voice disabled")
        return False
        
    if settings.VOICE_PROVIDER != "pipecat":
        return False
        
    url = f"{settings.PIPECAT_SERVER_URL.rstrip('/')}/start-call"
    payload = {
        "phone": lead.phone,
        "lead_id": str(lead.id),
        "lead_name": lead.name,
        "company": lead.company_name,
        "known_info": {
            "industry": lead.industry,
            "budget": lead.monthly_ad_budget,
            "pain": lead.pain_point
        },
        "callback_url": f"https://{settings.RAILWAY_PUBLIC_DOMAIN}/api/webhooks/pipecat"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
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
                logger.error(f"Pipecat call failed: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        logger.error(f"Pipecat call exception: {e}")
        return False
