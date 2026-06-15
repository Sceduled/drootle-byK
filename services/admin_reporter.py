import httpx
import logging
import asyncio
from core.config import settings

logger = logging.getLogger(__name__)

async def push_event(event_type: str, lead_id: str, data: dict = None):
    """
    Pushes lifecycle events to the central Admin DB for cross-client reporting.
    Never blocks or crashes the local node.
    """
    if not settings.ADMIN_API_URL or not settings.ADMIN_SECRET:
        return
        
    url = f"{settings.ADMIN_API_URL.rstrip('/')}/stats"
    headers = {"X-Admin-Secret": settings.ADMIN_SECRET}
    
    payload = {
        "client_id": settings.CLIENT_ID,
        "client_name": settings.CLIENT_NAME,
        "event_type": event_type,
        "lead_score": data.get("lead_score") if data else None,
        "from_stage": data.get("from_stage") if data else None,
        "to_stage": data.get("to_stage") if data else "new"
    }
    
    async def _fire_and_forget():
        try:
            logger.info(f"Pushing event to admin: {event_type}")
            logger.info(f"Admin API URL: {settings.ADMIN_API_URL}")
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload, timeout=5.0)
                logger.info(f"Response status: {response.status_code}")
                if response.status_code >= 400:
                    logger.warning(f"Admin API error response: {response.text}")
        except Exception as e:
            logger.warning(f"Failed to push admin event {event_type}: {e}")
            
    # Fire and forget
    asyncio.create_task(_fire_and_forget())
