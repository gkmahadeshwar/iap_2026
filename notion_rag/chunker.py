"""Semantic text chunking for social media posts."""

import re
from dataclasses import dataclass


@dataclass
class ChunkConfig:
    """Configuration for text chunking."""

    max_chunk_size: int = 500  # Max characters per chunk
    min_chunk_size: int = 50  # Minimum characters for a chunk
    overlap: int = 50  # Character overlap between chunks
    short_content_threshold: int = 500  # Don't chunk content shorter than this


class SemanticChunker:
    """Chunk text semantically by paragraphs.

    For social media posts (typically short), most content will be
    a single chunk. Longer content is split by paragraphs with overlap.
    """

    def __init__(self, config: ChunkConfig | None = None):
        """Initialize the chunker.

        Args:
            config: Chunking configuration. Uses defaults if not provided.
        """
        self.config = config or ChunkConfig()

    def chunk(self, text: str) -> list[str]:
        """Split text into semantic chunks.

        Args:
            text: Text to chunk.

        Returns:
            List of text chunks.
        """
        if not text or not text.strip():
            return []

        text = text.strip()

        # Short content: return as single chunk
        if len(text) <= self.config.short_content_threshold:
            return [text]

        # Split into paragraphs
        paragraphs = self._split_paragraphs(text)

        # Merge small paragraphs and split large ones
        chunks = self._merge_and_split(paragraphs)

        return chunks

    def _split_paragraphs(self, text: str) -> list[str]:
        """Split text into paragraphs."""
        # Split on double newlines or multiple newlines
        paragraphs = re.split(r"\n\s*\n+", text)

        # Clean up each paragraph
        return [p.strip() for p in paragraphs if p.strip()]

    def _merge_and_split(self, paragraphs: list[str]) -> list[str]:
        """Merge small paragraphs and split large ones."""
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            # If paragraph itself is too large, split it
            if len(para) > self.config.max_chunk_size:
                # Save current chunk first
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""

                # Split large paragraph by sentences
                sentences = self._split_sentences(para)
                sentence_chunk = ""

                for sentence in sentences:
                    if len(sentence_chunk) + len(sentence) <= self.config.max_chunk_size:
                        sentence_chunk += (" " if sentence_chunk else "") + sentence
                    else:
                        if sentence_chunk:
                            chunks.append(sentence_chunk.strip())
                        sentence_chunk = sentence

                if sentence_chunk:
                    current_chunk = sentence_chunk

            # Check if adding this paragraph exceeds max size
            elif len(current_chunk) + len(para) + 2 > self.config.max_chunk_size:
                # Save current chunk with overlap
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    # Add overlap from end of current chunk
                    overlap_text = self._get_overlap(current_chunk)
                    current_chunk = overlap_text + " " + para if overlap_text else para
                else:
                    current_chunk = para
            else:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para

        # Don't forget the last chunk
        if current_chunk and len(current_chunk.strip()) >= self.config.min_chunk_size:
            chunks.append(current_chunk.strip())

        return chunks

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Simple sentence splitting on common end punctuation
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    def _get_overlap(self, text: str) -> str:
        """Get overlap text from the end of a chunk."""
        if len(text) <= self.config.overlap:
            return text

        # Try to break at a word boundary
        overlap_start = len(text) - self.config.overlap
        space_idx = text.find(" ", overlap_start)

        if space_idx != -1:
            return text[space_idx + 1 :]
        return text[-self.config.overlap :]
