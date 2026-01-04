from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Workflow
import openai
from app.config import settings

class SemanticCache:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)

    async def get_embedding(self, text: str):
        response = await self.client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        return response.data[0].embedding

    async def find_similar_workflow(self, text: str, threshold: float = 0.95):
        embedding = await self.get_embedding(text)
        
        # PGVector l2_distance or cosine_distance
        # We need cosine similarity. PGVector operator <=> is cosine distance
        # Similarity = 1 - Distance
        # So we want distance < (1 - threshold)
        
        limit_distance = 1 - threshold
        
        stmt = select(Workflow).order_by(
            Workflow.request_embedding.cosine_distance(embedding)
        ).limit(1)
        
        result = await self.db.execute(stmt)
        workflow = result.scalar_one_or_none()
        
        if workflow and workflow.final_output:
            # Check actual distance manually or trust the order_by + post-verification
            # It's better to filter in the query but cosine_distance isn't always easy to filter on directly in all pgvector versions
            # Let's verify manually for safety? No, let's trust the logic if we filter
             
             # Re-fetch with filter if needed, or just return top 1 and check distance in python?
             # Actually, let's just use the embedding.
             pass
             
        stmt_filtered = select(Workflow).filter(
            Workflow.request_embedding.cosine_distance(embedding) < limit_distance
        ).filter(
            Workflow.status == "completed"
        ).order_by(
            Workflow.request_embedding.cosine_distance(embedding)
        ).limit(1)

        result = await self.db.execute(stmt_filtered)
        return result.scalar_one_or_none()
