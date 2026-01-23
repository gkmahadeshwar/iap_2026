"""Notion to SQLite RAG Pipeline.

Fetch social media posts from Notion, chunk, embed with MiniLM-L6-v2,
and store in SQLite for hybrid RAG search (BM25 + vector).
"""

from notion_rag.config import Config
from notion_rag.models import Post, Chunk, SearchResult
from notion_rag.database import VectorDatabase
from notion_rag.embeddings import EmbeddingService
from notion_rag.hybrid_search import HybridSearch
from notion_rag.notion_client import NotionClient
from notion_rag.chunker import SemanticChunker
from notion_rag.sync import NotionSync
from notion_rag.rag import RAG
from notion_rag.watcher import NotionWatcher
from notion_rag.poster import MastodonPoster

__all__ = [
    "Config",
    "Post",
    "Chunk",
    "SearchResult",
    "VectorDatabase",
    "EmbeddingService",
    "HybridSearch",
    "NotionClient",
    "SemanticChunker",
    "NotionSync",
    "RAG",
    "NotionWatcher",
    "MastodonPoster",
]
