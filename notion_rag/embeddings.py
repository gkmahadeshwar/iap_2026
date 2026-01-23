"""Embedding service using sentence-transformers."""

from typing import Optional


class EmbeddingService:
    """Generate embeddings using MiniLM-L6-v2 from HuggingFace."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize the embedding service.

        Args:
            model_name: Name of the sentence-transformer model to use.
                       Default is all-MiniLM-L6-v2 (384 dimensions).
        """
        self.model_name = model_name
        self._model: Optional["SentenceTransformer"] = None

    def _load_model(self) -> None:
        """Lazy load the model on first use."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                print(f"Loading embedding model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name)
                print(f"Model loaded successfully. Embedding dimension: {self.dimensions}")
            except ImportError:
                raise ImportError(
                    "sentence-transformers is required for embeddings. "
                    "Install with: pip install sentence-transformers"
                )

    @property
    def dimensions(self) -> int:
        """Return the embedding dimensions."""
        self._load_model()
        return self._model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors (each is a list of floats).
        """
        self._load_model()

        if not texts:
            return []

        # Encode all texts in a batch for efficiency
        embeddings = self._model.encode(
            texts,
            show_progress_bar=len(texts) > 10,
            convert_to_numpy=True,
        )

        return embeddings.tolist()

    def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text string to embed.

        Returns:
            Embedding vector as a list of floats.
        """
        return self.embed([text])[0]
