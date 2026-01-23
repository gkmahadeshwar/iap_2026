#!/usr/bin/env python3
"""Run the Notion watcher for auto-posting to Mastodon."""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from notion_rag.config import Config
from notion_rag.database import VectorDatabase
from notion_rag.notion_client import NotionClient
from notion_rag.poster import MastodonPoster
from notion_rag.watcher import NotionWatcher


def main():
    """Run the watcher."""
    parser = argparse.ArgumentParser(
        description="Watch Notion for posts with status='Ready' and auto-post to Mastodon"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single poll cycle and exit",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Poll interval in seconds (default: from config or 60)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress progress output",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be posted without actually posting",
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
        print("  MASTODON_ACCESS_TOKEN=your_token")
        sys.exit(1)

    verbose = not args.quiet

    if verbose:
        print("Notion Watcher")
        print("=" * 40)

    # Initialize components
    if verbose:
        print("\nInitializing...")

    notion = NotionClient(config.notion_api_key, config.notion_database_id)

    db = VectorDatabase(config.database_path)
    db.connect()
    db.initialize_schema()

    poster = MastodonPoster(config.mastodon_instance_url, config.mastodon_access_token)

    # Verify Mastodon credentials
    if verbose:
        print("Verifying Mastodon credentials...")

    if not poster.verify_credentials():
        print("Error: Invalid Mastodon credentials")
        print("Please check your MASTODON_ACCESS_TOKEN")
        sys.exit(1)

    if verbose:
        print("  Credentials verified!")

    # Handle dry run
    if args.dry_run:
        if verbose:
            print("\n[DRY RUN MODE - No posts will be made]\n")

        ready_posts = notion.fetch_posts_by_status("Ready")
        print(f"Found {len(ready_posts)} posts with status 'Ready':\n")

        for post in ready_posts:
            is_posted = db.is_posted(post.id)
            status = "SKIP (already posted)" if is_posted else "WOULD POST"
            print(f"  [{status}] {post.title}")
            if not is_posted:
                # Show content preview
                preview = post.content[:100] + "..." if len(post.content) > 100 else post.content
                print(f"    Preview: {preview}")
            print()

        db.close()
        return

    # Set poll interval
    poll_interval = args.interval or config.poll_interval

    # Create watcher
    watcher = NotionWatcher(
        notion=notion,
        db=db,
        poster=poster,
        poll_interval=poll_interval,
    )

    try:
        if args.once:
            if verbose:
                print("\nRunning single poll cycle...\n")
            watcher.poll_once(verbose=verbose)
        else:
            if verbose:
                print()
            watcher.run(verbose=verbose)

    finally:
        db.close()


if __name__ == "__main__":
    main()
