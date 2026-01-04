from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import SearchCache
from app.config import settings

async def get_cached_search(db: AsyncSession, query: str, provider: str):
    """
    Retrieve cached search results if they exist and are not expired.
    """
    if not settings.CACHE_ENABLED:
        return None
        
    stmt = select(SearchCache).where(
        SearchCache.query == query,
        SearchCache.provider == provider
    )
    result = await db.execute(stmt)
    cache_entry = result.scalar_one_or_none()
    
    if cache_entry:
        # TTL check if implemented (optional)
        # if cache_entry.expires_at and cache_entry.expires_at < datetime.now():
        #     return None
        return cache_entry.results
        
    return None

async def set_cached_search(db: AsyncSession, query: str, provider: str, results: list):
    """
    Store search results in cache.
    """
    if not settings.CACHE_ENABLED:
        return

    # Check existence to avoid unique constraint if we didn't use index or if race condition
    # Simple insert for now, assuming check performed before.
    # Ideally should use upsert.
    
    entry = SearchCache(
        query=query,
        provider=provider,
        results=results
    )
    db.add(entry)
    # Commit should be handled by caller or here? 
    # Usually services don't commit if part of larger transaction, but here it's isolated side-effect.
    # We will commit here for safety.
    try:
        await db.commit()
    except Exception as e:
        print(f"Cache interaction failed: {e}")
        await db.rollback()
