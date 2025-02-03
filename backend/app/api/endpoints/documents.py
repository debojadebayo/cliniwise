from typing import List, Optional
import logging
from fastapi import Depends, APIRouter, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.api.deps import get_db
from app.api import crud
from app import schema

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
        1. If document_ids provided:
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