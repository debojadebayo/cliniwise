from app.clinical.document_processor import GuidelineProcessor
from typing import Dict, List, Optional
import logging
from pathlib import Path
from datetime import datetime
import s3fs
from fsspec.asyn import AsyncFileSystem
from llama_index import (
    ServiceContext,
    VectorStoreIndex,
    StorageContext,
    load_indices_from_storage,
)
from llama_index.vector_stores.types import VectorStore, MetadataFilters, ExactMatchFilter
from tempfile import TemporaryDirectory
import requests
import nest_asyncio
from datetime import timedelta
from cachetools import cached, TTLCache
from llama_index.readers.file.docs_reader import PDFReader
from llama_index.schema import Document as LlamaIndexDocument
from llama_index.llms import ChatMessage, OpenAI
from llama_index.embeddings.base import BaseEmbedding
from llama_index.embeddings.openai import (
    OpenAIEmbedding,
    OpenAIEmbeddingMode,
    OpenAIEmbeddingModelType,
)
from llama_index.llms.base import MessageRole
from llama_index.callbacks.base import BaseCallbackHandler, CallbackManager
from llama_index.tools import QueryEngineTool, ToolMetadata
from llama_index.query_engine import SubQuestionQueryEngine, RetrieverQueryEngine
from llama_index.indices.query.base import BaseQueryEngine
from llama_index.vector_stores.types import (
    MetadataFilters,
    ExactMatchFilter,
)
from llama_index.node_parser import SentenceSplitter
from llama_index.agent import OpenAIAgent
from app.core.config import settings
from app.schema import (
    Message as MessageSchema,
    Document as DocumentSchema,
    Conversation as ConversationSchema,
    DocumentMetadataKeysEnum,
    SecDocumentMetadata,
    ClinicalGuidelineMetadata,
)
from app.models.db import MessageRoleEnum, MessageStatusEnum
from app.chat.constants import (
    DB_DOC_ID_KEY,
    CLINICAL_SYSTEM_MESSAGE,
    NODE_PARSER_CHUNK_OVERLAP,
    NODE_PARSER_CHUNK_SIZE
)
from app.chat.utils import build_title_for_document
from app.chat.pg_vector import get_vector_store_singleton
from app.chat.qa_response_synth import get_custom_response_synth
from llama_index.retrievers import VectorIndexRetriever
from llama_index.response_synthesizers.factory import get_response_synthesizer

logger = logging.getLogger(__name__)

OPENAI_CHAT_LLM_NAME = "gpt-4-1106-preview"

logger.info("Applying nested asyncio patch")
nest_asyncio.apply()

OPENAI_TOOL_LLM_NAME = "gpt-4-1106-preview"


def get_s3_fs() -> AsyncFileSystem:
    """
    Creates and configures an S3 filesystem interface.
    
    Process:
        1. Determines if using LocalStack (development) or real S3 (production)
        2. Creates filesystem with appropriate endpoint and credentials
        3. Ensures target bucket exists
        4. Returns configured filesystem interface
    """
    s3 = s3fs.S3FileSystem(
        key=settings.AWS_KEY,
        secret=settings.AWS_SECRET,
        endpoint_url=settings.S3_ENDPOINT_URL,
    )
    if not (settings.RENDER or s3.exists(settings.S3_BUCKET_NAME)):
        s3.mkdir(settings.S3_BUCKET_NAME)
    return s3


def fetch_and_read_document(
    document: DocumentSchema,
) -> List[LlamaIndexDocument]:
    """
    Downloads and processes a document from its URL into indexable chunks.
    
    Process:
        1. Downloads document to temporary directory
        2. Determines document type from metadata
        3. For clinical guidelines:
           - Uses GuidelineProcessor with specialized chunking
           - Adds clinical metadata to each chunk
        4. For other documents:
           - Uses standard PDFReader
           - Adds basic document metadata
        5. Returns list of processed document chunks
    """
    with TemporaryDirectory() as temp_dir:
        temp_file_path = Path(temp_dir) / f"{str(document.id)}.pdf"
        # Download the file
        with open(temp_file_path, "wb") as temp_file:
            with requests.get(document.url, stream=True) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=8192):
                    temp_file.write(chunk)
            temp_file.seek(0)
        
        # Determine document type and process accordingly
        if DocumentMetadataKeysEnum.CLINICAL_GUIDELINE in document.metadata_map:
            # Process clinical guideline
            from app.clinical.document_processor import GuidelineProcessor
            processor = GuidelineProcessor()
            nodes = processor.process_document(
                temp_file_path,
                metadata={
                    DB_DOC_ID_KEY: str(document.id),
                    DocumentMetadataKeysEnum.CLINICAL_GUIDELINE: document.metadata_map[DocumentMetadataKeysEnum.CLINICAL_GUIDELINE]
                }
            )
            return nodes
        else:
            # Default PDF processing for other document types
            reader = PDFReader()
            return reader.load_data(
                temp_file_path, 
                extra_info={DB_DOC_ID_KEY: str(document.id)}
            )


def build_description_for_document(document: DocumentSchema) -> str:
    """
    Creates a human-readable description of a document for the chat interface.
    
    Process:
        1. Identifies document type from metadata
        2. For clinical guidelines:
           - Extracts title and issuing organization
           - Formats as medical guideline description
        3. Falls back to basic description if metadata missing
    """
    
    for DocumentMetadataKeysEnum.CLINICAL_GUIDELINE in document.metadata_map:
        clinical_metadata = ClinicalGuidelineMetadata.parse_obj(
            document.metadata_map[DocumentMetadataKeysEnum.CLINICAL_GUIDELINE]
        )
        return f"Clinical practice guidelines titled '{clinical_metadata.title}' from {clinical_metadata.issuing_organization}, published {clinical_metadata.publication_date.strftime('%Y') if clinical_metadata.publication_date else 'date not specified'}."
    
    return "A document containing useful information that the user pre-selected to discuss with the assistant."


def get_chat_history(
    chat_messages: List[MessageSchema],
) -> List[ChatMessage]:
    """
    Prepares chat history for the LLM conversation.
    
    Process:
        1. Filters out failed messages
        2. Sorts messages by creation time
        3. Converts to LlamaIndex ChatMessage format
        4. Preserves user/assistant roles
    """
    # pre-process chat messages
    chat_messages = [
        m for m in chat_messages
        if m.content.strip() and m.status == MessageStatusEnum.SUCCESS
    ]
    # TODO: could be a source of high CPU utilization
    chat_messages = sorted(chat_messages, key=lambda m: m.created_at)

    chat_history = []
    for message in chat_messages:
        role = (
            MessageRole.ASSISTANT
            if message.role == MessageRoleEnum.assistant
            else MessageRole.USER
        )
        chat_history.append(ChatMessage(content=message.content, role=role))

    return chat_history


def get_embedding_model(document_type: str = None) -> BaseEmbedding:
    """
    Selects appropriate embedding model based on document type.
    
    Process:
        1. Determines document category (clinical/financial)
        2. Configures embedding parameters:
           - Model type (text-embedding-ada-002)
           - Mode (text-search for documents)
           - Dimensions and other settings
        3. Returns configured embedding model
    """
    return OpenAIEmbedding(
        mode=OpenAIEmbeddingMode.SIMILARITY_MODE,
        model_type=OpenAIEmbeddingModelType.TEXT_EMBED_3_LARGE,
    )

def get_tool_service_context(
    callback_handlers: List[BaseCallbackHandler],
) -> ServiceContext:
    """
    Creates service context for document processing tools.
    
    Process:
        1. Configures LLM settings (temperature, model)
        2. Sets up callback manager for processing events
        3. Creates embedding model
        4. Returns context with all configurations
    """
    llm = OpenAI(
        model=settings.MODEL_NAME,
        temperature=0.1,
        api_key=settings.OPENAI_API_KEY,
    )

    embedding_model = get_embedding_model()

    callback_manager = CallbackManager(callback_handlers)

    return ServiceContext.from_defaults(
        llm=llm,
        embed_model=embedding_model,
        callback_manager=callback_manager,
    )


async def build_doc_id_to_index_map(
    service_context: ServiceContext,
    documents: List[DocumentSchema],
    fs: Optional[AsyncFileSystem] = None,
) -> Dict[str, VectorStoreIndex]:
    """
    Creates vector store indices for a list of documents.
    
    Process:
        1. For each document:
           - Gets appropriate embedding model
           - Creates document-specific service context
           - Downloads and processes document into nodes
           - Creates vector store index
        2. Caches indices for performance
        3. Returns mapping of document IDs to indices
    """
    persist_dir = f"{settings.S3_BUCKET_NAME}"
    vector_store = await get_vector_store_singleton()
    storage_context = get_storage_context(persist_dir, vector_store, fs=fs)
    
    doc_id_to_index = {}
    for document in documents:
        doc_id = str(document.id)
        
        # Get document-specific embedding model
        document_type = document.metadata_map.get("document_type")
        embedding_model = get_embedding_model(document_type)
        
        # Create document-specific service context with appropriate embedding model
        doc_service_context = ServiceContext.from_defaults(
            llm=service_context.llm,
            embed_model=embedding_model,
            callback_manager=service_context.callback_manager,
        )
        
        # Try to load existing index or create new one
        try:
            indices = load_indices_from_storage(
                storage_context,
                index_ids=[doc_id],
                service_context=doc_service_context,
            )
            if indices:
                doc_id_to_index[doc_id] = indices[0]
                logger.debug(f"Loaded existing index for document {doc_id}")
                continue
        except (ValueError, FileNotFoundError) as e:
            logger.info(f"Could not load index for document {doc_id}: {str(e)}")
        
        # Create new index if loading failed
        llama_index_docs = fetch_and_read_document(document)
        index = VectorStoreIndex(
            nodes=llama_index_docs,
            storage_context=storage_context,
            service_context=doc_service_context,
        )
        index.set_index_id(doc_id)
        index.storage_context.persist(persist_dir=persist_dir, fs=fs)
        doc_id_to_index[doc_id] = index
        logger.info(f"Created new index for document {doc_id}")
    
    return doc_id_to_index


def index_to_query_engine(
    doc_id: str, 
    index: VectorStoreIndex,
    documents: List[DocumentSchema]
) -> RetrieverQueryEngine:
    """
    Creates specialized query engine for a document.
    
    Process:
        1. Identifies document type and metadata
        2. Configures retriever with:
           - Document-specific filters
           - Similarity search parameters
        3. Sets up response synthesizer
        4. Returns optimized query engine
    """
    # Create retriever
    retriever = VectorIndexRetriever(
        index=index,
        similarity_top_k=3,
        vector_store_kwargs={
            "filter": MetadataFilters(
                filters=[
                    ExactMatchFilter(
                        key=DB_DOC_ID_KEY,
                        value=doc_id,
                    )
                ]
            )
        },
    )
    
    # Create response synthesizer
    response_synthesizer = get_custom_response_synth(
        service_context=index.service_context,
        documents=[doc for doc in documents if str(doc.id) == doc_id]
    )
    
    # Create query engine
    query_engine = RetrieverQueryEngine(
        retriever=retriever,
        response_synthesizer=response_synthesizer,
        callback_manager=index.service_context.callback_manager,
    )
    
    return query_engine


@cached(
    TTLCache(maxsize=10, ttl=timedelta(minutes=5).total_seconds()),
    key=lambda *args, **kwargs: f"storage_context_{args[0]}",  # Use persist_dir in cache key
)
def get_storage_context(
    persist_dir: str,
    vector_store: VectorStore,
    fs: Optional[AsyncFileSystem] = None
) -> StorageContext:
    """
    Creates or retrieves cached storage context.
    
    Process:
        1. Generates cache key from directory and store
        2. Checks TTL cache for existing context
        3. If not found:
           - Creates new context with vector store
           - Configures persistence settings
           - Caches for 5 minutes
        4. Returns ready-to-use context
    """
    logger.info("Creating storage context with vector store.")
    return StorageContext.from_defaults(
        persist_dir=persist_dir, 
        vector_store=vector_store, 
        fs=fs
    )


async def get_chat_engine(
    callback_handler: BaseCallbackHandler,
    conversation: ConversationSchema,
) -> OpenAIAgent:
    """
    Creates comprehensive chat engine for document-based conversations.
    
    Process:
        1. Sets up service context with callbacks
        2. Initializes S3 filesystem
        3. For each conversation document:
           - Creates vector indices
           - Builds specialized query engines
           - Configures document-specific tools
        4. Sets up chat history and context
        5. Configures system prompts
        6. Returns fully configured chat agent
    """
    service_context = get_tool_service_context([callback_handler])
    s3_fs = get_s3_fs()
    doc_id_to_index = await build_doc_id_to_index_map(
        service_context, conversation.documents, fs=s3_fs
    )
    id_to_doc: Dict[str, DocumentSchema] = {
        str(doc.id): doc for doc in conversation.documents
    }

    vector_query_engine_tools = [
        QueryEngineTool(
            query_engine=index_to_query_engine(doc_id, index, conversation.documents),
            metadata=ToolMetadata(
                name=doc_id,
                description=build_description_for_document(id_to_doc[doc_id]),
            ),
        )
        for doc_id, index in doc_id_to_index.items()
    ]

    response_synth = get_custom_response_synth(service_context, conversation.documents)

    clinical_query_engine = SubQuestionQueryEngine.from_defaults(
        query_engine_tools=vector_query_engine_tools,
        service_context=service_context,
        response_synthesizer=response_synth,
        verbose=settings.VERBOSE,
        use_async=True,
    )

    top_level_tools = [
        QueryEngineTool(
            query_engine=clinical_query_engine,
            metadata=ToolMetadata(
                name="clinical_guidelines",
                description="""
A query engine specialized for analyzing clinical practice guidelines. Use this for:
- Understanding clinical recommendations and their evidence levels
- Finding specific treatment protocols and procedures
- Identifying patient care guidelines and best practices
- Analyzing clinical outcomes and quality measures
""".strip(),
            ),
        ),
    ]

    chat_llm = OpenAI(
        temperature=0,
        model=OPENAI_CHAT_LLM_NAME,
        streaming=True,
        api_key=settings.OPENAI_API_KEY,
    )
    chat_messages: List[MessageSchema] = conversation.messages
    chat_history = get_chat_history(chat_messages)
    logger.debug("Chat history: %s", chat_history)

    if conversation.documents:
        doc_titles = "\n".join(
            "- " + build_title_for_document(doc) for doc in conversation.documents
        )
    else:
        doc_titles = "No clinical guidelines selected."

    curr_date = datetime.utcnow().strftime("%Y-%m-%d")
    chat_engine = OpenAIAgent.from_tools(
        tools=top_level_tools,
        llm=chat_llm,
        chat_history=chat_history,
        verbose=settings.VERBOSE,
        system_prompt=CLINICAL_SYSTEM_MESSAGE.format(doc_titles=doc_titles, curr_date=curr_date),
        callback_manager=service_context.callback_manager,
        max_function_calls=3,
    )

    return chat_engine
