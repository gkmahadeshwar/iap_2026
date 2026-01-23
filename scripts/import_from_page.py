#!/usr/bin/env python3
"""Import posts from a Notion page into a new database."""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

def main():
    client = Client(auth=os.getenv('NOTION_API_KEY'))
    page_id = os.getenv('NOTION_DATABASE_ID')

    # Read all posts from the page
    print('Reading posts from page...')
    blocks = client.blocks.children.list(block_id=page_id)

    posts = []
    current_category = None
    current_post = None

    for block in blocks.get('results', []):
        block_type = block.get('type')

        if block_type == 'heading_1':
            text = block.get('heading_1', {}).get('rich_text', [])
            current_category = ''.join(t.get('plain_text', '') for t in text)

        elif block_type == 'heading_2':
            if current_post and current_post.get('content'):
                posts.append(current_post)

            text = block.get('heading_2', {}).get('rich_text', [])
            title = ''.join(t.get('plain_text', '') for t in text)
            # Clean up title (remove "Post X: " prefix)
            if title.startswith('Post ') and ':' in title:
                title = title.split(':', 1)[1].strip()
            current_post = {
                'title': title,
                'category': current_category,
                'content': []
            }

        elif block_type == 'paragraph' and current_post:
            text = block.get('paragraph', {}).get('rich_text', [])
            para = ''.join(t.get('plain_text', '') for t in text)
            if para.strip():
                current_post['content'].append(para)

    if current_post and current_post.get('content'):
        posts.append(current_post)

    print(f'Found {len(posts)} posts')

    # Create database as a child of the same page
    print('\nCreating database...')

    # Get unique categories for select options
    categories = list(set(
        p['category'] for p in posts
        if p['category'] and 'Tips' not in p['category'] and 'Suggestion' not in p['category']
    ))

    db = client.databases.create(
        parent={"type": "page_id", "page_id": page_id},
        title=[{"type": "text", "text": {"content": "Social Media Posts"}}],
        properties={
            "Name": {"title": {}},
            "Content": {"rich_text": {}},
            "Status": {
                "status": {
                    "options": [
                        {"name": "Draft", "color": "gray"},
                        {"name": "Ready", "color": "yellow"},
                        {"name": "Posted", "color": "green"}
                    ]
                }
            },
            "Category": {
                "select": {
                    "options": [{"name": cat, "color": "blue"} for cat in categories]
                }
            },
            "Hashtags": {"multi_select": {}},
            "Mastodon URL": {"url": {}}
        }
    )

    db_id = db['id']
    print(f'Created database: {db_id}')

    # Add posts to database
    print('\nAdding posts...')
    added = 0
    for post in posts:
        if 'Tips' in (post['category'] or '') or 'Suggestion' in (post['category'] or ''):
            continue

        content = '\n\n'.join(post['content'])

        # Extract hashtags from content
        hashtags = re.findall(r'#(\w+)', content)

        properties = {
            "Name": {"title": [{"text": {"content": post['title']}}]},
            "Content": {"rich_text": [{"text": {"content": content[:2000]}}]},
            "Status": {"status": {"name": "Draft"}},
        }

        if post['category']:
            properties["Category"] = {"select": {"name": post['category']}}

        if hashtags:
            properties["Hashtags"] = {"multi_select": [{"name": tag} for tag in hashtags[:10]]}

        client.pages.create(parent={"database_id": db_id}, properties=properties)
        print(f'  Added: {post["title"]}')
        added += 1

    print(f'\n✓ Database created with {added} posts!')
    print(f'\nDatabase ID: {db_id}')

    # Format for .env
    clean_id = db_id.replace("-", "")
    print(f'\nUpdate your .env with:')
    print(f'NOTION_DATABASE_ID={clean_id}')

    return clean_id

if __name__ == "__main__":
    main()
