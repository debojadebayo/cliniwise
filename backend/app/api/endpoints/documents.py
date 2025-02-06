from typing import List, Optional
import logging
from fastapi import Depends, APIRouter, HTTPException, Query, Response, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import s3fs
import re
from app.api.deps import get_db
from app.api import crud
from app import schema
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

"""
Document management endpoints.
Handles CRUD operations for documents in the system.
"""

@router.get("/")
async def get_documents(
    document_ids: Optional[List[UUID]] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> List[schema.Document]:
    """
    Retrieve documents from the database.
    
    Process:
        1. If document_ids provided:ß
           - Fetches specific documents by their IDs
        2. If no document_ids:
           - Returns all documents in the system
        3. Raises 404 if no documents found
    """
    if document_ids is None:
        # If no ids provided, fetch all documents
        docs = await crud.fetch_documents(db)
    else:
        # If ids are provided, fetch documents by ids
        docs = await crud.fetch_documents(db, ids=document_ids)

    if len(docs) == 0:
        raise HTTPException(status_code=404, detail="Document(s) not found")

    return docs

@router.get("/{document_id}")
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> schema.Document:
    """
    Retrieve a single document by its ID.
    
    Process:
        1. Queries database for document with matching ID
        2. Returns document if found
        3. Raises 404 if document doesn't exist
    """
    docs = await crud.fetch_documents(db, id=document_id)
    if len(docs) == 0:
        raise HTTPException(status_code=404, detail="Document not found")

    return docs[0]


@router.post("/")
async def create_document(
    document: schema.Document,
    db: AsyncSession = Depends(get_db),
) -> schema.Document:
    """
    Create or update a document in the system.
    
    Process:
        1. Takes document metadata including:
           - URL to the document
           - Clinical guideline metadata
           - Other document properties
        2. Upserts document in database:
           - Creates new if doesn't exist
           - Updates if URL already exists
        3. Returns created/updated document
        
    Note:
        Document processing and embedding creation happens 
        lazily when the document is first used in a conversation.
    """
    return await crud.upsert_document_by_url(db, document)

@router.options("/assets/{filename}")
async def options_document_asset(filename: str):
    """Handle CORS preflight requests for document assets."""
    return {
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        }
    }

# Cache to store file handles and metadata
_file_cache = {}

@router.get("/assets/{filename}")
async def get_document_asset(filename: str, response: Response, range: str = Header(None)):
    """
    Stream PDF files directly from S3 with support for byte-range requests.
    Handles partial content loading for better performance with large PDFs.
    """
    logger.debug(f"Initializing S3 connection with endpoint: {settings.S3_ENDPOINT_URL}")
    s3_kwargs = {
        "anon": False,
        "client_kwargs": {
            "endpoint_url": settings.S3_ENDPOINT_URL if settings.ENVIRONMENT != "production" else None,
        }
    }
    
    s3_kwargs["key"] = settings.AWS_KEY
    s3_kwargs["secret"] = settings.AWS_SECRET
    if hasattr(settings, 'AWS_SESSION_TOKEN') and settings.AWS_SESSION_TOKEN:
        s3_kwargs["token"] = settings.AWS_SESSION_TOKEN
    
    s3 = s3fs.S3FileSystem(**s3_kwargs)
    
    try:
        clean_filename = filename.lstrip('/')
        file_path = f"{settings.S3_ASSET_BUCKET_NAME}/{clean_filename}"
        
        # Get file size
        file_size = s3.size(file_path)
        
        # Handle byte-range requests
        start = 0
        end = file_size - 1
        
        if range is not None:
            try:
                range_match = re.match(r'bytes=(\d+)-(\d*)', range)
                if range_match:
                    start = int(range_match.group(1))
                    if range_match.group(2):
                        end = min(int(range_match.group(2)), file_size - 1)
                    response.status_code = 206
            except ValueError:
                # If range is invalid, serve full file
                pass
        
        # Calculate actual content length
        content_length = end - start + 1
        
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Type": "application/pdf",
            "Content-Disposition": f"inline; filename={clean_filename}",
            "Cache-Control": "public, max-age=31536000" if settings.ENVIRONMENT == "production" else "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Range, Content-Type"
        }
        
        # Add Content-Range only for partial content
        if response.status_code == 206:
            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        
        # Open file and seek to start position
        file = s3.open(file_path, 'rb')
        file.seek(start)
        
        # Create async generator for streaming
        async def file_streamer():
            try:
                bytes_remaining = content_length
                while bytes_remaining > 0:
                    chunk_size = min(8192, bytes_remaining)
                    chunk = file.read(chunk_size)
                    if not chunk:
                        break
                    bytes_remaining -= len(chunk)
                    yield chunk
            finally:
                file.close()
        
        return StreamingResponse(
            file_streamer(),
            headers=headers,
            media_type="application/pdf"
        )
            
    except Exception as e:
        logger.error(f"Error accessing S3 file {filename}: {str(e)}")
        raise HTTPException(status_code=404, detail=f"File {filename} not found")