"""Hybrid search combining BM25 and semantic search."""

from notion_rag.database import VectorDatabase
from notion_rag.embeddings import EmbeddingService
from notion_rag.models import SearchResult


class HybridSearch:
    """Combine BM25 keyword search with semantic vector search.

    Uses Reciprocal Rank Fusion (RRF) to merge results from both
    search methods with configurable weighting.
    """

    def __init__(
        self,
        db: VectorDatabase,
        embedder: EmbeddingService,
        alpha: float = 0.5,
        rrf_k: int = 60,
    ):
        """Initialize hybrid search.

        Args:
            db: Vector database for search.
            embedder: Embedding service for query vectors.
            alpha: Weight for semantic search (0=BM25 only, 1=semantic only).
            rrf_k: Constant for RRF formula (default 60).
        """
        self.db = db
        self.embedder = embedder
        self.alpha = alpha
        self.rrf_k = rrf_k

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Perform hybrid search.

        Args:
            query: Search query string.
            limit: Maximum number of results to return.

        Returns:
            List of SearchResult objects sorted by combined score.
        """
        # Get more results than needed for better fusion
        fetch_limit = limit * 3

        # BM25 search
        bm25_results = self.db.fts_search(query, limit=fetch_limit)

        # Semantic search (if vector search is available)
        if self.db.vec_enabled:
            query_embedding = self.embedder.embed_single(query)
            semantic_results = self.db.vector_search(query_embedding, limit=fetch_limit)
        else:
            semantic_results = []

        # Fuse results
        if not semantic_results:
            # Fall back to BM25 only
            return bm25_results[:limit]

        if not bm25_results:
            # Fall back to semantic only
            return semantic_results[:limit]

        return self._reciprocal_rank_fusion(bm25_results, semantic_results, limit)

    def _reciprocal_rank_fusion(
        self,
        bm25_results: list[SearchResult],
        semantic_results: list[SearchResult],
        limit: int,
    ) -> list[SearchResult]:
        """Combine results using Reciprocal Rank Fusion.

        RRF formula: score = sum(1 / (k + rank)) across all rankings

        Args:
            bm25_results: Results from BM25 search.
            semantic_results: Results from semantic search.
            limit: Maximum results to return.

        Returns:
            Fused and ranked results.
        """
        # Create score dictionaries
        scores: dict[int, dict] = {}  # chunk_id -> {rrf_score, result, bm25, semantic}

        # Add BM25 results with weighted RRF score
        bm25_weight = 1.0 - self.alpha
        for rank, result in enumerate(bm25_results, 1):
            rrf_score = bm25_weight * (1.0 / (self.rrf_k + rank))
            scores[result.chunk_id] = {
                "rrf_score": rrf_score,
                "result": result,
                "bm25_rank": rank,
                "bm25_score": result.bm25_score,
                "semantic_rank": None,
                "semantic_score": None,
            }

        # Add semantic results with weighted RRF score
        semantic_weight = self.alpha
        for rank, result in enumerate(semantic_results, 1):
            rrf_score = semantic_weight * (1.0 / (self.rrf_k + rank))

            if result.chunk_id in scores:
                # Combine scores
                scores[result.chunk_id]["rrf_score"] += rrf_score
                scores[result.chunk_id]["semantic_rank"] = rank
                scores[result.chunk_id]["semantic_score"] = result.semantic_score
            else:
                scores[result.chunk_id] = {
                    "rrf_score": rrf_score,
                    "result": result,
                    "bm25_rank": None,
                    "bm25_score": None,
                    "semantic_rank": rank,
                    "semantic_score": result.semantic_score,
                }

        # Sort by combined RRF score
        sorted_items = sorted(
            scores.items(), key=lambda x: x[1]["rrf_score"], reverse=True
        )

        # Build final results
        results = []
        for chunk_id, data in sorted_items[:limit]:
            result = data["result"]
            results.append(
                SearchResult(
                    chunk_id=result.chunk_id,
                    post_id=result.post_id,
                    content=result.content,
                    score=data["rrf_score"],
                    bm25_score=data["bm25_score"],
                    semantic_score=data["semantic_score"],
                    title=result.title,
                    category=result.category,
                )
            )

        return results

    def search_bm25_only(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Search using only BM25 (keyword matching).

        Args:
            query: Search query string.
            limit: Maximum number of results.

        Returns:
            List of SearchResult objects.
        """
        return self.db.fts_search(query, limit=limit)

    def search_semantic_only(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Search using only semantic similarity.

        Args:
            query: Search query string.
            limit: Maximum number of results.

        Returns:
            List of SearchResult objects.
        """
        if not self.db.vec_enabled:
            raise RuntimeError("Vector search is not available")

        query_embedding = self.embedder.embed_single(query)
        return self.db.vector_search(query_embedding, limit=limit)
