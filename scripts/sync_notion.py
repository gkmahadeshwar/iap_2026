#!/usr/bin/env python3
"""Sync posts from Notion to SQLite database."""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from notion_rag.chunker import SemanticChunker
from notion_rag.config import Config
from notion_rag.database import VectorDatabase
from notion_rag.embeddings import EmbeddingService
from notion_rag.notion_client import NotionClient
from notion_rag.sync import NotionSync


def main():
    """Run the sync process."""
    parser = argparse.ArgumentParser(
        description="Sync posts from Notion to SQLite database"
    )
    parser.add_argument(
        "--status",
        type=str,
        help="Only sync posts with this status (e.g., 'Ready', 'Draft')",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress progress output",
    )
    args = parser.parse_args()

    # Load configuration
    config = Config.from_env()

    # Validate configuration
    errors = config.validate()
    if errors:
        for error in errors:
            print(f"Error: {error}")
        print("\nPlease set the required environment variables in your .env file:")
        print("  NOTION_API_KEY=secret_xxx")
        print("  NOTION_DATABASE_ID=your_database_id")
        sys.exit(1)

    verbose = not args.quiet

    if verbose:
        print("Notion to SQLite Sync")
        print("=" * 40)

    # Initialize components
    if verbose:
        print("\nInitializing...")

    notion = NotionClient(config.notion_api_key, config.notion_database_id)

    db = VectorDatabase(config.database_path)
    db.connect()
    db.initialize_schema()

    embedder = EmbeddingService(config.embedding_model)
    chunker = SemanticChunker()

    sync = NotionSync(notion, db, embedder, chunker)

    # Run sync
    if verbose:
        print()

    try:
        if args.status:
            stats = sync.sync_by_status(args.status, verbose=verbose)
        else:
            stats = sync.sync_all(verbose=verbose)

        if not verbose:
            print(
                f"Synced {stats['synced']}/{stats['total']} posts, "
                f"{stats['chunks_created']} chunks, "
                f"{stats['embeddings_created']} embeddings"
            )

    finally:
        db.close()


if __name__ == "__main__":
    main()
