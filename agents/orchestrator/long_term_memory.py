"""Orchestrator — Long-term memory via pgvector for solution RAG.

Stores and retrieves past agent resolutions as embeddings.
When a new complaint/request arrives, searches for similar past solutions
to provide context to the specialist agent.

Schema (in outbox schema, shared across services):
  Table: outbox.solution_embeddings
    - id UUID PK
    - domain TEXT (billing, network, campaign, customer_support)
    - summary TEXT
    - resolution TEXT
    - embedding VECTOR(1536)
    - metadata JSONB
    - created_at TIMESTAMPTZ
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from shared.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SolutionMemory:
    """Long-term memory for agent solutions using pgvector.

    Provides RAG (Retrieval-Augmented Generation) capabilities:
    - Store past resolutions with embeddings
    - Search similar past solutions for new requests
    - Enrich agent context with relevant history
    """

    def __init__(self) -> None:
        self._session_factory = None

    async def _get_session(self):
        if self._session_factory is None:
            from shared.utils.database import async_session_factory

            self._session_factory = async_session_factory
        return self._session_factory()

    async def ensure_table(self) -> None:
        """Create the solution_embeddings table if it doesn't exist."""
        from sqlalchemy import text

        async with await self._get_session() as session:
            await session.execute(
                text("""
                    CREATE TABLE IF NOT EXISTS outbox.solution_embeddings (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        domain TEXT NOT NULL,
                        summary TEXT NOT NULL,
                        resolution TEXT NOT NULL,
                        embedding VECTOR(1536),
                        metadata JSONB DEFAULT '{}',
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """)
            )
            # Create index for vector similarity search
            await session.execute(
                text("""
                    CREATE INDEX IF NOT EXISTS idx_solution_embeddings_vector
                    ON outbox.solution_embeddings
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 10)
                """)
            )
            await session.commit()
            logger.info("solution_embeddings table ensured")

    async def store_solution(
        self,
        domain: str,
        summary: str,
        resolution: str,
        metadata: dict[str, Any] | None = None,
        embedding: list[float] | None = None,
    ) -> str:
        """Store a past resolution for future RAG retrieval.

        If no embedding is provided, the solution is stored without vector
        (can be backfilled later via batch embedding job).
        """
        from sqlalchemy import text

        solution_id = str(uuid.uuid4())
        async with await self._get_session() as session:
            if embedding:
                await session.execute(
                    text("""
                        INSERT INTO outbox.solution_embeddings (id, domain, summary, resolution, embedding, metadata)
                        VALUES (:id, :domain, :summary, :resolution, :embedding::vector, :metadata::jsonb)
                    """),
                    {
                        "id": solution_id,
                        "domain": domain,
                        "summary": summary,
                        "resolution": resolution,
                        "embedding": str(embedding),
                        "metadata": json.dumps(metadata or {}),
                    },
                )
            else:
                await session.execute(
                    text("""
                        INSERT INTO outbox.solution_embeddings (id, domain, summary, resolution, metadata)
                        VALUES (:id, :domain, :summary, :resolution, :metadata::jsonb)
                    """),
                    {
                        "id": solution_id,
                        "domain": domain,
                        "summary": summary,
                        "resolution": resolution,
                        "metadata": json.dumps(metadata or {}),
                    },
                )
            await session.commit()

        logger.info("solution_stored", extra={"id": solution_id, "domain": domain})
        return solution_id

    async def search_similar_solutions(
        self,
        embedding: list[float],
        domain: str | None = None,
        limit: int = 5,
        min_similarity: float = 0.7,
    ) -> list[dict[str, Any]]:
        """Search for similar past solutions using cosine similarity.

        Args:
            embedding: Query vector (1536-dim)
            domain: Optional domain filter
            limit: Max results to return
            min_similarity: Minimum cosine similarity threshold

        Returns:
            List of similar solutions with similarity scores
        """
        from sqlalchemy import text

        query = """
            SELECT id, domain, summary, resolution, metadata,
                   1 - (embedding <=> :embedding::vector) AS similarity
            FROM outbox.solution_embeddings
            WHERE embedding IS NOT NULL
        """
        params: dict[str, Any] = {"embedding": str(embedding), "limit": limit}

        if domain:
            query += " AND domain = :domain"
            params["domain"] = domain

        query += " ORDER BY embedding <=> :embedding::vector LIMIT :limit"

        async with await self._get_session() as session:
            result = await session.execute(text(query), params)
            rows = result.fetchall()

        solutions = []
        for row in rows:
            similarity = float(row.similarity)
            if similarity >= min_similarity:
                solutions.append(
                    {
                        "id": str(row.id),
                        "domain": row.domain,
                        "summary": row.summary,
                        "resolution": row.resolution,
                        "metadata": (
                            row.metadata
                            if isinstance(row.metadata, dict)
                            else json.loads(row.metadata or "{}")
                        ),
                        "similarity": round(similarity, 4),
                    }
                )

        return solutions

    async def get_context_for_request(
        self,
        description: str,
        domain: str | None = None,
        limit: int = 3,
    ) -> str:
        """Generate RAG context from similar past solutions.

        Attempts to embed the description and find similar solutions.
        Falls back to keyword-based context if embedding is not available.

        Returns formatted context string to prepend to the agent prompt.
        """
        # Try to generate embedding via LLM
        embedding = await self._generate_embedding(description)
        if embedding is None:
            return ""

        solutions = await self.search_similar_solutions(
            embedding=embedding,
            domain=domain,
            limit=limit,
        )

        if not solutions:
            return ""

        context_parts = ["--- Benzer Geçmiş Çözümler (RAG) ---"]
        for i, sol in enumerate(solutions, 1):
            context_parts.append(
                f"\n{i}. [Benzerlik: %{sol['similarity'] * 100:.0f}] ({sol['domain']})\n"
                f"   Sorun: {sol['summary']}\n"
                f"   Çözüm: {sol['resolution']}"
            )
        context_parts.append("\n--- Geçmiş çözümleri referans al ama her vakayı bağımsız değerlendir ---\n")

        return "\n".join(context_parts)

    async def _generate_embedding(self, text: str) -> list[float] | None:
        """Generate embedding for text using the LLM API.

        Uses OpenAI-compatible embedding endpoint.
        Returns None if embedding generation fails.
        """
        try:
            import httpx

            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{settings.openai_api_base}/embeddings",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                    json={"model": "text-embedding-ada-002", "input": text[:8000]},
                )
                resp.raise_for_status()
                data = resp.json()
                return data["data"][0]["embedding"]
        except Exception:
            logger.debug("embedding_generation_failed", exc_info=True)
            return None
