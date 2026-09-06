"""
Service for handling WhatsApp interactions via Meta.
"""
import httpx
import logging
import asyncio
from datetime import datetime, timezone
from core.config import settings

logger = logging.getLogger(__name__)

def is_within_service_window(lead) -> bool:
    if not lead.last_inbound_message_at:
        return False
    now = datetime.now(timezone.utc)
    # Ensure both are timezone aware, or just assume UTC.
    # The DB returns timezone-aware datetimes if configured properly.
    if lead.last_inbound_message_at.tzinfo is None:
        last_inbound = lead.last_inbound_message_at.replace(tzinfo=timezone.utc)
    else:
        last_inbound = lead.last_inbound_message_at
        
    delta = now - last_inbound
    return delta.total_seconds() < 24 * 3600

def build_template_payload(template_name: str, parameters: list) -> dict:
    from client_config import META_TEMPLATE_MAP
    
    if not template_name or template_name not in META_TEMPLATE_MAP:
        logger.error(f"Template {template_name} not found in META_TEMPLATE_MAP")
        return {}

    mapping = META_TEMPLATE_MAP[template_name]
    
    components = []
    if parameters:
        param_list = [{"type": "text", "text": str(p)} for p in parameters]
        components.append({
            "type": "body",
            "parameters": param_list
        })

    return {
        "type": "template",
        "template": {
            "name": mapping["meta_name"],
            "language": {
                "code": mapping["language"]
            },
            "components": components
        }
    }

async def _send_meta(lead, text: str, template_name: str = None, parameters: list = None) -> bool:
    url = f"https://graph.facebook.com/{settings.META_API_VERSION}/{settings.META_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.META_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    meta_phone = lead.phone.lstrip('+')
    
    if is_within_service_window(lead):
        payload = {
            "messaging_product": "whatsapp",
            "to": meta_phone,
            "type": "text",
            "text": {
                "body": text
            }
        }
    else:
        payload = build_template_payload(template_name, parameters)
        if not payload:
            return False
        payload["messaging_product"] = "whatsapp"
        payload["to"] = meta_phone

    backoffs = [1, 2, 4]
    async with httpx.AsyncClient() as client:
        for attempt, delay in enumerate(backoffs, 1):
            try:
                response = await client.post(url, headers=headers, json=payload, timeout=10.0)
                if response.status_code in (200, 201):
                    return True
                else:
                    logger.warning(f"WhatsApp Meta API attempt {attempt} failed: {response.status_code} - {response.text}")
            except Exception as e:
                logger.warning(f"WhatsApp Meta API attempt {attempt} exception: {e}")
            
            if attempt < len(backoffs):
                await asyncio.sleep(delay)
                
    logger.error("All retries failed for sending Meta WhatsApp message")
    return False

async def _send_waha(lead, text: str) -> bool:
    """Send via WAHA (WhatsApp HTTP API)"""
    base_url = settings.WAHA_URL.rstrip('/')
    url = f"{base_url}/api/sendText"
    headers = {"Content-Type": "application/json"}

    # WAHA expects chatId in format: 919876543210@s.whatsapp.net
    # Strip leading + if present
    clean_phone = lead.phone.lstrip('+')
    chat_id = f"{clean_phone}@s.whatsapp.net"

    payload = {
        "chatId": chat_id,
        "text": text,
        "session": settings.WAHA_SESSION
    }
    
    logger.info(f"Sending WAHA message to {chat_id}")
    
    backoffs = [1, 2, 4]
    async with httpx.AsyncClient() as client:
        for attempt, delay in enumerate(backoffs, 1):
            try:
                response = await client.post(url, headers=headers, json=payload, timeout=10.0)
                if response.status_code in (200, 201):
                    return True
                else:
                    logger.warning(f"WAHA API attempt {attempt} failed: {response.status_code} - {response.text}")
            except Exception as e:
                logger.warning(f"WAHA API attempt {attempt} exception: {e}")
            
            if attempt < len(backoffs):
                await asyncio.sleep(delay)
                
    logger.error("All retries failed for sending WAHA message")
    return False

async def send_whatsapp_message(lead, text: str, template_name: str = None, parameters: list = None) -> bool:
    if settings.WHATSAPP_PROVIDER == "waha":
        return await _send_waha(lead, text)
    else:
        return await _send_meta(lead, text, template_name, parameters)

# Backwards compatibility for legacy imports (e.g. notifications.py, tasks.py)
async def send_message(phone: str, text: str) -> bool:
    class _MockLead:
        def __init__(self, p):
            self.phone = p
            self.last_inbound_message_at = datetime.now(timezone.utc)
    return await send_whatsapp_message(_MockLead(phone), text)

async def send_template_message(phone: str, template_name: str, parameters: list = None) -> bool:
    class _MockLead:
        def __init__(self, p):
            self.phone = p
            self.last_inbound_message_at = None
    return await send_whatsapp_message(_MockLead(phone), "template", template_name, parameters)
