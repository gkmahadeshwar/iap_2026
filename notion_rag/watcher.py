"""Polling watcher for auto-posting to Mastodon."""

import time
from datetime import datetime
from typing import Callable, Optional

from notion_rag.database import VectorDatabase
from notion_rag.models import Post
from notion_rag.notion_client import NotionClient
from notion_rag.poster import MastodonPoster


class NotionWatcher:
    """Watch Notion for posts with status='Ready' and auto-post to Mastodon."""

    def __init__(
        self,
        notion: NotionClient,
        db: VectorDatabase,
        poster: MastodonPoster,
        poll_interval: int = 60,
        on_post: Optional[Callable[[Post, str], None]] = None,
        on_error: Optional[Callable[[Post, str], None]] = None,
    ):
        """Initialize the watcher.

        Args:
            notion: Notion API client.
            db: Vector database for tracking posted status.
            poster: Mastodon poster.
            poll_interval: Seconds between polls.
            on_post: Optional callback when a post is successfully posted.
            on_error: Optional callback when posting fails.
        """
        self.notion = notion
        self.db = db
        self.poster = poster
        self.poll_interval = poll_interval
        self.on_post = on_post
        self.on_error = on_error
        self._running = False

    def poll_once(self, verbose: bool = True) -> dict:
        """Perform a single poll cycle.

        Args:
            verbose: Print progress messages.

        Returns:
            Dictionary with poll statistics.
        """
        stats = {
            "checked": 0,
            "posted": 0,
            "skipped": 0,
            "errors": 0,
        }

        if verbose:
            print(f"[{datetime.now().isoformat()}] Polling Notion for ready posts...")

        try:
            ready_posts = self.notion.fetch_posts_by_status("Ready")
            stats["checked"] = len(ready_posts)

            if verbose:
                print(f"  Found {len(ready_posts)} posts with status 'Ready'")

            for post in ready_posts:
                # Check if already posted locally
                if self.db.is_posted(post.id):
                    if verbose:
                        print(f"  Skipping (already posted): {post.title[:40]}...")
                    stats["skipped"] += 1
                    continue

                if verbose:
                    print(f"  Posting: {post.title[:40]}...")

                # Post to Mastodon
                result = self.poster.post_from_notion(post)

                if result.success:
                    # Update local database
                    self.db.mark_as_posted(post.id, result.mastodon_url or "")

                    # Update Notion status
                    try:
                        self.notion.update_status(
                            post.id, "Posted", result.mastodon_url
                        )
                    except Exception as e:
                        if verbose:
                            print(f"    Warning: Failed to update Notion status: {e}")

                    if verbose:
                        print(f"    Posted: {result.mastodon_url}")

                    stats["posted"] += 1

                    if self.on_post:
                        self.on_post(post, result.mastodon_url or "")
                else:
                    if verbose:
                        print(f"    Error: {result.error}")
                    stats["errors"] += 1

                    if self.on_error:
                        self.on_error(post, result.error or "Unknown error")

        except Exception as e:
            if verbose:
                print(f"  Error during poll: {e}")
            stats["errors"] += 1

        if verbose:
            print(
                f"  Poll complete: {stats['posted']} posted, "
                f"{stats['skipped']} skipped, {stats['errors']} errors"
            )

        return stats

    def run(self, verbose: bool = True) -> None:
        """Run the watcher in a continuous loop.

        Args:
            verbose: Print progress messages.
        """
        self._running = True

        if verbose:
            print(f"Starting Notion watcher (polling every {self.poll_interval}s)")
            print("Press Ctrl+C to stop\n")

        try:
            while self._running:
                self.poll_once(verbose=verbose)

                if self._running:
                    if verbose:
                        print(f"  Next poll in {self.poll_interval} seconds...\n")
                    time.sleep(self.poll_interval)

        except KeyboardInterrupt:
            if verbose:
                print("\nWatcher stopped by user")
            self._running = False

    def stop(self) -> None:
        """Stop the watcher loop."""
        self._running = False
