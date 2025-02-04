from tqdm import tqdm
from fire import Fire
import asyncio
from app.db.session import SessionLocal
from app.api import crud
from app.chat.engine import (
    get_tool_service_context,
    build_doc_id_to_index_map,
    get_s3_fs,
)


async def async_main_seed_storage_context():
    fs = get_s3_fs()
    async with SessionLocal() as db:
        docs = await crud.fetch_documents(db)
    
    service_context = get_tool_service_context([])
    failed_docs = []
    
    for doc in tqdm(docs, desc="Seeding storage with DB documents"):
        try:
            # First check if file exists in S3
            if not fs.exists(doc.url.replace('http://localhost:4566/', '')):
                print(f"\nWarning: Document not found in S3: {doc.url}")
                print("Please ensure the file is uploaded to S3 before running this script.")
                failed_docs.append(doc.id)
                continue
                
            await build_doc_id_to_index_map(service_context, [doc], fs=fs)
            print(f"\nSuccessfully processed document {doc.id}")
        except Exception as e:
            print(f"\nError processing document {doc.id}: {str(e)}")
            failed_docs.append(doc.id)
    
    if failed_docs:
        print("\nFailed to process the following documents:")
        for doc_id in failed_docs:
            print(f"- {doc_id}")
        print("\nPlease ensure these documents exist in S3 and try again.")


def main_seed_storage_context():
    asyncio.run(async_main_seed_storage_context())


if __name__ == "__main__":
    Fire(main_seed_storage_context)
