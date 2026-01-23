"""RAG query interface."""

from notion_rag.database import VectorDatabase
from notion_rag.embeddings import EmbeddingService
from notion_rag.hybrid_search import HybridSearch
from notion_rag.models import Post, SearchResult


class RAG:
    """RAG (Retrieval Augmented Generation) query interface.

    Provides a high-level interface for searching and retrieving
    relevant posts from the database.
    """

    def __init__(
        self,
        db: VectorDatabase,
        embedder: EmbeddingService,
        alpha: float = 0.5,
    ):
        """Initialize RAG.

        Args:
            db: Vector database.
            embedder: Embedding service.
            alpha: Weight for hybrid search (0=BM25 only, 1=semantic only).
        """
        self.db = db
        self.embedder = embedder
        self.search = HybridSearch(db, embedder, alpha=alpha)

    def query(self, query: str, limit: int = 5) -> list[dict]:
        """Query the database and return relevant posts with context.

        Args:
            query: Search query.
            limit: Maximum number of results.

        Returns:
            List of dictionaries containing post info and relevance scores.
        """
        results = self.search.search(query, limit=limit)

        # Group by post and get full post info
        seen_posts: set[str] = set()
        output = []

        for result in results:
            if result.post_id in seen_posts:
                continue
            seen_posts.add(result.post_id)

            post = self.db.get_post(result.post_id)
            if post:
                output.append(
                    {
                        "post": post,
                        "matched_chunk": result.content,
                        "score": result.score,
                        "bm25_score": result.bm25_score,
                        "semantic_score": result.semantic_score,
                    }
                )

        return output

    def get_context(self, query: str, limit: int = 3) -> str:
        """Get context string for LLM augmentation.

        Args:
            query: Search query.
            limit: Maximum number of posts to include.

        Returns:
            Formatted context string for LLM prompt.
        """
        results = self.query(query, limit=limit)

        if not results:
            return "No relevant context found."

        context_parts = []
        for i, result in enumerate(results, 1):
            post: Post = result["post"]
            context_parts.append(
                f"[{i}] {post.title}\n"
                f"Category: {post.category or 'N/A'}\n"
                f"Content: {post.content}\n"
            )

        return "\n---\n".join(context_parts)

    def find_similar(self, post_id: str, limit: int = 5) -> list[SearchResult]:
        """Find posts similar to a given post.

        Args:
            post_id: ID of the reference post.
            limit: Maximum number of similar posts.

        Returns:
            List of similar search results.
        """
        post = self.db.get_post(post_id)
        if not post:
            return []

        # Search using the post's content
        results = self.search.search(post.content, limit=limit + 1)

        # Filter out the original post
        return [r for r in results if r.post_id != post_id][:limit]
