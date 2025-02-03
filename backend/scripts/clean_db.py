from app.db.session import SessionLocal
from app.models.db import Document
import asyncio

async def clean():
    async with SessionLocal() as db:
        await db.execute('DELETE FROM document')
        await db.commit()

if __name__ == "__main__":
    asyncio.run(clean())
