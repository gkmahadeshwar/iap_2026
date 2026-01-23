"""Notion API client for fetching social media posts."""

from datetime import datetime
from typing import Any, Optional

from notion_rag.models import Post


class NotionClient:
    """Client for fetching posts from a Notion database."""

    def __init__(self, api_key: str, database_id: str):
        """Initialize the Notion client.

        Args:
            api_key: Notion integration API key.
            database_id: ID of the Notion database containing posts.
        """
        self.api_key = api_key
        self.database_id = database_id
        self._client: Optional["Client"] = None
        self._data_source_id: Optional[str] = None

    def _get_client(self) -> "Client":
        """Lazy load the Notion client."""
        if self._client is None:
            try:
                from notion_client import Client

                self._client = Client(auth=self.api_key)
            except ImportError:
                raise ImportError(
                    "notion-client is required. Install with: pip install notion-client"
                )
        return self._client

    def _get_data_source_id(self) -> str:
        """Find the data source ID for this database."""
        if self._data_source_id:
            return self._data_source_id

        client = self._get_client()
        # Search for data sources and find one linked to our database
        search = client.search(filter={"property": "object", "value": "data_source"})

        clean_db_id = self.database_id.replace("-", "")
        for item in search.get("results", []):
            parent = item.get("parent", {})
            parent_db_id = parent.get("database_id", "").replace("-", "")
            if parent_db_id == clean_db_id:
                self._data_source_id = item["id"]
                return self._data_source_id

        raise RuntimeError(f"No data source found for database {self.database_id}")

    def fetch_all_posts(self) -> list[Post]:
        """Fetch all posts from the Notion database.

        Returns:
            List of Post objects.
        """
        client = self._get_client()
        data_source_id = self._get_data_source_id()
        posts = []
        start_cursor = None

        while True:
            kwargs: dict[str, Any] = {"data_source_id": data_source_id}
            if start_cursor:
                kwargs["start_cursor"] = start_cursor

            response = client.data_sources.query(**kwargs)

            for page in response.get("results", []):
                post = self._page_to_post(page)
                if post:
                    posts.append(post)

            if not response.get("has_more"):
                break

            start_cursor = response.get("next_cursor")

        return posts

    def fetch_posts_by_status(self, status: str) -> list[Post]:
        """Fetch posts with a specific status.

        Args:
            status: Status to filter by (e.g., "Ready", "Draft", "Posted").

        Returns:
            List of Post objects matching the status.
        """
        client = self._get_client()
        data_source_id = self._get_data_source_id()
        posts = []
        start_cursor = None

        while True:
            kwargs: dict[str, Any] = {
                "data_source_id": data_source_id,
                "filter": {
                    "property": "Status",
                    "select": {"equals": status},
                },
            }
            if start_cursor:
                kwargs["start_cursor"] = start_cursor

            response = client.data_sources.query(**kwargs)

            for page in response.get("results", []):
                post = self._page_to_post(page)
                if post:
                    posts.append(post)

            if not response.get("has_more"):
                break

            start_cursor = response.get("next_cursor")

        return posts

    def update_status(
        self, page_id: str, status: str, mastodon_url: Optional[str] = None
    ) -> None:
        """Update the status of a Notion page.

        Args:
            page_id: Notion page ID to update.
            status: New status value.
            mastodon_url: Optional Mastodon URL to store.
        """
        client = self._get_client()

        properties: dict[str, Any] = {
            "Status": {"status": {"name": status}},
        }

        if mastodon_url:
            properties["Mastodon URL"] = {"url": mastodon_url}

        client.pages.update(page_id=page_id, properties=properties)

    def _page_to_post(self, page: dict[str, Any]) -> Optional[Post]:
        """Convert a Notion page to a Post object.

        Args:
            page: Notion page data from API response.

        Returns:
            Post object or None if conversion fails.
        """
        try:
            page_id = page["id"]
            properties = page.get("properties", {})

            # Extract title
            title = self._get_title(properties)
            if not title:
                return None

            # Extract content
            content = self._get_rich_text(properties, "Content")
            if not content:
                # Try to get content from page blocks if not in properties
                content = self._get_page_content(page_id)

            if not content:
                return None

            # Extract other properties
            category = self._get_select(properties, "Category")
            hashtags = self._get_multi_select(properties, "Hashtags")
            # Status can be either 'status' type or 'select' type
            status = self._get_status(properties, "Status")
            if not status:
                status = self._get_select(properties, "Status")
            status = status or "draft"
            mastodon_url = self._get_url(properties, "Mastodon URL")

            # Parse dates
            created_at = datetime.fromisoformat(
                page["created_time"].replace("Z", "+00:00")
            )
            updated_at = datetime.fromisoformat(
                page["last_edited_time"].replace("Z", "+00:00")
            )

            return Post(
                id=page_id,
                notion_url=page.get("url"),
                title=title,
                content=content,
                category=category,
                hashtags=hashtags,
                status=status.lower(),
                mastodon_url=mastodon_url,
                created_at=created_at,
                updated_at=updated_at,
            )

        except Exception as e:
            print(f"Error converting page to post: {e}")
            return None

    def _get_title(self, properties: dict[str, Any]) -> Optional[str]:
        """Extract title from properties."""
        # Try common title property names
        for prop_name in ["Name", "Title", "Post"]:
            if prop_name in properties:
                prop = properties[prop_name]
                if prop.get("type") == "title":
                    title_parts = prop.get("title", [])
                    return "".join(t.get("plain_text", "") for t in title_parts)
        return None

    def _get_rich_text(
        self, properties: dict[str, Any], prop_name: str
    ) -> Optional[str]:
        """Extract rich text from a property."""
        if prop_name not in properties:
            return None

        prop = properties[prop_name]
        if prop.get("type") != "rich_text":
            return None

        text_parts = prop.get("rich_text", [])
        return "".join(t.get("plain_text", "") for t in text_parts)

    def _get_select(
        self, properties: dict[str, Any], prop_name: str
    ) -> Optional[str]:
        """Extract select value from a property."""
        if prop_name not in properties:
            return None

        prop = properties[prop_name]
        if prop.get("type") != "select":
            return None

        select_val = prop.get("select")
        return select_val.get("name") if select_val else None

    def _get_multi_select(
        self, properties: dict[str, Any], prop_name: str
    ) -> list[str]:
        """Extract multi-select values from a property."""
        if prop_name not in properties:
            return []

        prop = properties[prop_name]
        if prop.get("type") != "multi_select":
            return []

        return [item.get("name", "") for item in prop.get("multi_select", [])]

    def _get_status(
        self, properties: dict[str, Any], prop_name: str
    ) -> Optional[str]:
        """Extract status value from a property."""
        if prop_name not in properties:
            return None

        prop = properties[prop_name]
        if prop.get("type") != "status":
            return None

        status_val = prop.get("status")
        return status_val.get("name") if status_val else None

    def _get_url(
        self, properties: dict[str, Any], prop_name: str
    ) -> Optional[str]:
        """Extract URL from a property."""
        if prop_name not in properties:
            return None

        prop = properties[prop_name]
        if prop.get("type") != "url":
            return None

        return prop.get("url")

    def _get_page_content(self, page_id: str) -> Optional[str]:
        """Fetch content from page blocks (for pages with content in blocks)."""
        try:
            client = self._get_client()
            blocks = client.blocks.children.list(block_id=page_id)

            content_parts = []
            for block in blocks.get("results", []):
                block_type = block.get("type")

                if block_type == "paragraph":
                    text = self._extract_block_text(block.get("paragraph", {}))
                    if text:
                        content_parts.append(text)

                elif block_type == "bulleted_list_item":
                    text = self._extract_block_text(
                        block.get("bulleted_list_item", {})
                    )
                    if text:
                        content_parts.append(f"- {text}")

                elif block_type == "numbered_list_item":
                    text = self._extract_block_text(
                        block.get("numbered_list_item", {})
                    )
                    if text:
                        content_parts.append(text)

            return "\n\n".join(content_parts) if content_parts else None

        except Exception:
            return None

    def _extract_block_text(self, block_content: dict[str, Any]) -> Optional[str]:
        """Extract text from a block's rich_text content."""
        rich_text = block_content.get("rich_text", [])
        if not rich_text:
            return None
        return "".join(t.get("plain_text", "") for t in rich_text)
