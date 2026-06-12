"""
Service for handling WhatsApp interactions via Meta or OpenWA.
"""
import httpx
import logging
import asyncio
from core.config import settings

logger = logging.getLogger(__name__)

class WhatsAppClient:
    def __init__(self):
        self.provider = settings.WHATSAPP_PROVIDER
        self.meta_token = settings.META_WHATSAPP_TOKEN
        self.meta_phone_id = settings.META_PHONE_NUMBER_ID
        self.openwa_url = settings.OPENWA_URL
        self.openwa_key = settings.OPENWA_API_KEY

    async def send_message(self, phone: str, message: str) -> bool:
        if self.provider in ("meta", "vobiz"):
            return await self._send_meta(phone, message)
        elif self.provider == "openwa":
            return await self._send_openwa(phone, message)
        else:
            logger.error(f"Unknown WhatsApp provider: {self.provider}")
            return False

    async def _send_meta(self, phone: str, message: str) -> bool:
        url = f"https://graph.facebook.com/v18.0/{self.meta_phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.meta_token}",
            "Content-Type": "application/json"
        }
        
        # Meta API standard expects E.164 format without the '+' sign
        meta_phone = phone.lstrip('+')
        
        payload = {
            "messaging_product": "whatsapp",
            "to": meta_phone,
            "type": "text",
            "text": {
                "body": message
            }
        }
        return await self._execute_with_retry(url, headers, payload, "meta")

    async def _send_openwa(self, phone: str, message: str) -> bool:
        base_url = self.openwa_url.rstrip('/')
        url = f"{base_url}/api/sendText"
        headers = {
            "Authorization": f"Bearer {self.openwa_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "phone": phone,
            "message": message
        }
        return await self._execute_with_retry(url, headers, payload, "openwa")

    async def _execute_with_retry(self, url: str, headers: dict, payload: dict, provider: str) -> bool:
        backoffs = [1, 2, 4]
        async with httpx.AsyncClient() as client:
            for attempt, delay in enumerate(backoffs, 1):
                try:
                    response = await client.post(url, headers=headers, json=payload, timeout=10.0)
                    if response.status_code in (200, 201):
                        return True
                    else:
                        logger.warning(f"WhatsApp API ({provider}) attempt {attempt} failed: {response.status_code} - {response.text}")
                except Exception as e:
                    logger.warning(f"WhatsApp API ({provider}) attempt {attempt} exception: {e}")
                
                if attempt < len(backoffs):
                    await asyncio.sleep(delay)
                    
        logger.error(f"All retries failed for sending WhatsApp message via {provider}")
        return False

# Module-level instance and function for easy importing
_client = WhatsAppClient()

async def send_message(phone: str, message: str) -> bool:
    return await _client.send_message(phone, message)
