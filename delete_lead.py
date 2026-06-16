import asyncio
from core.database import AsyncSessionLocal
from core.models import Lead
from sqlalchemy import delete

async def main():
    async with AsyncSessionLocal() as db:
        await db.execute(delete(Lead).where(Lead.name == 'srihari'))
        await db.commit()
        print('Deleted successfully')

if __name__ == '__main__':
    asyncio.run(main())
