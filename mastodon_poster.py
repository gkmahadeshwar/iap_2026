#!/usr/bin/env python3
"""
Mastodon poster with search & reply capabilities.
Supports posting pre-written content and AI-generated replies.

Run: python mastodon_poster.py
"""

import os
import re
import time
from typing import List, Optional

import requests
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field


# Load environment variables
load_dotenv()

# Configuration from environment
INSTANCE_URL = os.getenv("MASTODON_INSTANCE_URL", "https://mastodon.social")
ACCESS_TOKEN = os.getenv("MASTODON_ACCESS_TOKEN", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")


# Pydantic Models for structured outputs
class MastodonPost(BaseModel):
    """Represents a Mastodon post retrieved from search."""
    id: str
    account_username: str
    content: str
    url: str


class GeneratedReply(BaseModel):
    """A single generated reply to a Mastodon post."""
    original_post_id: str = Field(description="ID of the post being replied to")
    original_author: str = Field(description="Username of the original post author")
    reply_text: str = Field(description="The reply text, max 500 characters", max_length=500)
    tone: str = Field(description="Tone of the reply (e.g., friendly, informative, curious)")
    key_topic: str = Field(description="Main topic addressed in the reply")


class BatchReplies(BaseModel):
    """Batch of generated replies with summary."""
    replies: List[GeneratedReply]
    summary: str = Field(description="Brief summary of all generated replies")


# Pre-written posts for mode 1
POSTS = [
    {
        "title": "Turing Patterns",
        "content": """In 1952, Alan Turing proposed that simple chemical reactions + diffusion could create spots, stripes, and spirals in nature. 70 years later, we're still finding his equations everywhere—from zebrafish stripes to cardiac arrhythmias. Math predicting biology at its finest.

#CompBio #MathBiology #Biophysics"""
    },
    {
        "title": "Kleiber's Law",
        "content": """Why does metabolic rate scale with body mass^0.75 across 20+ orders of magnitude—from bacteria to blue whales? West, Brown & Enquist showed it emerges from fractal-like vascular networks optimized for nutrient delivery. One equation. All of life.

#CompBio #MathBiology #SystemsBiology"""
    },
    {
        "title": "Chaos in Population Dynamics",
        "content": """Robert May showed in 1976 that a simple equation for population growth (x → rx(1-x)) can produce chaos. Lesson: deterministic ≠ predictable. Ecology, epidemiology, and even cardiac dynamics all exhibit this beautiful complexity.

#CompBio #MathBiology #Complexity"""
    },
    {
        "title": "DNA as a Polymer",
        "content": """DNA isn't just a genetic code—it's a semiflexible polymer with a persistence length of ~50 nm. This means physics constrains how it bends, loops, and packs into your nucleus. Information storage meets materials science.

#Biophysics #CompBio #DNA"""
    },
    {
        "title": "Molecular Motors",
        "content": """Kinesin "walks" along microtubules taking 8 nm steps, converting ATP hydrolysis into directed motion with ~50% efficiency. For comparison, car engines are ~25% efficient. Evolution has been optimizing nanomachines for billions of years.

#Biophysics #CellBiology #Evolution"""
    },
    {
        "title": "Levinthal's Paradox",
        "content": """A 100-amino-acid protein has ~10^100 possible conformations. Sampling one per femtosecond would take longer than the age of the universe. Yet proteins fold in milliseconds. The energy landscape must be funneled, not flat. Physics > brute force.

#ProteinFolding #Biophysics #CompBio"""
    },
    {
        "title": "Enzyme Kinetics",
        "content": """The Michaelis-Menten equation (1913) is still biochemistry's workhorse. But single-molecule experiments now show individual enzymes have "memory"—their activity fluctuates over time. The average hides the individual.

#Biochemistry #SingleMolecule #CompBio"""
    },
    {
        "title": "Allosteric Regulation",
        "content": """How does hemoglobin "know" to grab O2 in lungs and release it in tissues? Cooperative binding + allosteric effects. The MWC model (1965) showed proteins are molecular switches, not just catalysts. Molecular computation before computers.

#Biochemistry #Biophysics #MolecularBiology"""
    },
    {
        "title": "The Central Dogma... Isn't",
        "content": """"DNA → RNA → Protein" was the central dogma. Then came reverse transcriptase (RNA → DNA), ribozymes (RNA = catalyst), and now we know ~80% of our genome is transcribed. Biology loves exceptions.

#MolecularBiology #Genetics #CompBio"""
    },
    {
        "title": "Network Motifs",
        "content": """Evolution repeatedly converges on the same network motifs: negative autoregulation for speed, feed-forward loops for filtering noise. Cells are running the same algorithms we'd engineer. Convergent design across 4 billion years.

#SystemsBiology #NetworkBiology #CompBio"""
    },
    {
        "title": "Robustness and Fragility",
        "content": """Bacterial chemotaxis achieves perfect adaptation—response returns to baseline regardless of signal strength. The cost? Specific protein ratios must be exact. Robust to some perturbations, fragile to others. No free lunch.

#SystemsBiology #Microbiology #CompBio"""
    },
    {
        "title": "Stochastic Gene Expression",
        "content": """Identical twins aren't truly identical. Same genome, same environment, different phenotypes. Why? Gene expression is stochastic—individual mRNA molecules matter. Noise isn't just tolerated; sometimes it's exploited.

#Genetics #SystemsBiology #CompBio"""
    },
    {
        "title": "AlphaFold",
        "content": """50 years of the protein folding problem, solved by deep learning in 2020. AlphaFold2 predicts structures with experimental accuracy. But knowing the structure doesn't tell you the function. The next 50 years: dynamics, interactions, design.

#ProteinFolding #AI #CompBio #AlphaFold"""
    },
    {
        "title": "Sequence Space",
        "content": """There are 20^100 possible 100-amino-acid proteins. That's more than atoms in the observable universe. Evolution has sampled a vanishingly small fraction. What functions remain undiscovered in sequence space?

#Evolution #ProteinEngineering #CompBio"""
    },
    {
        "title": "Fisher's Geometric Model",
        "content": """Fisher (1930) showed that beneficial mutations become rarer as organisms approach an optimum, and large mutations are almost always deleterious. Adaptation must proceed in small steps. Geometry constrains evolution.

#Evolution #MathBiology #PopulationGenetics"""
    },
    {
        "title": "Neutral Theory",
        "content": """Most molecular evolution is neutral—not adaptive. Kimura's neutral theory (1968) was controversial but explains why molecular clocks exist. Selection is strong, but drift is everywhere.

#Evolution #PopulationGenetics #MolecularEvolution"""
    },
]

# Default keywords for search
DEFAULT_KEYWORDS = [
    "computational biology",
    "bioinformatics",
    "systems biology",
    "protein folding",
    "genomics",
    "single cell",
    "AlphaFold",
    "molecular dynamics",
]


def load_config() -> bool:
    """Verify that required configuration is loaded."""
    if not ACCESS_TOKEN:
        print("Error: MASTODON_ACCESS_TOKEN not set in .env file")
        return False
    if not OPENROUTER_API_KEY:
        print("Warning: OPENROUTER_API_KEY not set - reply generation will not work")
    return True


def strip_html(text: str) -> str:
    """Remove HTML tags and decode common entities from text."""
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', text)
    # Decode common HTML entities
    clean = clean.replace('&amp;', '&')
    clean = clean.replace('&lt;', '<')
    clean = clean.replace('&gt;', '>')
    clean = clean.replace('&quot;', '"')
    clean = clean.replace('&#39;', "'")
    clean = clean.replace('&nbsp;', ' ')
    # Clean up whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def post_to_mastodon(content: str, visibility: str = "public", in_reply_to_id: Optional[str] = None) -> dict:
    """Post a status to Mastodon."""
    url = f"{INSTANCE_URL}/api/v1/statuses"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    data = {"status": content, "visibility": visibility}

    if in_reply_to_id:
        data["in_reply_to_id"] = in_reply_to_id

    response = requests.post(url, headers=headers, data=data)
    response.raise_for_status()
    return response.json()


def search_mastodon_posts(keyword: str, limit: int = 5) -> List[MastodonPost]:
    """Search Mastodon for posts containing the keyword.

    Only returns posts from mastodon.social to ensure replies are possible.
    """
    url = f"{INSTANCE_URL}/api/v2/search"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    # Request more results since we'll filter some out
    params = {
        "q": keyword,
        "type": "statuses",
        "limit": limit * 3,
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    results = response.json()
    posts = []

    for status in results.get("statuses", []):
        post_url = status.get("url", "")
        # Only include posts from mastodon.social (public instance)
        if not post_url or "mastodon.social" not in post_url:
            continue

        post = MastodonPost(
            id=status["id"],
            account_username=status["account"]["acct"],
            content=strip_html(status["content"]),
            url=post_url
        )
        posts.append(post)

        # Stop once we have enough posts
        if len(posts) >= limit:
            break

    return posts


def generate_replies_batch(posts: List[MastodonPost]) -> Optional[BatchReplies]:
    """Generate replies for a batch of posts using OpenRouter with structured output."""
    if not OPENROUTER_API_KEY:
        print("Error: OPENROUTER_API_KEY not set")
        return None

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY
    )

    # Build the prompt with all posts
    posts_text = "\n\n".join([
        f"Post {i+1}:\n"
        f"  ID: {post.id}\n"
        f"  Author: @{post.account_username}\n"
        f"  Content: {post.content}"
        for i, post in enumerate(posts)
    ])

    system_prompt = """You are a friendly computational biology enthusiast who engages thoughtfully with scientific discussions on social media.

When generating replies:
- Be genuinely engaging and add value to the conversation
- Reference specific points from the original post
- Share relevant insights or ask thoughtful questions
- Keep replies under 500 characters
- Use a natural, conversational tone
- Include relevant hashtags when appropriate
- Address the author by their username with @"""

    user_prompt = f"""Generate thoughtful replies to these Mastodon posts about science/computational biology:

{posts_text}

For each post, create a reply that:
1. Acknowledges the original content
2. Adds value (insight, question, or related information)
3. Encourages further discussion
4. Stays under 500 characters

Return ONLY a JSON object (no markdown) with this exact structure:
{{
  "replies": [
    {{
      "original_post_id": "the post ID",
      "original_author": "username without @",
      "reply_text": "your reply under 500 chars",
      "tone": "friendly/informative/curious",
      "key_topic": "main topic"
    }}
  ],
  "summary": "brief summary of all replies"
}}"""

    try:
        response = client.chat.completions.create(
            model="z-ai/glm-4.5-air:free",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        import json
        content = response.choices[0].message.content
        # Strip markdown code blocks if present
        if content.startswith("```"):
            content = content.split("\n", 1)[1]  # Remove first line
            content = content.rsplit("```", 1)[0]  # Remove closing ```
        result = json.loads(content.strip())
        return BatchReplies(**result)

    except Exception as e:
        print(f"Error generating replies: {e}")
        return None


def post_reply_to_mastodon(reply: GeneratedReply, visibility: str = "public") -> Optional[dict]:
    """Post a single reply to Mastodon."""
    try:
        result = post_to_mastodon(
            content=reply.reply_text,
            visibility=visibility,
            in_reply_to_id=reply.original_post_id
        )
        return result
    except requests.exceptions.HTTPError as e:
        print(f"Error posting reply: {e}")
        return None


def post_all_replies(replies: List[GeneratedReply], visibility: str = "public", delay: float = 2.0) -> List[dict]:
    """Post all replies with rate limiting."""
    results = []

    for i, reply in enumerate(replies):
        print(f"  Posting reply {i+1}/{len(replies)} to @{reply.original_author}...")
        result = post_reply_to_mastodon(reply, visibility)

        if result:
            results.append(result)
            print(f"    Posted: {result.get('url', 'N/A')}")
        else:
            print(f"    Failed to post reply to @{reply.original_author}")

        # Rate limiting
        if i < len(replies) - 1:
            time.sleep(delay)

    return results


def select_keyword() -> Optional[str]:
    """Interactive keyword selection."""
    print("\nSelect a search keyword:\n")
    for i, keyword in enumerate(DEFAULT_KEYWORDS, 1):
        print(f"  {i}. {keyword}")
    print(f"  {len(DEFAULT_KEYWORDS)+1}. Enter custom keyword")
    print()

    choice = input("Enter choice: ").strip()

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(DEFAULT_KEYWORDS):
            return DEFAULT_KEYWORDS[idx]
        elif idx == len(DEFAULT_KEYWORDS):
            custom = input("Enter custom keyword: ").strip()
            return custom if custom else None
    except ValueError:
        # Treat as custom keyword if not a number
        return choice if choice else None

    return None


def display_posts(posts: List[MastodonPost]):
    """Display search results."""
    print(f"\nFound {len(posts)} posts:\n")
    for i, post in enumerate(posts, 1):
        print(f"  {i}. @{post.account_username}")
        # Truncate long content for display
        content = post.content[:150] + "..." if len(post.content) > 150 else post.content
        print(f"     {content}")
        print(f"     URL: {post.url}")
        print()


def display_generated_replies(batch: BatchReplies):
    """Display generated replies for preview."""
    print("\n" + "="*50)
    print("  Generated Replies Preview")
    print("="*50)

    for i, reply in enumerate(batch.replies, 1):
        print(f"\n  Reply {i} to @{reply.original_author}")
        print(f"  Tone: {reply.tone} | Topic: {reply.key_topic}")
        print(f"  {'-'*46}")
        print(f"  {reply.reply_text}")
        print(f"  {'-'*46}")
        print(f"  Characters: {len(reply.reply_text)}/500")

    print(f"\n  Summary: {batch.summary}")
    print("="*50)


def reply_workflow():
    """Main workflow for search and reply mode."""
    print("\n" + "="*50)
    print("  Search & Reply Mode")
    print("="*50)

    # Step 1: Select keyword
    keyword = select_keyword()
    if not keyword:
        print("No keyword selected. Returning to main menu.")
        return

    print(f"\nSearching for '{keyword}'...")

    # Step 2: Search Mastodon
    try:
        posts = search_mastodon_posts(keyword, limit=5)
    except requests.exceptions.HTTPError as e:
        print(f"Search error: {e}")
        return

    if not posts:
        print("No posts found. Try a different keyword.")
        return

    display_posts(posts)

    # Step 3: Confirm to generate replies
    confirm = input("Generate AI replies for these posts? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled. Returning to main menu.")
        return

    # Step 4: Generate replies
    print("\nGenerating replies with AI...")
    batch = generate_replies_batch(posts)

    if not batch:
        print("Failed to generate replies.")
        return

    # Step 5: Preview replies
    display_generated_replies(batch)

    # Step 6: Options
    print("\nOptions:")
    print("  [a] Post all replies")
    print("  [s] Select specific replies to post")
    print("  [d] Dry run (show what would be posted)")
    print("  [c] Cancel")

    action = input("\nSelect action: ").strip().lower()

    if action == 'c':
        print("Cancelled.")
        return

    if action == 'd':
        print("\n--- DRY RUN ---")
        for i, reply in enumerate(batch.replies, 1):
            print(f"\nWould post reply {i}:")
            print(f"  To: @{reply.original_author} (post ID: {reply.original_post_id})")
            print(f"  Content: {reply.reply_text}")
        print("\n--- END DRY RUN ---")
        return

    if action == 's':
        indices = input("Enter reply numbers to post (comma-separated, e.g., 1,3,5): ").strip()
        try:
            selected_indices = [int(x.strip()) - 1 for x in indices.split(',')]
            selected_replies = [batch.replies[i] for i in selected_indices if 0 <= i < len(batch.replies)]
        except (ValueError, IndexError):
            print("Invalid selection. Cancelled.")
            return

        if not selected_replies:
            print("No valid replies selected. Cancelled.")
            return

        confirm = input(f"Post {len(selected_replies)} selected replies? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Cancelled.")
            return

        print(f"\nPosting {len(selected_replies)} replies...")
        results = post_all_replies(selected_replies)

    elif action == 'a':
        confirm = input(f"Post all {len(batch.replies)} replies? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Cancelled.")
            return

        print(f"\nPosting {len(batch.replies)} replies...")
        results = post_all_replies(batch.replies)

    else:
        print("Invalid option. Cancelled.")
        return

    # Step 8: Summary
    print(f"\n{'='*50}")
    print(f"  Summary: Posted {len(results)} replies")
    print(f"{'='*50}")
    for result in results:
        print(f"  {result.get('url', 'N/A')}")


def list_posts():
    """Display all available pre-written posts."""
    print("\nAvailable posts:\n")
    for i, post in enumerate(POSTS, 1):
        print(f"  {i:2}. {post['title']}")
    print()


def preview_post(index: int):
    """Preview a post before sending."""
    post = POSTS[index]
    print(f"\n{'='*50}")
    print(f"Title: {post['title']}")
    print(f"{'='*50}")
    print(post['content'])
    print(f"{'='*50}")
    print(f"Character count: {len(post['content'])}/500\n")


def post_content_workflow():
    """Workflow for posting pre-written content."""
    while True:
        list_posts()

        choice = input("Enter post number to preview (or 'b' for back): ").strip()

        if choice.lower() == 'b':
            return

        try:
            index = int(choice) - 1
            if 0 <= index < len(POSTS):
                preview_post(index)

                confirm = input("Post this to Mastodon? (y/n): ").strip().lower()
                if confirm == 'y':
                    try:
                        result = post_to_mastodon(POSTS[index]['content'])
                        print(f"\nPosted successfully!")
                        print(f"URL: {result.get('url', 'N/A')}\n")
                    except requests.exceptions.HTTPError as e:
                        print(f"\nError posting: {e}")
                        print(f"Response: {e.response.text}\n")
                else:
                    print("Post cancelled.\n")
            else:
                print(f"Invalid choice. Please enter 1-{len(POSTS)}.\n")
        except ValueError:
            print("Please enter a valid number.\n")


def main():
    """Main entry point."""
    print("\n" + "="*50)
    print("  Computational Biology Mastodon Poster")
    print("="*50)

    if not load_config():
        return

    while True:
        print("\nMain Menu:")
        print("  [1] Post pre-written content")
        print("  [2] Search & Reply")
        print("  [q] Quit")

        choice = input("\nSelect mode: ").strip().lower()

        if choice == 'q':
            print("Goodbye!")
            break
        elif choice == '1':
            post_content_workflow()
        elif choice == '2':
            if not OPENROUTER_API_KEY:
                print("Error: OPENROUTER_API_KEY required for Search & Reply mode")
                continue
            reply_workflow()
        else:
            print("Invalid choice. Please enter 1, 2, or q.")


if __name__ == "__main__":
    main()
