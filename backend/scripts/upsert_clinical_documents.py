from pathlib import Path
from fire import Fire
from tqdm import tqdm
import asyncio
from fastapi.encoders import jsonable_encoder
from app.models.db import Document
from app.schema import (
    ClinicalGuidelineMetadata,
    DocumentMetadataMap,
    DocumentMetadataKeysEnum,
    Document as DocumentSchema,
)
from app.db.session import SessionLocal
from app.api import crud

DEFAULT_URL_BASE = "http://localhost:4566"  # LocalStack endpoint
DEFAULT_DOC_DIR = "clinical_guidelines/"

async def upsert_single_document(doc_dir: str, guideline_file: Path, metadata: dict, url_base: str):
    """
    Upsert a single clinical guideline document into the database.
    """
    # Construct the document path
    doc_path = guideline_file.relative_to(doc_dir)
    
    # Handle URL construction based on environment
    if url_base.startswith("http://localhost:4566"):
        # For local development with direct S3 endpoint
        url_path = f"{url_base}/clinical-guidelines/{doc_path}"
    else:
        # For production S3 or other environments
        url_path = f"{url_base.rstrip('/')}/clinical-guidelines/{doc_path}"
    
    # Create guideline metadata
    guideline_metadata = ClinicalGuidelineMetadata(
        title=metadata.get("title", guideline_file.stem),
        issuing_organization=metadata.get("issuing_organization"),
        publication_date=metadata.get("publication_date"),
        specialty=metadata.get("specialty"),
        evidence_grading_system=metadata.get("evidence_grading_system")
    )
    
    metadata_map: DocumentMetadataMap = {
        DocumentMetadataKeysEnum.CLINICAL_GUIDELINE: jsonable_encoder(
            guideline_metadata.dict(exclude_none=True)
        )
    }
    
    doc = DocumentSchema(url=str(url_path), metadata_map=metadata_map)
    
    async with SessionLocal() as db:
        document = await crud.upsert_document_by_url(db, doc)
        return document

async def async_upsert_documents_from_guidelines(
    url_base: str,
    doc_dir: str,
    metadata_list: list
):
    """
    Upserts clinical guideline documents into the database.
    """
    doc_dir_path = Path(doc_dir)
    guideline_files = list(doc_dir_path.glob("*.pdf"))
    
    print(f"Found {len(guideline_files)} clinical guidelines in {doc_dir}")
    
    documents = []
    for guideline_file, metadata in tqdm(
        zip(guideline_files, metadata_list),
        total=len(guideline_files),
        desc="Upserting clinical guidelines"
    ):
        document = await upsert_single_document(doc_dir, guideline_file, metadata, url_base)
        documents.append(document)
        print(f"Upserted document {guideline_file.name}. Database ID: {document.id}")
    
    return documents

def main_upsert_documents_from_guidelines(
    url_base: str = DEFAULT_URL_BASE,
    doc_dir: str = DEFAULT_DOC_DIR,
    metadata_list: list = None
):
    """
    Main entry point for upserting clinical guideline documents.
    """
    if metadata_list is None:
        metadata_list = []
    
    asyncio.run(
        async_upsert_documents_from_guidelines(
            url_base=url_base,
            doc_dir=doc_dir,
            metadata_list=metadata_list
        )
    )

if __name__ == "__main__":
    Fire(main_upsert_documents_from_guidelines)