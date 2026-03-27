#!/usr/bin/env python3
"""
Credit Kaagapay - Auto Blog Poster
Uses Google Gemini to generate SEO blog articles with Pexels images,
then publishes to WordPress.
"""

import json
import os
import sys
import random
import re
import time
import io
import requests
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
WP_SITE = "https://www.creditkaagapay.com"
WP_API = f"{WP_SITE}/wp-json/wp/v2"
WP_USERNAME = os.environ.get("WP_USERNAME", "")
WP_APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")

PEXELS_API = "https://api.pexels.com/v1"


# ---------------------------------------------------------------------------
# Topics
# ---------------------------------------------------------------------------
def load_topics():
    """Return the pool of SEO topics to write about."""
    return [
        {
            "keyword": "credit score Philippines",
            "angle": "how to check and improve your credit score in the Philippines",
            "category": "Credit Education",
            "img_query": "credit score finance Philippines",
        },
        {
            "keyword": "CIC credit report",
            "angle": "complete guide to getting your free CIC credit report",
            "category": "Credit Education",
            "img_query": "credit report document",
        },
        {
            "keyword": "personal loan Philippines",
            "angle": "best personal loan options and how to qualify",
            "category": "Loans",
            "img_query": "personal loan money Philippines",
        },
        {
            "keyword": "credit card application Philippines",
            "angle": "tips for first-time credit card applicants in the Philippines",
            "category": "Credit Cards",
            "img_query": "credit card application",
        },
        {
            "keyword": "improve credit score fast",
            "angle": "actionable steps to improve your credit score quickly",
            "category": "Credit Education",
            "img_query": "financial growth chart",
        },
        {
            "keyword": "debt consolidation Philippines",
            "angle": "how to consolidate debt and manage payments",
            "category": "Financial Planning",
            "img_query": "debt management finance",
        },
        {
            "keyword": "salary loan Philippines",
            "angle": "comparing salary loan providers and interest rates",
            "category": "Loans",
            "img_query": "salary paycheck office",
        },
        {
            "keyword": "financial literacy Philippines",
            "angle": "essential financial literacy tips for Filipino professionals",
            "category": "Financial Planning",
            "img_query": "financial education learning",
        },
        {
            "keyword": "home loan Philippines 2026",
            "angle": "guide to home loans, requirements, and best rates",
            "category": "Loans",
            "img_query": "house keys home buying",
        },
        {
            "keyword": "SSS loan application",
            "angle": "step-by-step guide to applying for SSS loans online",
            "category": "Government Services",
            "img_query": "government services application form",
        },
        {
            "keyword": "Pag-IBIG housing loan",
            "angle": "how to apply for Pag-IBIG housing loan and requirements",
            "category": "Government Services",
            "img_query": "housing loan home family",
        },
        {
            "keyword": "online lending apps Philippines",
            "angle": "safe and SEC-registered online lending apps review",
            "category": "Loans",
            "img_query": "mobile app finance smartphone",
        },
        {
            "keyword": "build credit history Philippines",
            "angle": "how to build credit history from scratch",
            "category": "Credit Education",
            "img_query": "building blocks growth",
        },
        {
            "keyword": "credit score meaning",
            "angle": "understanding what your credit score number means",
            "category": "Credit Education",
            "img_query": "numbers score data analytics",
        },
        {
            "keyword": "emergency fund Philippines",
            "angle": "how to build an emergency fund on a Filipino salary",
            "category": "Financial Planning",
            "img_query": "savings piggy bank money",
        },
        {
            "keyword": "car loan Philippines",
            "angle": "comparing car loan options and how to get approved",
            "category": "Loans",
            "img_query": "car purchase keys auto",
        },
        {
            "keyword": "GCash credit features",
            "angle": "using GCash for credit building and loan access",
            "category": "Fintech",
            "img_query": "mobile payment digital wallet",
        },
        {
            "keyword": "credit card rewards Philippines",
            "angle": "maximizing credit card rewards and cashback",
            "category": "Credit Cards",
            "img_query": "rewards cashback shopping",
        },
        {
            "keyword": "loan calculator Philippines",
            "angle": "how to use loan calculators to plan your borrowing",
            "category": "Financial Planning",
            "img_query": "calculator finance planning",
        },
        {
            "keyword": "bad credit loan Philippines",
            "angle": "loan options available even with a low credit score",
            "category": "Loans",
            "img_query": "financial difficulty help",
        },
    ]


# ---------------------------------------------------------------------------
# WordPress helpers
# ---------------------------------------------------------------------------
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
        if any(keyword_lower in title for title in existing_titles):
            continue
        return topic

    # All topics covered - pick a random one with a fresh angle
    topic = random.choice(topics)
    topic["angle"] = f"latest updates and tips about {topic['keyword']} in 2026"
    return topic


# ---------------------------------------------------------------------------
# Pexels image helpers
# ---------------------------------------------------------------------------
def search_pexels_images(query, count=3):
    """Search Pexels for images matching query. Returns list of photo dicts."""
    if not PEXELS_API_KEY:
        print("  Warning: PEXELS_API_KEY not set, skipping images")
        return []

    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": count * 2, "orientation": "landscape"}

    try:
        resp = requests.get(
            f"{PEXELS_API}/search", headers=headers, params=params, timeout=30
        )
        if resp.status_code == 200:
            photos = resp.json().get("photos", [])
            # Pick `count` random photos from results for variety
            if len(photos) > count:
                photos = random.sample(photos, count)
            return photos
        else:
            print(f"  Pexels API error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"  Pexels search failed: {e}")
    return []


def download_and_strip_image(photo_url):
    """Download image and strip EXIF metadata. Returns (bytes, content_type)."""
    try:
        resp = requests.get(photo_url, timeout=60)
        if resp.status_code != 200:
            return None, None

        img_bytes = resp.content
        content_type = resp.headers.get("Content-Type", "image/jpeg")

        # Strip EXIF by re-encoding with Pillow if available
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(img_bytes))
            # Create clean image without EXIF
            clean = Image.new(img.mode, img.size)
            clean.putdata(list(img.getdata()))
            buf = io.BytesIO()
            fmt = "JPEG" if "jpeg" in content_type or "jpg" in content_type else "PNG"
            clean.save(buf, format=fmt, quality=85, optimize=True)
            return buf.getvalue(), content_type
        except ImportError:
            # Pillow not available - return raw bytes (still works, just keeps EXIF)
            print("  Warning: Pillow not installed, EXIF not stripped")
            return img_bytes, content_type

    except Exception as e:
        print(f"  Image download failed: {e}")
        return None, None


def upload_to_wordpress(img_bytes, filename, alt_text, content_type="image/jpeg"):
    """Upload image to WordPress media library. Returns media ID and URL."""
    auth = (WP_USERNAME, WP_APP_PASSWORD)

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": content_type,
    }

    try:
        resp = requests.post(
            f"{WP_API}/media",
            headers=headers,
            data=img_bytes,
            auth=auth,
            timeout=60,
        )
        if resp.status_code == 201:
            media = resp.json()
            media_id = media["id"]
            media_url = media["source_url"]

            # Update alt text
            requests.post(
                f"{WP_API}/media/{media_id}",
                json={"alt_text": alt_text},
                auth=auth,
                timeout=30,
            )
            return media_id, media_url
        else:
            print(f"  WP media upload error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"  WP media upload failed: {e}")
    return None, None


def fetch_and_upload_images(query, keyword, count=3):
    """Search, download, clean, and upload images. Returns list of (id, url, alt)."""
    photos = search_pexels_images(query, count)
    results = []

    for i, photo in enumerate(photos):
        # Use medium size (good quality, reasonable file size)
        photo_url = photo.get("src", {}).get("large", photo.get("src", {}).get("original", ""))
        photographer = photo.get("photographer", "Pexels")
        alt_text = f"{keyword} - Photo by {photographer} on Pexels"

        print(f"  Downloading image {i + 1}/{len(photos)} from Pexels...")
        img_bytes, content_type = download_and_strip_image(photo_url)
        if not img_bytes:
            continue

        # Generate a clean filename
        slug = re.sub(r"[^a-z0-9]+", "-", keyword.lower()).strip("-")
        ext = "jpg" if "jpeg" in (content_type or "") else "png"
        filename = f"{slug}-{i + 1}.{ext}"

        print(f"  Uploading {filename} to WordPress...")
        media_id, media_url = upload_to_wordpress(img_bytes, filename, alt_text, content_type)
        if media_id:
            results.append({"id": media_id, "url": media_url, "alt": alt_text, "photographer": photographer})
            print(f"  Uploaded: {media_url}")

    return results


# ---------------------------------------------------------------------------
# Article generation (Gemini)
# ---------------------------------------------------------------------------
def generate_article(topic, image_data=None):
    """Use Gemini REST API to generate an SEO-optimized, highly readable blog article."""
    GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

    # Build image placement instructions
    img_instructions = ""
    if image_data and len(image_data) > 0:
        img_tags = []
        for i, img in enumerate(image_data):
            img_tags.append(
                f'  Image {i + 1}: <img src="{img["url"]}" alt="{img["alt"]}" '
                f'class="wp-image-{img["id"]}" style="width:100%;height:auto;" />'
            )
        img_list = "\n".join(img_tags)
        img_instructions = f"""

**Images available for the article (INSERT these naturally within the article body):**
{img_list}

IMPORTANT image placement rules:
- Insert the FIRST image right after the opening paragraph (before the first H2)
- Distribute remaining images evenly throughout the article between sections
- Wrap each image in a <figure> tag with a <figcaption> that includes photographer credit
- Example: <figure><img src="..." alt="..." style="width:100%;height:auto;" /><figcaption>Photo by [Photographer] on Pexels</figcaption></figure>
"""

    prompt = f"""You are an expert content writer creating an article for Credit Kaagapay, a fintech app in the Philippines that helps users check their credit scores, access CIC credit reports, and find AI-powered loan recommendations.

**Target Keyword:** {topic['keyword']}
**Angle:** {topic['angle']}
**Category:** {topic['category']}
{img_instructions}

Write a blog article following these STRICT readability and quality guidelines:

## READABILITY RULES (MOST IMPORTANT):
1. **Opening hook**: Start with a relatable scenario, surprising statistic, or direct question that connects with Filipino readers. NO generic openings.
2. **Short paragraphs**: Maximum 3 sentences per paragraph. White space is your friend.
3. **Conversational tone**: Write like you're explaining to a smart friend over coffee. Use "you" and "your" frequently. Avoid stiff, formal language.
4. **Concrete examples**: Every key point MUST include a specific, real-world example relevant to Filipinos (e.g., actual bank names, peso amounts, specific steps).
5. **Scannable structure**: Use H2 for main sections, H3 for subsections. Add bullet points or numbered lists in EVERY section.
6. **Transition sentences**: Every section must flow naturally into the next. Use bridge sentences.
7. **Filipino context**: Reference local institutions (BDO, BPI, Metrobank, SSS, Pag-IBIG), peso amounts, and Filipino financial habits.

## CONTENT RULES:
- Title: Catchy, includes keyword, under 60 characters
- Length: 1200-1800 words of SUBSTANTIVE content
- Keyword usage: 5-8 times, placed naturally
- Meta description: Under 155 characters, compelling, includes keyword
- Include a "Key Takeaways" or "Quick Summary" box near the top (use a styled div)
- End with a clear call-to-action mentioning Credit Kaagapay app
- Include at least one comparison table or pros/cons list using HTML tables
- Add internal linking suggestions as [INTERNAL_LINK: topic] placeholders

## FORMATTING RULES:
- Use <strong> for emphasis on key terms (2-3 per section max)
- Use <blockquote> for important tips or warnings
- Use HTML tables with proper <thead> and <tbody> for comparisons
- Style the key takeaways box: <div style="background:#f0f7ff;border-left:4px solid #2563eb;padding:20px;margin:20px 0;border-radius:8px;">

## WHAT TO AVOID:
- NO filler phrases like "In today's world" or "As we all know"
- NO walls of text without formatting
- NO vague advice - be specific with numbers, steps, names
- NO keyword stuffing - it should read naturally
- NO overly promotional tone for Credit Kaagapay

**Output format (JSON):**
{{
    "title": "Article Title Here",
    "meta_description": "Compelling meta description here",
    "excerpt": "A 2-3 sentence summary for the post excerpt",
    "content": "<full HTML content here>",
    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
    "focus_keyword": "{topic['keyword']}"
}}

IMPORTANT: Return ONLY valid JSON. No markdown code fences or extra text."""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.85,
            "maxOutputTokens": 8192,
        },
    }

    # Retry up to 3 times with backoff
    for attempt in range(3):
        resp = requests.post(GEMINI_URL, json=payload, timeout=120)
        if resp.status_code == 200:
            break
        elif resp.status_code == 429:
            wait = 30 * (attempt + 1)
            print(f"  Rate limited, waiting {wait}s (attempt {attempt + 1}/3)...")
            time.sleep(wait)
        else:
            print(f"  Gemini API error {resp.status_code}: {resp.text[:300]}")
            if attempt == 2:
                sys.exit(1)
            time.sleep(10)

    data = resp.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()

    # Clean up potential markdown code fences
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n?", "", text)
        text = re.sub(r"\n?```$", "", text)

    return json.loads(text)


# ---------------------------------------------------------------------------
# WordPress publishing
# ---------------------------------------------------------------------------
def get_or_create_category(name):
    """Get category ID by name, create if not exists."""
    auth = (WP_USERNAME, WP_APP_PASSWORD)

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

    resp = requests.post(
        f"{WP_API}/categories",
        json={"name": name},
        auth=auth,
        timeout=30,
    )
    if resp.status_code == 201:
        return resp.json()["id"]

    print(f"Warning: Could not create category '{name}', using default")
    return 1


def get_or_create_tags(tag_names):
    """Get or create tags and return their IDs."""
    auth = (WP_USERNAME, WP_APP_PASSWORD)
    tag_ids = []

    for name in tag_names[:5]:
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


def publish_post(article, topic, featured_image_id=None):
    """Publish the article to WordPress."""
    auth = (WP_USERNAME, WP_APP_PASSWORD)

    cat_id = get_or_create_category(topic["category"])
    tag_ids = get_or_create_tags(article.get("tags", []))

    post_data = {
        "title": article["title"],
        "content": article["content"],
        "excerpt": article.get("excerpt", ""),
        "status": "publish",
        "categories": [cat_id],
        "tags": tag_ids,
        "meta": {},
    }

    # Set featured image if available
    if featured_image_id:
        post_data["featured_media"] = featured_image_id

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

        # Update Rank Math meta
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    if not all([WP_USERNAME, WP_APP_PASSWORD, GEMINI_API_KEY]):
        print("Error: Missing required environment variables")
        print("  WP_USERNAME, WP_APP_PASSWORD, GEMINI_API_KEY")
        sys.exit(1)

    print("=== Credit Kaagapay Auto Blog Poster ===")
    print(f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
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

    # Fetch images from Pexels
    image_data = []
    img_query = topic.get("img_query", topic["keyword"])
    if PEXELS_API_KEY:
        print(f"Searching Pexels for: {img_query}")
        image_data = fetch_and_upload_images(img_query, topic["keyword"], count=3)
        print(f"  Uploaded {len(image_data)} images")
    else:
        print("Skipping images (PEXELS_API_KEY not set)")
    print()

    # Generate article
    print("Generating article with Gemini...")
    article = generate_article(topic, image_data)
    print(f"Title: {article['title']}")
    print(f"Meta: {article.get('meta_description', 'N/A')}")
    print(f"Tags: {article.get('tags', [])}")
    print()

    # Publish
    featured_id = image_data[0]["id"] if image_data else None
    print("Publishing to WordPress...")
    post_id, post_url = publish_post(article, topic, featured_image_id=featured_id)
    print()
    print(f"Done! Article published at {post_url}")


if __name__ == "__main__":
    main()
