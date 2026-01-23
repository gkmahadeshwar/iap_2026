"""Configuration management for the Notion RAG pipeline."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Config:
    """Configuration for the Notion RAG pipeline."""

    # Notion settings
    notion_api_key: str
    notion_database_id: str

    # Mastodon settings
    mastodon_instance_url: str
    mastodon_access_token: str

    # Database settings
    database_path: Path

    # Embedding settings
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimensions: int = 384

    # Search settings
    hybrid_alpha: float = 0.5  # 0=BM25 only, 1=semantic only

    # Watcher settings
    poll_interval: int = 60  # seconds

    @classmethod
    def from_env(cls, env_path: str | None = None) -> "Config":
        """Load configuration from environment variables."""
        if env_path:
            load_dotenv(env_path)
        else:
            load_dotenv()

        # Determine project root and data directory
        project_root = Path(__file__).parent.parent
        data_dir = project_root / "data"
        data_dir.mkdir(exist_ok=True)

        return cls(
            notion_api_key=os.getenv("NOTION_API_KEY", ""),
            notion_database_id=os.getenv("NOTION_DATABASE_ID", ""),
            mastodon_instance_url=os.getenv(
                "MASTODON_INSTANCE_URL", "https://mastodon.social"
            ),
            mastodon_access_token=os.getenv("MASTODON_ACCESS_TOKEN", ""),
            database_path=Path(os.getenv("DATABASE_PATH", str(data_dir / "posts.db"))),
            embedding_model=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            embedding_dimensions=int(os.getenv("EMBEDDING_DIMENSIONS", "384")),
            hybrid_alpha=float(os.getenv("HYBRID_ALPHA", "0.5")),
            poll_interval=int(os.getenv("POLL_INTERVAL", "60")),
        )

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []

        if not self.notion_api_key:
            errors.append("NOTION_API_KEY is required")
        if not self.notion_database_id:
            errors.append("NOTION_DATABASE_ID is required")
        if not self.mastodon_access_token:
            errors.append("MASTODON_ACCESS_TOKEN is required for posting")

        return errors
