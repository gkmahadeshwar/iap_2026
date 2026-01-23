"""Mastodon posting functionality."""

from typing import Optional

import requests

from notion_rag.models import Post, PostingResult


class MastodonPoster:
    """Post content to Mastodon."""

    def __init__(self, instance_url: str, access_token: str):
        """Initialize the Mastodon poster.

        Args:
            instance_url: Mastodon instance URL (e.g., https://mastodon.social).
            access_token: Mastodon API access token.
        """
        self.instance_url = instance_url.rstrip("/")
        self.access_token = access_token

    def post(
        self,
        content: str,
        visibility: str = "public",
        in_reply_to_id: Optional[str] = None,
    ) -> PostingResult:
        """Post a status to Mastodon.

        Args:
            content: Status text content.
            visibility: Post visibility (public, unlisted, private, direct).
            in_reply_to_id: Optional ID of post to reply to.

        Returns:
            PostingResult with success status and details.
        """
        url = f"{self.instance_url}/api/v1/statuses"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        data = {"status": content, "visibility": visibility}

        if in_reply_to_id:
            data["in_reply_to_id"] = in_reply_to_id

        try:
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()

            result = response.json()
            return PostingResult(
                success=True,
                mastodon_id=result.get("id"),
                mastodon_url=result.get("url"),
            )

        except requests.exceptions.HTTPError as e:
            return PostingResult(
                success=False,
                error=f"HTTP error: {e.response.status_code} - {e.response.text}",
            )
        except requests.exceptions.RequestException as e:
            return PostingResult(
                success=False,
                error=f"Request error: {str(e)}",
            )

    def post_from_notion(self, post: Post, visibility: str = "public") -> PostingResult:
        """Post a Notion post to Mastodon.

        Formats the post content with hashtags if present.

        Args:
            post: Post object from Notion.
            visibility: Post visibility.

        Returns:
            PostingResult with success status and details.
        """
        # Build the content with hashtags
        content = post.content

        # Add hashtags if they exist and aren't already in the content
        if post.hashtags:
            existing_hashtags = set()
            # Find hashtags already in content
            import re

            for match in re.finditer(r"#(\w+)", content):
                existing_hashtags.add(match.group(1).lower())

            # Add missing hashtags
            new_hashtags = [
                f"#{tag}" for tag in post.hashtags
                if tag.lower() not in existing_hashtags
            ]

            if new_hashtags:
                if not content.endswith("\n"):
                    content += "\n\n"
                elif not content.endswith("\n\n"):
                    content += "\n"
                content += " ".join(new_hashtags)

        return self.post(content, visibility=visibility)

    def verify_credentials(self) -> bool:
        """Verify that the access token is valid.

        Returns:
            True if credentials are valid, False otherwise.
        """
        url = f"{self.instance_url}/api/v1/accounts/verify_credentials"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException:
            return False
