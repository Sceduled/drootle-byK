"""
Service for interacting with Google Sheets API.
"""
import logging
import json
import asyncio
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from core.config import settings

logger = logging.getLogger(__name__)

async def update_lead_row(lead) -> bool:
    if lead.sheet_row_index is None:
        logger.warning(f"Lead {lead.id} has no sheet_row_index, skipping sheet update")
        return False
        
    if not settings.GOOGLE_CREDENTIALS_JSON or not settings.GOOGLE_SHEET_ID:
        logger.warning("Google Sheets credentials or ID not configured")
        return False

    def _sync_update():
        try:
            creds_info = json.loads(settings.GOOGLE_CREDENTIALS_JSON)
            credentials = Credentials.from_service_account_info(
                creds_info, 
                scopes=["https://www.googleapis.com/auth/spreadsheets"]
            )
            service = build("sheets", "v4", credentials=credentials)
            
            score = lead.lead_score or ""
            industry = lead.industry or ""
            markets = ", ".join(lead.target_markets) if lead.target_markets else ""
            budget = lead.monthly_ad_budget or ""
            pain = lead.pain_point or ""
            call_time = lead.preferred_call_time or ""
            status = lead.conv_status or ""
            updated_at = datetime.utcnow().isoformat() + "Z"
            
            values = [[score, industry, markets, budget, pain, call_time, status, updated_at]]
            range_name = f"Sheet1!G{lead.sheet_row_index}:N{lead.sheet_row_index}"
            
            service.spreadsheets().values().update(
                spreadsheetId=settings.GOOGLE_SHEET_ID,
                range=range_name,
                valueInputOption="RAW",
                body={"values": values}
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Google Sheets update failed for lead {lead.id}: {e}")
            return False

    return await asyncio.to_thread(_sync_update)
