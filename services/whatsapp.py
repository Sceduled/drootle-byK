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
        self.waha_url = settings.WAHA_URL
        self.waha_key = settings.WAHA_API_KEY
        self.waha_session = settings.WAHA_SESSION

    async def send_message(self, phone: str, message: str) -> bool:
        if self.provider in ("meta", "vobiz"):
            return await self._send_meta(phone, message)
        elif self.provider in ("openwa", "waha"):
            return await self._send_waha(phone, message)
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

    async def _send_waha(self, phone: str, message: str) -> bool:
        """Send via WAHA (WhatsApp HTTP API) - correct API format"""
        base_url = self.waha_url.rstrip('/')
        url = f"{base_url}/api/sendText"
        headers = {"Content-Type": "application/json"}
        if self.waha_key:
            headers["Authorization"] = f"Bearer {self.waha_key}"
            headers["X-Api-Key"] = self.waha_key

        # If it already has an '@' (like @lid or @g.us), use it directly
        clean_phone = phone.lstrip('+')
        if '@' in clean_phone:
            chat_id = clean_phone
        else:
            chat_id = f"{clean_phone}@c.us"

        payload = {
            "chatId": chat_id,
            "text": message,
            "session": self.waha_session
        }
        logger.info(f"Sending WAHA message to {chat_id} via {url}")
        return await self._execute_with_retry(url, headers, payload, "waha")

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
