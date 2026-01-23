#!/usr/bin/env python3
"""Initialize the SQLite database with FTS5 and vector tables."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from notion_rag.config import Config
from notion_rag.database import VectorDatabase


def main():
    """Initialize the database."""
    print("Initializing database...")

    # Load configuration
    config = Config.from_env()

    print(f"Database path: {config.database_path}")

    # Ensure data directory exists
    config.database_path.parent.mkdir(parents=True, exist_ok=True)

    # Connect and initialize
    db = VectorDatabase(config.database_path)
    db.connect()

    print("Creating schema...")
    db.initialize_schema()

    # Report status
    print("\nDatabase initialized successfully!")
    print(f"  - FTS5 enabled: Yes")
    print(f"  - Vector search enabled: {db.vec_enabled}")

    if not db.vec_enabled:
        print("\n  Note: Install sqlite-vec for vector search:")
        print("    pip install sqlite-vec")

    db.close()


if __name__ == "__main__":
    main()
