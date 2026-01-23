"""SQLite database with FTS5 and vector search support."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np

from notion_rag.models import Chunk, Post, SearchResult


class VectorDatabase:
    """SQLite database with FTS5 for BM25 and sqlite-vec for vector search."""

    SCHEMA = """
    -- Main posts table
    CREATE TABLE IF NOT EXISTS posts (
        id TEXT PRIMARY KEY,
        notion_url TEXT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        category TEXT,
        hashtags TEXT,
        status TEXT DEFAULT 'draft',
        posted_at TIMESTAMP,
        mastodon_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Chunks table
    CREATE TABLE IF NOT EXISTS chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id TEXT NOT NULL,
        chunk_index INTEGER NOT NULL,
        content TEXT NOT NULL,
        FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
    );

    -- FTS5 for BM25 keyword search
    CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
        content,
        content='chunks',
        content_rowid='id'
    );

    -- Triggers to keep FTS in sync
    CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
        INSERT INTO chunks_fts(rowid, content) VALUES (new.id, new.content);
    END;

    CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
        INSERT INTO chunks_fts(chunks_fts, rowid, content) VALUES('delete', old.id, old.content);
    END;

    CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
        INSERT INTO chunks_fts(chunks_fts, rowid, content) VALUES('delete', old.id, old.content);
        INSERT INTO chunks_fts(rowid, content) VALUES (new.id, new.content);
    END;
    """

    def __init__(self, db_path: str | Path):
        """Initialize the database connection."""
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None
        self._vec_enabled = False

    def connect(self) -> None:
        """Connect to the database and load extensions."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

        # Try to load sqlite-vec extension
        try:
            self.conn.enable_load_extension(True)
            # Try common paths for sqlite-vec
            try:
                import sqlite_vec

                sqlite_vec.load(self.conn)
                self._vec_enabled = True
            except ImportError:
                # Try loading as extension directly
                self.conn.load_extension("vec0")
                self._vec_enabled = True
        except Exception as e:
            print(f"Warning: sqlite-vec not available: {e}")
            print("Vector search will be disabled. Install with: pip install sqlite-vec")
            self._vec_enabled = False

    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def initialize_schema(self) -> None:
        """Create database schema."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        # Create main tables and FTS
        self.conn.executescript(self.SCHEMA)

        # Create vector table if extension is available
        if self._vec_enabled:
            try:
                self.conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS embeddings USING vec0(
                        chunk_id INTEGER PRIMARY KEY,
                        embedding FLOAT[384]
                    )
                """)
            except sqlite3.OperationalError as e:
                print(f"Warning: Could not create embeddings table: {e}")
                self._vec_enabled = False

        self.conn.commit()

    def upsert_post(self, post: Post) -> None:
        """Insert or update a post."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        self.conn.execute(
            """
            INSERT INTO posts (id, notion_url, title, content, category, hashtags,
                             status, posted_at, mastodon_url, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                notion_url = excluded.notion_url,
                title = excluded.title,
                content = excluded.content,
                category = excluded.category,
                hashtags = excluded.hashtags,
                status = excluded.status,
                posted_at = excluded.posted_at,
                mastodon_url = excluded.mastodon_url,
                updated_at = excluded.updated_at
            """,
            (
                post.id,
                post.notion_url,
                post.title,
                post.content,
                post.category,
                json.dumps(post.hashtags),
                post.status,
                post.posted_at.isoformat() if post.posted_at else None,
                post.mastodon_url,
                post.created_at.isoformat(),
                post.updated_at.isoformat(),
            ),
        )
        self.conn.commit()

    def get_post(self, post_id: str) -> Optional[Post]:
        """Get a post by ID."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        row = self.conn.execute(
            "SELECT * FROM posts WHERE id = ?", (post_id,)
        ).fetchone()

        if not row:
            return None

        return self._row_to_post(row)

    def get_post_by_status(self, status: str) -> list[Post]:
        """Get all posts with a given status."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        rows = self.conn.execute(
            "SELECT * FROM posts WHERE status = ?", (status,)
        ).fetchall()

        return [self._row_to_post(row) for row in rows]

    def _row_to_post(self, row: sqlite3.Row) -> Post:
        """Convert a database row to a Post model."""
        return Post(
            id=row["id"],
            notion_url=row["notion_url"],
            title=row["title"],
            content=row["content"],
            category=row["category"],
            hashtags=json.loads(row["hashtags"]) if row["hashtags"] else [],
            status=row["status"],
            posted_at=datetime.fromisoformat(row["posted_at"])
            if row["posted_at"]
            else None,
            mastodon_url=row["mastodon_url"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def delete_chunks_for_post(self, post_id: str) -> None:
        """Delete all chunks for a post."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        # Get chunk IDs first to delete embeddings
        chunk_ids = [
            row[0]
            for row in self.conn.execute(
                "SELECT id FROM chunks WHERE post_id = ?", (post_id,)
            ).fetchall()
        ]

        # Delete embeddings
        if self._vec_enabled and chunk_ids:
            for chunk_id in chunk_ids:
                try:
                    self.conn.execute(
                        "DELETE FROM embeddings WHERE chunk_id = ?", (chunk_id,)
                    )
                except sqlite3.OperationalError:
                    pass

        # Delete chunks (FTS will be updated by trigger)
        self.conn.execute("DELETE FROM chunks WHERE post_id = ?", (post_id,))
        self.conn.commit()

    def insert_chunk(self, chunk: Chunk) -> int:
        """Insert a chunk and return its ID."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        cursor = self.conn.execute(
            "INSERT INTO chunks (post_id, chunk_index, content) VALUES (?, ?, ?)",
            (chunk.post_id, chunk.chunk_index, chunk.content),
        )
        self.conn.commit()
        return cursor.lastrowid

    def store_embedding(self, chunk_id: int, embedding: list[float]) -> None:
        """Store an embedding for a chunk."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        if not self._vec_enabled:
            return

        # Convert to bytes for sqlite-vec
        embedding_array = np.array(embedding, dtype=np.float32)

        self.conn.execute(
            "INSERT OR REPLACE INTO embeddings (chunk_id, embedding) VALUES (?, ?)",
            (chunk_id, embedding_array.tobytes()),
        )
        self.conn.commit()

    def fts_search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Search using FTS5 BM25 ranking."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        rows = self.conn.execute(
            """
            SELECT c.id, c.post_id, c.content, bm25(chunks_fts) as score,
                   p.title, p.category
            FROM chunks_fts
            JOIN chunks c ON chunks_fts.rowid = c.id
            JOIN posts p ON c.post_id = p.id
            WHERE chunks_fts MATCH ?
            ORDER BY score
            LIMIT ?
            """,
            (query, limit),
        ).fetchall()

        return [
            SearchResult(
                chunk_id=row["id"],
                post_id=row["post_id"],
                content=row["content"],
                score=-row["score"],  # BM25 returns negative scores
                bm25_score=-row["score"],
                title=row["title"],
                category=row["category"],
            )
            for row in rows
        ]

    def vector_search(
        self, query_embedding: list[float], limit: int = 10
    ) -> list[SearchResult]:
        """Search using vector similarity."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        if not self._vec_enabled:
            return []

        query_array = np.array(query_embedding, dtype=np.float32)

        rows = self.conn.execute(
            """
            SELECT e.chunk_id, e.distance, c.post_id, c.content,
                   p.title, p.category
            FROM embeddings e
            JOIN chunks c ON e.chunk_id = c.id
            JOIN posts p ON c.post_id = p.id
            WHERE embedding MATCH ? AND k = ?
            ORDER BY distance
            """,
            (query_array.tobytes(), limit),
        ).fetchall()

        return [
            SearchResult(
                chunk_id=row["chunk_id"],
                post_id=row["post_id"],
                content=row["content"],
                score=1.0 - row["distance"],  # Convert distance to similarity
                semantic_score=1.0 - row["distance"],
                title=row["title"],
                category=row["category"],
            )
            for row in rows
        ]

    def is_posted(self, post_id: str) -> bool:
        """Check if a post has been posted to Mastodon."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        row = self.conn.execute(
            "SELECT status FROM posts WHERE id = ?", (post_id,)
        ).fetchone()

        return row is not None and row["status"] == "posted"

    def mark_as_posted(
        self, post_id: str, mastodon_url: str, posted_at: Optional[datetime] = None
    ) -> None:
        """Mark a post as posted to Mastodon."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        if posted_at is None:
            posted_at = datetime.utcnow()

        self.conn.execute(
            """
            UPDATE posts
            SET status = 'posted', mastodon_url = ?, posted_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (mastodon_url, posted_at.isoformat(), datetime.utcnow().isoformat(), post_id),
        )
        self.conn.commit()

    def get_all_posts(self) -> list[Post]:
        """Get all posts."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        rows = self.conn.execute("SELECT * FROM posts ORDER BY created_at DESC").fetchall()
        return [self._row_to_post(row) for row in rows]

    @property
    def vec_enabled(self) -> bool:
        """Check if vector search is enabled."""
        return self._vec_enabled
