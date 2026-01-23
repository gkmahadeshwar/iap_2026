"""Synchronization between Notion and SQLite database."""

from notion_rag.chunker import SemanticChunker
from notion_rag.database import VectorDatabase
from notion_rag.embeddings import EmbeddingService
from notion_rag.models import Chunk
from notion_rag.notion_client import NotionClient


class NotionSync:
    """Synchronize posts from Notion to SQLite database."""

    def __init__(
        self,
        notion: NotionClient,
        db: VectorDatabase,
        embedder: EmbeddingService,
        chunker: SemanticChunker | None = None,
    ):
        """Initialize the sync service.

        Args:
            notion: Notion API client.
            db: Vector database.
            embedder: Embedding service.
            chunker: Text chunker (optional, uses default if not provided).
        """
        self.notion = notion
        self.db = db
        self.embedder = embedder
        self.chunker = chunker or SemanticChunker()

    def sync_all(self, verbose: bool = True) -> dict:
        """Sync all posts from Notion to the database.

        Args:
            verbose: Print progress messages.

        Returns:
            Dictionary with sync statistics.
        """
        if verbose:
            print("Fetching posts from Notion...")

        posts = self.notion.fetch_all_posts()

        if verbose:
            print(f"Found {len(posts)} posts in Notion")

        stats = {
            "total": len(posts),
            "synced": 0,
            "chunks_created": 0,
            "embeddings_created": 0,
            "errors": 0,
        }

        for post in posts:
            try:
                if verbose:
                    print(f"  Syncing: {post.title[:50]}...")

                # Upsert the post
                self.db.upsert_post(post)

                # Delete existing chunks for this post
                self.db.delete_chunks_for_post(post.id)

                # Chunk the content
                chunks = self.chunker.chunk(post.content)

                if not chunks:
                    # If no chunks, use the full content
                    chunks = [post.content]

                # Create new chunks and embeddings
                chunk_texts = []
                chunk_ids = []

                for i, chunk_text in enumerate(chunks):
                    chunk = Chunk(
                        post_id=post.id,
                        chunk_index=i,
                        content=chunk_text,
                    )
                    chunk_id = self.db.insert_chunk(chunk)
                    chunk_ids.append(chunk_id)
                    chunk_texts.append(chunk_text)
                    stats["chunks_created"] += 1

                # Generate embeddings in batch
                if chunk_texts:
                    embeddings = self.embedder.embed(chunk_texts)

                    for chunk_id, embedding in zip(chunk_ids, embeddings):
                        self.db.store_embedding(chunk_id, embedding)
                        stats["embeddings_created"] += 1

                stats["synced"] += 1

            except Exception as e:
                if verbose:
                    print(f"    Error syncing post {post.id}: {e}")
                stats["errors"] += 1

        if verbose:
            print(f"\nSync complete:")
            print(f"  Posts synced: {stats['synced']}/{stats['total']}")
            print(f"  Chunks created: {stats['chunks_created']}")
            print(f"  Embeddings created: {stats['embeddings_created']}")
            if stats["errors"]:
                print(f"  Errors: {stats['errors']}")

        return stats

    def sync_by_status(self, status: str, verbose: bool = True) -> dict:
        """Sync only posts with a specific status.

        Args:
            status: Status to filter by (e.g., "Ready").
            verbose: Print progress messages.

        Returns:
            Dictionary with sync statistics.
        """
        if verbose:
            print(f"Fetching posts with status '{status}' from Notion...")

        posts = self.notion.fetch_posts_by_status(status)

        if verbose:
            print(f"Found {len(posts)} posts")

        stats = {
            "total": len(posts),
            "synced": 0,
            "chunks_created": 0,
            "embeddings_created": 0,
            "errors": 0,
        }

        for post in posts:
            try:
                if verbose:
                    print(f"  Syncing: {post.title[:50]}...")

                # Upsert the post
                self.db.upsert_post(post)

                # Delete existing chunks for this post
                self.db.delete_chunks_for_post(post.id)

                # Chunk the content
                chunks = self.chunker.chunk(post.content)

                if not chunks:
                    chunks = [post.content]

                # Create new chunks and embeddings
                chunk_texts = []
                chunk_ids = []

                for i, chunk_text in enumerate(chunks):
                    chunk = Chunk(
                        post_id=post.id,
                        chunk_index=i,
                        content=chunk_text,
                    )
                    chunk_id = self.db.insert_chunk(chunk)
                    chunk_ids.append(chunk_id)
                    chunk_texts.append(chunk_text)
                    stats["chunks_created"] += 1

                # Generate embeddings in batch
                if chunk_texts:
                    embeddings = self.embedder.embed(chunk_texts)

                    for chunk_id, embedding in zip(chunk_ids, embeddings):
                        self.db.store_embedding(chunk_id, embedding)
                        stats["embeddings_created"] += 1

                stats["synced"] += 1

            except Exception as e:
                if verbose:
                    print(f"    Error syncing post {post.id}: {e}")
                stats["errors"] += 1

        if verbose:
            print(f"\nSync complete:")
            print(f"  Posts synced: {stats['synced']}/{stats['total']}")
            print(f"  Chunks created: {stats['chunks_created']}")
            print(f"  Embeddings created: {stats['embeddings_created']}")
            if stats["errors"]:
                print(f"  Errors: {stats['errors']}")

        return stats
