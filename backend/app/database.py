"""
Database connection and session management using SQLAlchemy.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Ensure connection string uses async driver
DATABASE_URL = settings.database_url
if "postgresql+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Create async database engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=10,
    max_overflow=20
)

# Application-wide session factory
AsyncSessionLocal = sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    autoflush=False
)

# Base class for ORM models - REMOVED (Circular import risk if Base imported from here)
# Base is actually imported from here in models.py? 
# Wait, models.py imports Base from app.database.
# So we need to keep Base here.
from sqlalchemy.orm import declarative_base
Base = declarative_base()

async def get_db():
    """
    Dependency function for FastAPI routes.
    Provides an async database session and ensures it's closed after use.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
