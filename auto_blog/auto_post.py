#!/usr/bin/env python3
"""
Credit Kaagapay - Auto Blog Poster
Uses Google Gemini to generate SEO blog articles and publishes to WordPress.
"""

import json
import os
import sys
import random
import re
import time
import requests
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
WP_SITE = "https://www.creditkaagapay.com"
WP_API = f"{WP_SITE}/wp-json/wp/v2"
WP_USERNAME = os.environ.get("WP_USERNAME", "")
WP_APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# SEO keyword topics for Credit Kaagapay
TOPIC_POOL = [
    # placeholder - filled below
]


def load_topics():
    """Return the pool of SEO topics to write about."""
    return [
        {
            "keyword": "credit score Philippines",
            "angle": "how to check and improve your credit score in the Philippines",
            "category": "Credit Education",
        },
        {
            "keyword": "CIC credit report",
            "angle": "complete guide to getting your free CIC credit report",
            "category": "Credit Education",
        },
        {
            "keyword": "personal loan Philippines",
            "angle": "best personal loan options and how to qualify",
            "category": "Loans",
        },
        {
            "keyword": "credit card application Philippines",
            "angle": "tips for first-time credit card applicants in the Philippines",
            "category": "Credit Cards",
        },
        {
            "keyword": "improve credit score fast",
            "angle": "actionable steps to improve your credit score quickly",
            "category": "Credit Education",
        },
        {
            "keyword": "debt consolidation Philippines",
            "angle": "how to consolidate debt and manage payments",
            "category": "Financial Planning",
        },
        {
            "keyword": "salary loan Philippines",
            "angle": "comparing salary loan providers and interest rates",
            "category": "Loans",
        },
        {
            "keyword": "financial literacy Philippines",
            "angle": "essential financial literacy tips for Filipino professionals",
            "category": "Financial Planning",
        },
        {
            "keyword": "home loan Philippines 2026",
            "angle": "guide to home loans, requirements, and best rates",
            "category": "Loans",
        },
        {
            "keyword": "SSS loan application",
            "angle": "step-by-step guide to applying for SSS loans online",
            "category": "Government Services",
        },
        {
            "keyword": "Pag-IBIG housing loan",
            "angle": "how to apply for Pag-IBIG housing loan and requirements",
            "category": "Government Services",
        },
        {
            "keyword": "online lending apps Philippines",
            "angle": "safe and SEC-registered online lending apps review",
            "category": "Loans",
        },
        {
            "keyword": "build credit history Philippines",
            "angle": "how to build credit history from scratch",
            "category": "Credit Education",
        },
        {
            "keyword": "credit score meaning",
            "angle": "understanding what your credit score number means",
            "category": "Credit Education",
        },
        {
            "keyword": "emergency fund Philippines",
            "angle": "how to build an emergency fund on a Filipino salary",
            "category": "Financial Planning",
        },
        {
            "keyword": "car loan Philippines",
            "angle": "comparing car loan options and how to get approved",
            "category": "Loans",
        },
        {
            "keyword": "GCash credit features",
            "angle": "using GCash for credit building and loan access",
            "category": "Fintech",
        },
        {
            "keyword": "credit card rewards Philippines",
            "angle": "maximizing credit card rewards and cashback",
            "category": "Credit Cards",
        },
        {
            "keyword": "loan calculator Philippines",
            "angle": "how to use loan calculators to plan your borrowing",
            "category": "Financial Planning",
        },
        {
            "keyword": "bad credit loan Philippines",
            "angle": "loan options available even with a low credit score",
            "category": "Loans",
        },
    ]


def get_existing_posts():
    """Fetch recent post titles to avoid duplicates."""
    try:
        resp = requests.get(
            f"{WP_API}/posts",
            params={"per_page": 50, "status": "publish"},
            timeout=30,
        )
        if resp.status_code == 200:
            return [p["title"]["rendered"].lower() for p in resp.json()]
    except Exception as e:
        print(f"Warning: Could not fetch existing posts: {e}")
    return []


def pick_topic(existing_titles):
    """Pick a random topic that hasn't been covered recently."""
    topics = load_topics()
    random.shuffle(topics)

    for topic in topics:
        keyword_lower = topic["keyword"].lower()
        # Skip if a very similar article already exists
        if any(keyword_lower in title for title in existing_titles):
            continue
        return topic

    # If all topics have been covered, pick a random one with a fresh angle
    topic = random.choice(topics)
    topic["angle"] = f"latest updates and tips about {topic['keyword']} in 2026"
    return topic


def generate_article(topic):
    """Use Gemini to generate an SEO-optimized blog article."""
    import google.generativeai as genai

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")

    prompt = f"""You are an expert SEO content writer for Credit Kaagapay, a fintech app in the Philippines that helps users check their credit scores, access CIC credit reports, and find AI-powered loan recommendations.

Write a comprehensive, SEO-optimized blog article with the following requirements:

**Target Keyword:** {topic['keyword']}
**Angle:** {topic['angle']}
**Category:** {topic['category']}

**Requirements:**
1. Title: Catchy, includes the target keyword, under 60 characters
2. Article length: 1200-1800 words
3. Structure: Use H2 and H3 headings throughout
4. Include the target keyword naturally 5-8 times
5. Include a meta description (under 160 characters)
6. Write in clear, professional English
7. Target audience: Filipino professionals and young adults
8. Include practical, actionable advice
9. Mention Credit Kaagapay naturally where relevant (not forced)
10. Include a call-to-action at the end encouraging readers to download Credit Kaagapay
11. Use bullet points and numbered lists for readability

**Output format (JSON):**
{{
    "title": "Article Title Here",
    "meta_description": "Meta description here",
    "content": "<h2>First Section</h2><p>Content...</p>...",
    "tags": ["tag1", "tag2", "tag3"],
    "focus_keyword": "{topic['keyword']}"
}}

IMPORTANT: Return ONLY valid JSON, no markdown code fences or extra text."""

    response = model.generate_content(prompt)
    text = response.text.strip()

    # Clean up potential markdown code fences
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n?", "", text)
        text = re.sub(r"\n?```$", "", text)

    return json.loads(text)


def get_or_create_category(name):
    """Get category ID by name, create if not exists."""
    auth = (WP_USERNAME, WP_APP_PASSWORD)

    # Search existing
    resp = requests.get(
        f"{WP_API}/categories",
        params={"search": name, "per_page": 10},
        auth=auth,
        timeout=30,
    )
    if resp.status_code == 200:
        for cat in resp.json():
            if cat["name"].lower() == name.lower():
                return cat["id"]

    # Create new
    resp = requests.post(
        f"{WP_API}/categories",
        json={"name": name},
        auth=auth,
        timeout=30,
    )
    if resp.status_code == 201:
        return resp.json()["id"]

    print(f"Warning: Could not create category '{name}', using default")
    return 1  # Default 'Uncategorized'


def get_or_create_tags(tag_names):
    """Get or create tags and return their IDs."""
    auth = (WP_USERNAME, WP_APP_PASSWORD)
    tag_ids = []

    for name in tag_names[:5]:  # Limit to 5 tags
        # Search existing
        resp = requests.get(
            f"{WP_API}/tags",
            params={"search": name, "per_page": 5},
            auth=auth,
            timeout=30,
        )
        found = False
        if resp.status_code == 200:
            for tag in resp.json():
                if tag["name"].lower() == name.lower():
                    tag_ids.append(tag["id"])
                    found = True
                    break

        if not found:
            resp = requests.post(
                f"{WP_API}/tags",
                json={"name": name},
                auth=auth,
                timeout=30,
            )
            if resp.status_code == 201:
                tag_ids.append(resp.json()["id"])

    return tag_ids


def publish_post(article, topic):
    """Publish the article to WordPress."""
    auth = (WP_USERNAME, WP_APP_PASSWORD)

    # Get category
    cat_id = get_or_create_category(topic["category"])

    # Get tags
    tag_ids = get_or_create_tags(article.get("tags", []))

    # Build post data
    post_data = {
        "title": article["title"],
        "content": article["content"],
        "status": "publish",
        "categories": [cat_id],
        "tags": tag_ids,
        "meta": {},
    }

    # Set Rank Math SEO meta via custom fields
    # These work if Rank Math REST API support is enabled
    rank_math_meta = {
        "rank_math_title": article["title"],
        "rank_math_description": article.get("meta_description", ""),
        "rank_math_focus_keyword": article.get("focus_keyword", topic["keyword"]),
    }

    resp = requests.post(
        f"{WP_API}/posts",
        json=post_data,
        auth=auth,
        timeout=60,
    )

    if resp.status_code == 201:
        post = resp.json()
        post_id = post["id"]
        post_url = post["link"]
        print(f"Published: {article['title']}")
        print(f"  URL: {post_url}")
        print(f"  ID: {post_id}")

        # Try to update Rank Math meta separately
        try:
            meta_resp = requests.post(
                f"{WP_API}/posts/{post_id}",
                json={"meta": rank_math_meta},
                auth=auth,
                timeout=30,
            )
            if meta_resp.status_code == 200:
                print("  Rank Math meta updated")
        except Exception:
            print("  Warning: Could not update Rank Math meta")

        return post_id, post_url
    else:
        print(f"Error publishing post: {resp.status_code}")
        print(resp.text[:500])
        sys.exit(1)


def main():
    # Validate config
    if not all([WP_USERNAME, WP_APP_PASSWORD, GEMINI_API_KEY]):
        print("Error: Missing required environment variables")
        print("  WP_USERNAME, WP_APP_PASSWORD, GEMINI_API_KEY")
        sys.exit(1)

    print(f"=== Credit Kaagapay Auto Blog Poster ===")
    print(f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print()

    # Get existing posts to avoid duplicates
    existing = get_existing_posts()
    print(f"Found {len(existing)} existing posts")

    # Pick topic
    topic = pick_topic(existing)
    print(f"Selected topic: {topic['keyword']}")
    print(f"Angle: {topic['angle']}")
    print(f"Category: {topic['category']}")
    print()

    # Generate article
    print("Generating article with Gemini...")
    article = generate_article(topic)
    print(f"Title: {article['title']}")
    print(f"Meta: {article.get('meta_description', 'N/A')}")
    print(f"Tags: {article.get('tags', [])}")
    print()

    # Publish
    print("Publishing to WordPress...")
    post_id, post_url = publish_post(article, topic)
    print()
    print(f"Done! Article published at {post_url}")


if __name__ == "__main__":
    main()
