"""Pydantic models for the Notion RAG pipeline."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Post(BaseModel):
    """A social media post from Notion."""

    id: str = Field(description="Notion page ID")
    notion_url: Optional[str] = None
    title: str
    content: str
    category: Optional[str] = None
    hashtags: list[str] = Field(default_factory=list)
    status: str = "draft"  # draft, ready, posted
    posted_at: Optional[datetime] = None
    mastodon_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Chunk(BaseModel):
    """A text chunk from a post."""

    id: Optional[int] = None
    post_id: str
    chunk_index: int
    content: str
    embedding: Optional[list[float]] = None


class SearchResult(BaseModel):
    """A search result from hybrid search."""

    chunk_id: int
    post_id: str
    content: str
    score: float
    bm25_score: Optional[float] = None
    semantic_score: Optional[float] = None
    title: Optional[str] = None
    category: Optional[str] = None


class PostingResult(BaseModel):
    """Result of posting to Mastodon."""

    success: bool
    mastodon_id: Optional[str] = None
    mastodon_url: Optional[str] = None
    error: Optional[str] = None
