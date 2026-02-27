"""Customer Service — pgvector integration for embedding storage.

Stores customer profile embeddings for:
- Similar customer retrieval (find customers with similar profiles/issues)
- Solution similarity search (find how similar issues were resolved)

pgvector is used here because embeddings live in the same PostgreSQL instance.
For high-volume semantic search, Qdrant is used instead (see shared/utils/qdrant.py).
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class CustomerVectorStore:
    """Stores and retrieves customer profile embeddings via pgvector."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_profile_embedding(
        self,
        customer_id: str,
        embedding: list[float],
    ) -> None:
        """Store/update customer profile embedding (1536-dim for OpenAI/DeepSeek)."""
        await self._session.execute(
            text("""
                UPDATE customer.customers
                SET profile_embedding = :embedding::vector
                WHERE id = :customer_id::uuid
            """),
            {
                "customer_id": customer_id,
                "embedding": str(embedding),  # pgvector accepts list as string
            },
        )

    async def find_similar_customers(
        self,
        embedding: list[float],
        limit: int = 5,
    ) -> list[dict]:
        """Find customers with similar profiles using cosine distance."""
        result = await self._session.execute(
            text("""
                SELECT id, name, segment, clv_score,
                       1 - (profile_embedding <=> :embedding::vector) AS similarity
                FROM customer.customers
                WHERE profile_embedding IS NOT NULL
                ORDER BY profile_embedding <=> :embedding::vector
                LIMIT :limit
            """),
            {"embedding": str(embedding), "limit": limit},
        )
        rows = result.fetchall()
        return [
            {
                "id": str(row.id),
                "name": row.name,
                "segment": row.segment,
                "clv_score": row.clv_score,
                "similarity": float(row.similarity),
            }
            for row in rows
        ]
