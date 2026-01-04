import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from app.config import settings

logger = logging.getLogger(__name__)

@asynccontextmanager
async def get_checkpointer() -> AsyncGenerator[AsyncPostgresSaver, None]:
    """
    Yields an AsyncPostgresSaver context manager for LangGraph.
    This manages the connection pool lifecycle.
    """
    # Create the connection string from settings (ensure it's async compatible if needed, 
    # though AsyncPostgresSaver typically uses psycopg 3 or asyncpg)
    # The current settings.database_url is likely in format: postgresql://user:pass@host:port/db
    # AsyncPostgresSaver works well with psycopg (v3) usually.
    # Note: langgraph-checkpoint-postgres dependencies might vary. 
    # Defaulting to psycopg 3 usage if available or using parameters as documented.
    
    # We will use the standard connection string.
    # Adjust schema if you need to use a specific schema or table names.
    
    async with AsyncPostgresSaver.from_conn_string(settings.DATABASE_URL) as checkpointer:
        yield checkpointer

# Alternative: Singleton pool management if we want to share the pool across requests widely
# But for now, the async context manager approach is clean for dependency injection or startup/shutdown.
