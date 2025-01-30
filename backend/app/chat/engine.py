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
from llama_index.vector_stores.types import VectorStore
from tempfile import TemporaryDirectory
import requests
import nest_asyncio
from datetime import timedelta
from cachetools import cached, TTLCache
from llama_index.readers.file.docs_reader import PDFReader
from llama_index.schema import Document as LlamaIndexDocument
from llama_index.agent import OpenAIAgent
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
from app.core.config import settings
from app.schema import (
    Message as MessageSchema,
    Document as DocumentSchema,
    Conversation as ConversationSchema,
    DocumentMetadataKeysEnum,
    SecDocumentMetadata,
)
from app.models.db import MessageRoleEnum, MessageStatusEnum
from app.chat.constants import (
    DB_DOC_ID_KEY,
    SYSTEM_MESSAGE,
    CLINICAL_SYSTEM_MESSAGE,
    NODE_PARSER_CHUNK_OVERLAP,
    NODE_PARSER_CHUNK_SIZE,
)
from app.chat.tools import get_api_query_engine_tool
from app.chat.utils import build_title_for_document
from app.chat.pg_vector import get_vector_store_singleton
from app.chat.qa_response_synth import get_custom_response_synth
from llama_index.retrievers import VectorIndexRetriever
from llama_index.response_synthesizers.factory import get_response_synthesizer


logger = logging.getLogger(__name__)


logger.info("Applying nested asyncio patch")
nest_asyncio.apply()

OPENAI_TOOL_LLM_NAME = "gpt-3.5-turbo-0613"
OPENAI_CHAT_LLM_NAME = "gpt-3.5-turbo-0613"


def get_s3_fs() -> AsyncFileSystem:
    """
Creates and returns an S3 filesystem interface.

Returns:
    AsyncFileSystem: An S3 filesystem object for S3/LocalStack interaction.
    
Side Effects:
    - Creates the S3 bucket if it doesn't exist
    - Uses LocalStack endpoint in development, real S3 in production
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
Downloads and processes a document from its URL.

Args:
    document (DocumentSchema): Document metadata including URL and type

Returns:
    List[LlamaIndexDocument]: Processed document nodes ready for indexing
    
Process:
    1. Downloads document to temporary directory
    2. Determines document type from metadata
    3. Uses appropriate processor (GuidelineProcessor/PDFReader)
    4. Processes document into nodes with metadata
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
    """Build a description for a document to be used in the tool metadata."""
    if DocumentMetadataKeysEnum.SEC_DOCUMENT in document.metadata_map:
        sec_metadata = SecDocumentMetadata.parse_obj(
            document.metadata_map[DocumentMetadataKeysEnum.SEC_DOCUMENT]
        )
        time_period = (
            f"{sec_metadata.year} Q{sec_metadata.quarter}"
            if sec_metadata.quarter
            else str(sec_metadata.year)
        )
        return f"A SEC {sec_metadata.doc_type.value} filing describing the financials of {sec_metadata.company_name} ({sec_metadata.company_ticker}) for the {time_period} time period."
    
    elif DocumentMetadataKeysEnum.CLINICAL_GUIDELINE in document.metadata_map:
        try:
            guideline = ClinicalGuidelineMetadata.parse_obj(
                document.metadata_map[DocumentMetadataKeysEnum.CLINICAL_GUIDELINE]
            )
            description = f"A clinical guideline titled '{guideline.title}' published by {guideline.issuing_organization}"
            
            if guideline.publication_date:
                description += f" in {guideline.publication_date.strftime('%Y')}"
            
            return description
        except (ValueError, AttributeError) as e:
            logger.warning(f"Error parsing clinical guideline metadata: {e}")
            return "A clinical guideline document."
    
    return "A document containing useful information that the user pre-selected to discuss with the assistant."


def get_chat_history(
    chat_messages: List[MessageSchema],
) -> List[ChatMessage]:
    """
    Given a list of chat messages, return a list of ChatMessage instances.

    Failed chat messages are filtered out and then the remaining ones are
    sorted by created_at.
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
    """Get the appropriate embedding model based on document type."""
    if document_type == "clinical_guideline":
        # Use text-embedding-3-large for clinical documents
        # It has better performance on domain-specific tasks than ada-002
        return OpenAIEmbedding(
            mode=OpenAIEmbeddingMode.SIMILARITY_MODE,
            model_type=OpenAIEmbeddingModelType.TEXT_EMBED_3_LARGE,
        )
    
    # Default to text-embed-ada-002 for SEC documents (maintains backwards compatibility)
    return OpenAIEmbedding(
        mode=OpenAIEmbeddingMode.SIMILARITY_MODE,
        model_type=OpenAIEmbeddingModelType.TEXT_EMBED_ADA_002,
    )


def get_tool_service_context(
    callback_handlers: List[BaseCallbackHandler],
) -> ServiceContext:
    llm = OpenAI(
        model=settings.MODEL_NAME,
        temperature=0.1,
        api_key=settings.OPENAI_API_KEY,
    )

    # Default to SEC document embedding model
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

    Args:
        service_context (ServiceContext): Context with LLM and callbacks
        documents (List[DocumentSchema]): Documents to index
        fs (Optional[AsyncFileSystem]): Optional filesystem
        
    Returns:
        Dict[str, VectorStoreIndex]: Mapping of document IDs to vector indices
        
    Process:
        For each document:
        1. Gets appropriate embedding model
        2. Creates document-specific service context
        3. Processes document into nodes
        4. Creates vector store index
    """
    persist_dir = f"{settings.S3_BUCKET_NAME}"
    vector_store = await get_vector_store_singleton()
    
    try:
        try:
            storage_context = get_storage_context(persist_dir, vector_store, fs=fs)
        except FileNotFoundError:
            logger.info("Could not find storage context in S3. Creating new storage context.")
            storage_context = StorageContext.from_defaults(vector_store=vector_store, fs=fs)
            storage_context.persist(persist_dir=persist_dir, fs=fs)
            
        index_ids = [str(doc.id) for doc in documents]
        indices = load_indices_from_storage(
            storage_context,
            index_ids=index_ids,
            service_context=service_context,
        )
        doc_id_to_index = dict(zip(index_ids, indices))
        logger.debug("Loaded indices from storage.")
        
    except ValueError:
        logger.error(
            "Failed to load indices from storage. Creating new indices. "
            "If you're running the seed_db script, this is normal and expected."
        )
        storage_context = StorageContext.from_defaults(
            persist_dir=persist_dir, vector_store=vector_store, fs=fs
        )
        
        doc_id_to_index = {}
        for document in documents:
            # Get document-specific embedding model
            document_type = document.metadata_map.get("document_type")
            embedding_model = get_embedding_model(document_type)
            
            # Create document-specific service context with appropriate embedding model
            doc_service_context = ServiceContext.from_defaults(
                llm=service_context.llm,
                embed_model=embedding_model,
                callback_manager=service_context.callback_manager,
            )
            
            llama_index_docs = fetch_and_read_document(document)
            index = VectorStoreIndex(
                nodes=llama_index_docs,
                storage_context=storage_context,
                service_context=doc_service_context,
            )
            index.set_index_id(str(document.id))
            index.storage_context.persist(persist_dir=persist_dir, fs=fs)
            doc_id_to_index[str(document.id)] = index
            
    return doc_id_to_index


def index_to_query_engine(doc_id: str, index: VectorStoreIndex, documents: List[DocumentSchema]) -> BaseQueryEngine:
    # Basic filters to ensure we only get nodes from this document
    base_filters = MetadataFilters(
        filters=[ExactMatchFilter(key=DB_DOC_ID_KEY, value=doc_id)]
    )
    
    """
    Creates a specialized query engine for a document based on its type.

    Args:
        doc_id (str): ID of the document to create query engine for
        index (VectorStoreIndex): Vector store index containing document nodes
        documents (List[DocumentSchema]): List of all documents for metadata lookup

    Returns:
        BaseQueryEngine: Configured query engine optimized for the document type
        
    Features:
        - Applies document-specific filters to ensure relevant nodes
        - Uses different similarity_top_k based on document type
        - Configures response synthesizer based on document type
        - Adds document metadata for better context
    """
    
    # Get a sample node to determine document type
    sample_nodes = index.docstore.get_nodes(node_ids=list(index.docstore.docs.keys())[:1])
    if sample_nodes and sample_nodes[0].metadata.get("document_type") == "clinical_guideline":
        from llama_index.query_engine import RetrieverQueryEngine
        from llama_index.retrievers import VectorIndexRetriever
        
        # Configure retriever for clinical guidelines
        retriever = VectorIndexRetriever(
            index=index,
            filters=base_filters,
            similarity_top_k=5,  # Get more context for clinical info
            # Additional parameters for clinical retrieval
            doc_ids=[doc_id],
            query_mode="hybrid"  # Use both semantic and keyword matching
        )
        
        # Get the clinical response synthesizer with clinical system message
        service_context = ServiceContext.from_defaults(
            system_prompt=CLINICAL_SYSTEM_MESSAGE.format(
                doc_titles="\n".join(
                    "- " + build_title_for_document(doc)
                    for doc in documents
                    if str(doc.id) == doc_id
                ),
                curr_date=datetime.now().strftime("%Y-%m-%d"),
            ),
            llm=index.service_context.llm,
            embed_model=index.service_context.embed_model,
            callback_manager=index.service_context.callback_manager,
        )
        
        response_synthesizer = get_clinical_response_synth(
            service_context=service_context,
            documents=[doc for doc in documents if str(doc.id) == doc_id]
        )
        
        return RetrieverQueryEngine(
            retriever=retriever,
            response_synthesizer=response_synthesizer
        )
    
    # For SEC documents, use the existing custom synthesizer with SEC system message
    response_synthesizer = get_custom_response_synth(
        service_context=index.service_context,
        documents=[doc for doc in documents if str(doc.id) == doc_id]
    )
    
    # Default query engine with custom synthesizer
    return index.as_query_engine(
        similarity_top_k=3,
        filters=base_filters,
        response_synthesizer=response_synthesizer
    )


@cached(
    TTLCache(maxsize=10, ttl=timedelta(minutes=5).total_seconds()),
    key=lambda *args, **kwargs: "global_storage_context",
)
def get_storage_context(
    persist_dir: str, vector_store: VectorStore, fs: Optional[AsyncFileSystem] = None
) -> StorageContext:
    """
    Creates or retrieves a cached storage context for vector storage.
    Note:
        - Cached for 300 seconds (5 minutes) to improve performance
        - Cache key combines persist_dir and vector_store identity
        - Supports optional filesystem for storage operations
    """
    logger.info("Creating new storage context.")
    return StorageContext.from_defaults(
        persist_dir=persist_dir, vector_store=vector_store, fs=fs
    )


async def get_chat_engine(
    callback_handler: BaseCallbackHandler,
    conversation: ConversationSchema,
) -> OpenAIAgent:
    
    """
    Creates a comprehensive chat engine for handling document-based conversations.

    Args:
        callback_handler (BaseCallbackHandler): Handler for managing chat callbacks
        conversation (ConversationSchema): Current conversation context and history

    Returns:
        OpenAIAgent: Fully configured chat agent ready to handle queries
        
    Process:
        1. Sets up service context with callback handler
        2. Initializes S3 filesystem for document access
        3. Creates vector indices for all conversation documents
        4. Builds query engines for each document
        5. Configures chat history and message handling
        6. Sets up system prompts and tools
        
    Features:
        - Handles multiple document types (SEC, Clinical)
        - Maintains conversation context
        - Uses document-specific embedding models
        - Provides specialized tools based on document types
        - Supports streaming responses
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

    qualitative_question_engine = SubQuestionQueryEngine.from_defaults(
        query_engine_tools=vector_query_engine_tools,
        service_context=service_context,
        response_synthesizer=response_synth,
        verbose=settings.VERBOSE,
        use_async=True,
    )

    api_query_engine_tools = [
        get_api_query_engine_tool(doc, service_context)
        for doc in conversation.documents
        if DocumentMetadataKeysEnum.SEC_DOCUMENT in doc.metadata_map
    ]

    quantitative_question_engine = SubQuestionQueryEngine.from_defaults(
        query_engine_tools=api_query_engine_tools,
        service_context=service_context,
        response_synthesizer=response_synth,
        verbose=settings.VERBOSE,
        use_async=True,
    )

    top_level_sub_tools = [
        QueryEngineTool(
            query_engine=qualitative_question_engine,
            metadata=ToolMetadata(
                name="qualitative_question_engine",
                description="""
A query engine that can answer qualitative questions about a set of SEC financial documents that the user pre-selected for the conversation.
Any questions about company-related headwinds, tailwinds, risks, sentiments, or administrative information should be asked here.
""".strip(),
            ),
        ),
        QueryEngineTool(
            query_engine=quantitative_question_engine,
            metadata=ToolMetadata(
                name="quantitative_question_engine",
                description="""
A query engine that can answer quantitative questions about a set of SEC financial documents that the user pre-selected for the conversation.
Any questions about company-related financials or other metrics should be asked here.
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
        doc_titles = "No documents selected."

    curr_date = datetime.utcnow().strftime("%Y-%m-%d")
    chat_engine = OpenAIAgent.from_tools(
        tools=top_level_sub_tools,
        llm=chat_llm,
        chat_history=chat_history,
        verbose=settings.VERBOSE,
        system_prompt=SYSTEM_MESSAGE.format(doc_titles=doc_titles, curr_date=curr_date),
        callback_manager=service_context.callback_manager,
        max_function_calls=3,
    )

    return chat_engine
