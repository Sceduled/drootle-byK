import asyncio
from sqlalchemy import select
from core.database import AsyncSessionLocal
from core.models import Lead, Conversation

async def main():
    async with AsyncSessionLocal() as db:
        phone_to_delete = "+918122787023"
        result = await db.execute(select(Lead).where(Lead.phone == phone_to_delete))
        lead = result.scalars().first()
        
        if lead:
            print(f"Found lead {lead.id}, deleting...")
            await db.delete(lead)
            await db.commit()
            print("Lead and its conversations deleted successfully!")
        else:
            print(f"Lead with phone {phone_to_delete} not found!")

asyncio.run(main())
