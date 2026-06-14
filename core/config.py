"""
Configuration module for Agentic Lead AI.
Loads settings from environment variables using Pydantic BaseSettings.
"""
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o"

    # WhatsApp
    WHATSAPP_PROVIDER: str = "waha"
    META_WHATSAPP_TOKEN: str = ""
    META_PHONE_NUMBER_ID: str = ""
    META_WEBHOOK_VERIFY_TOKEN: str = ""
    META_APP_SECRET: str = ""
    WAHA_URL: str = ""
    WAHA_API_KEY: str = ""
    WAHA_SESSION: str = "default"

    # Google Sheets
    GOOGLE_SHEET_ID: str = ""
    GOOGLE_CREDENTIALS_JSON: str = ""

    # Sales team
    SALES_TEAM_WHATSAPP_NUMBERS: str = ""

    # Auth
    JWT_SECRET: str = "supersecret"
    JWT_EXPIRY_HOURS: int = 24

    # Webhook security
    WEBHOOK_SECRET: str = ""

    # Voice (disabled by default)
    VOICE_ENABLED: bool = False
    VOICE_PROVIDER: str = "bolna"  # "bolna" or "pipecat"
    VOICE_TRIGGER: str = "manual"  # "manual", "no_reply_2h", "reminder"
    BOLNA_API_KEY: str = ""
    BOLNA_AGENT_ID: str = ""
    PIPECAT_SERVER_URL: str = ""

    # Railway
    RAILWAY_PUBLIC_DOMAIN: str = ""

    # Dashboard auth
    DASHBOARD_USERNAME: str
    DASHBOARD_PASSWORD: str

    # Client & Admin
    CLIENT_ID: str = ""
    CLIENT_NAME: str = ""
    ADMIN_API_URL: str = ""
    ADMIN_SECRET: str = ""

    @property
    def sales_team_numbers(self) -> List[str]:
        if not self.SALES_TEAM_WHATSAPP_NUMBERS:
            return []
        return [num.strip() for num in self.SALES_TEAM_WHATSAPP_NUMBERS.split(",") if num.strip()]

    class Config:
        env_file = ".env"

settings = Settings()
