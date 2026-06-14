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
        
    url = f"{settings.ADMIN_API_URL.rstrip('/')}/api/events"
    headers = {"X-Admin-Secret": settings.ADMIN_SECRET}
    
    payload = {
        "client_id": settings.CLIENT_ID,
        "event_type": event_type,
        "lead_id": str(lead_id),
        "data": data or {}
    }
    
    async def _fire_and_forget():
        try:
            async with httpx.AsyncClient() as client:
                await client.post(url, headers=headers, json=payload, timeout=5.0)
        except Exception as e:
            logger.warning(f"Failed to push admin event {event_type}: {e}")
            
    # Fire and forget
    asyncio.create_task(_fire_and_forget())
