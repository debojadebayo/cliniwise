from llama_index.vector_stores.types import VectorStore
from llama_index.vector_stores.postgres import PGVectorStore
from sqlalchemy.engine import make_url
from app.db.session import SessionLocal as AppSessionLocal, engine as app_engine
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

singleton_instance = None
did_run_setup = False


class CustomPGVectorStore(PGVectorStore):
    """
    Custom PostgreSQL vector store that shares connection pool with the main application.
    
    Features:
        - Uses pgvector extension for efficient similarity search
        - Shares database connection pool with FastAPI app
        - Handles async operations for better performance
        - Implements singleton pattern to prevent multiple instances
    """

    def _connect(self) -> None:
        """
        Configure database connections.
        
        Process:
            1. Creates standard SQLAlchemy engine for sync operations
            2. Uses app's async engine and session for async operations
            3. Shares connection pool with main application
        """
        self._engine = create_engine(self.connection_string)
        self._session = sessionmaker(self._engine)

        # Use our existing app engine and session so we can use the same connection pool
        self._async_engine = app_engine
        self._async_session = AppSessionLocal

    async def close(self) -> None:
        """
        Clean up database connections.
        
        Process:
            1. Closes all active sessions
            2. Disposes sync engine
            3. Disposes async engine
        """
        self._session.close_all()
        self._engine.dispose()

        await self._async_engine.dispose()

    def _create_tables_if_not_exists(self) -> None:
        """
        Disabled table creation as it's handled in run_setup.
        Tables are created with proper async context.
        """
        pass

    def _create_extension(self) -> None:
        """
        Disabled extension creation as it's handled in run_setup.
        Extension is created with proper async context.
        """
        pass

    async def run_setup(self) -> None:
        """
        Initialize vector store database components.
        
        Process:
            1. Checks if setup was already run
            2. Creates vector extension if not exists
            3. Creates necessary tables and indices
            4. Uses async operations for all database setup
            
        Note:
            This is called automatically when vector store is first used.
            Setup operations are only performed once per application lifecycle.
        """
        global did_run_setup
        if did_run_setup:
            return
        self._initialize()
        async with self._async_session() as session:
            async with session.begin():
                statement = sqlalchemy.text("CREATE EXTENSION IF NOT EXISTS vector")
                await session.execute(statement)
                await session.commit()

        async with self._async_session() as session:
            async with session.begin():
                conn = await session.connection()
                await conn.run_sync(self._base.metadata.create_all)
        did_run_setup = True


async def get_vector_store_singleton() -> VectorStore:
    """
    Get or create the vector store instance.
    
    Process:
        1. Checks for existing instance
        2. If none exists:
           - Creates new CustomPGVectorStore
           - Configures with database settings
           - Sets up vector extension and tables
        3. Returns singleton instance
        
    Returns:
        VectorStore: Configured vector store instance
        
    Note:
        Uses singleton pattern to ensure only one vector store
        instance exists across the application.
    """
    global singleton_instance
    if singleton_instance is not None:
        return singleton_instance
    url = make_url(settings.DATABASE_URL)
    singleton_instance = CustomPGVectorStore.from_params(
        url.host,
        url.port or 5432,
        url.database,
        url.username,
        url.password,
        settings.VECTOR_STORE_TABLE_NAME,
    )
    return singleton_instance
