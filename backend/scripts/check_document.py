from fire import Fire
from app.db.session import SessionLocal
from app.api import crud
import asyncio

async def check_document():
    async with SessionLocal() as db:
        docs = await crud.fetch_documents(db)
        print("\nDocuments in database:")
        for doc in docs:
            print(f"ID: {doc.id}")
            print(f"URL: {doc.url}")
            print(f"Metadata: {doc.metadata_map}")
            print("---")

def main():
    asyncio.run(check_document())

if __name__ == "__main__":
    Fire(main)