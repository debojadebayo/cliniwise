from typing import Optional, cast, Sequence, List
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db import Conversation, Message, Document, ConversationDocument
from app import schema
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert


"""
Database CRUD operations for conversations, messages, and documents.
Uses SQLAlchemy for async database interactions.
"""


async def fetch_conversation_with_messages(
    db: AsyncSession, conversation_id: str
) -> Optional[schema.Conversation]:
    """
    Retrieve a conversation with all its messages and subprocesses.
    
    Process:
        1. Builds query with eager loading for:
           - Messages and their subprocesses
           - Associated documents
        2. Executes query and gets first result
        3. Formats response with document list
        4. Returns None if conversation not found
    """
    # Eagerly load required relationships
    stmt = (
        select(Conversation)
        .options(joinedload(Conversation.messages).subqueryload(Message.sub_processes))
        .options(
            joinedload(Conversation.conversation_documents).subqueryload(
                ConversationDocument.document
            )
        )
        .where(Conversation.id == conversation_id)
    )

    result = await db.execute(stmt)  # execute the statement
    conversation = result.scalars().first()  # get the first result
    if conversation is not None:
        convo_dict = {
            **conversation.__dict__,
            "documents": [
                convo_doc.document for convo_doc in conversation.conversation_documents
            ],
        }
        return schema.Conversation(**convo_dict)
    return None


async def create_conversation(
    db: AsyncSession, convo_payload: schema.ConversationCreate
) -> schema.Conversation:
    """
    Create a new conversation with document associations.
    
    Process:
        1. Creates new conversation record
        2. Creates ConversationDocument links for each document
        3. Adds all records to database
        4. Commits transaction
        5. Returns created conversation
    """
    conversation = Conversation()
    convo_doc_db_objects = [
        ConversationDocument(document_id=doc_id, conversation=conversation)
        for doc_id in convo_payload.document_ids
    ]
    db.add(conversation)
    db.add_all(convo_doc_db_objects)
    await db.commit()
    await db.refresh(conversation)
    return await fetch_conversation_with_messages(db, conversation.id)


async def delete_conversation(db: AsyncSession, conversation_id: str) -> bool:
    """
    Delete a conversation and all associated records.
    
    Process:
        1. Builds delete statement for conversation
        2. Executes delete (cascades to related records)
        3. Commits transaction
    """
    stmt = delete(Conversation).where(Conversation.id == conversation_id)
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0


async def fetch_message_with_sub_processes(
    db: AsyncSession, message_id: str
) -> Optional[schema.Message]:
    """
    Retrieve a message with all its subprocess records.
    
    Process:
        1. Builds query with eager loading for:
           - Message subprocesses
        2. Executes query and gets first result
        3. Returns None if message not found
    """
    # Eagerly load required relationships
    stmt = (
        select(Message)
        .options(joinedload(Message.sub_processes))
        .where(Message.id == message_id)
    )
    result = await db.execute(stmt)  # execute the statement
    message = result.scalars().first()  # get the first result
    if message is not None:
        return schema.Message.from_orm(message)
    return None


async def fetch_documents(
    db: AsyncSession,
    id: Optional[str] = None,
    ids: Optional[List[str]] = None,
    url: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[schema.Document]:
    """
    Flexible document retrieval with multiple filter options.
    
    Process:
        1. Builds base query for documents
        2. Applies filters if provided:
           - Single ID lookup
           - Multiple IDs lookup
           - URL lookup
        3. Applies optional result limit
        4. Executes query and returns results
    """
    stmt = select(Document)
    if id is not None:
        stmt = stmt.where(Document.id == id)
        limit = 1
    elif ids is not None:
        stmt = stmt.where(Document.id.in_(ids))
    if url is not None:
        stmt = stmt.where(Document.url == url)
    if limit is not None:
        stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    documents = result.scalars().all()
    return [schema.Document.from_orm(doc) for doc in documents]


async def upsert_document_by_url(
    db: AsyncSession, document: schema.Document
) -> schema.Document:
    """
    Create or update a document based on its URL.
    
    Process:
        1. Builds upsert statement with:
           - All document fields for insert
           - Metadata update on conflict
        2. Uses URL as unique constraint
        3. Returns inserted/updated document
        4. Commits transaction
        
    Note:
        This only handles database operations.
        Document processing and embedding happens lazily
        when document is first used in conversation.
    """
    stmt = insert(Document).values(**document.dict(exclude_none=True))
    stmt = stmt.on_conflict_do_update(
        index_elements=[Document.url],
        set_=document.dict(include={"metadata_map"}),
    )
    stmt = stmt.returning(Document)
    result = await db.execute(stmt)
    upserted_doc = schema.Document.from_orm(result.scalars().first())
    await db.commit()
    return upserted_doc
