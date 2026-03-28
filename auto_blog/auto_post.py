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

# Existing articles for internal linking
EXISTING_ARTICLES = {
    "credit score": "/the-ultimate-guide-to-credit-scores-in-the-philippines-2026/",
    "CIC credit report": "/how-to-read-your-cic-credit-report-in-the-philippines-a-step-by-step-guide/",
    "personal loan": "/personal-loan-philippines-best-options-smart-qualification/",
    "credit card rewards": "/credit-card-rewards-philippines-maximize-your-perks/",
    "credit score vs credit report": "/credit-score-vs-credit-report-in-the-philippines-whats-the-difference/",
    "online lending scams": "/how-to-avoid-online-lending-scams-in-the-philippines-2026-complete-guide/",
    "budgeting": "/cost-of-living-budgeting-why-its-the-top-priority-for-millennials-gen-z-living-paycheck-to-paycheck/",
    "top credit cards": "/top-5-credit-cards-in-the-philippines-2025-lowest-rates-no-annual-fees-for-life-naffl/",
    "online loan apps": "/deep-dive-into-the-philippines-top-online-loan-apps/",
}


# ---------------------------------------------------------------------------
# Topics (with real data points for grounding)
# ---------------------------------------------------------------------------
def load_topics():
    """Return the pool of SEO topics with real Philippine financial data."""
    return [
        {
            "keyword": "credit card application Philippines",
            "angle": "first-time applicant guide with actual bank requirements and approval tips",
            "category": "Credit Cards",
            "img_query": "credit card application form",
            "data_points": (
                "BPI: min ₱15k/mo income, 21 yrs old. BDO: min ₱10k/mo (Visa Classic). "
                "Metrobank: min ₱15k/mo. UnionBank: min ₱12k/mo. Processing: 7-14 days. "
                "Annual fees: ₱1,500-₱5,000 (often waived 1st year). Interest: 2-3.5%/month."
            ),
        },
        {
            "keyword": "improve credit score fast Philippines",
            "angle": "month-by-month plan with real impact numbers on your CIC score",
            "category": "Credit Education",
            "img_query": "financial growth chart upward",
            "data_points": (
                "CIC score range: 300-850. >700 = good. On-time payment = ~35% of score. "
                "Utilization below 30% boosts score 20-40 points in 2-3 months. "
                "Each new account inquiry drops score ~15 points. "
                "Dispute errors at CIC: free, takes 30 days. Negative records: fall off after 5 years."
            ),
        },
        {
            "keyword": "debt consolidation Philippines",
            "angle": "real bank programs with rates and a savings calculation example",
            "category": "Financial Planning",
            "img_query": "debt management planning documents",
            "data_points": (
                "CIMB balance transfer: 0% for 3 months then 1.49%/mo. "
                "BPI: 0.59%/mo for 12-36 months. Metrobank: 0.79%/mo. "
                "Average CC interest without consolidation: 2-3.5%/mo (24-42% APR). "
                "₱50k debt at 3%/mo vs 0.79%/mo saves ₱13,260/year."
            ),
        },
        {
            "keyword": "salary loan Philippines 2026",
            "angle": "SSS vs Pag-IBIG vs bank salary loans - which is cheapest?",
            "category": "Loans",
            "img_query": "salary paycheck office desk",
            "data_points": (
                "SSS: up to ₱52k, 10%/yr, 24 payments. "
                "Pag-IBIG MPL: up to 80% of savings, 10.5%/yr, max 24 months. "
                "BPI: ₱20k-₱2M, 1.2-1.6%/mo. CIMB: ₱30k-₱1M, from 1.19%/mo."
            ),
        },
        {
            "keyword": "financial literacy Philippines",
            "angle": "the 5 money mistakes most Filipinos make (with BSP survey data)",
            "category": "Financial Planning",
            "img_query": "financial planning notebook money",
            "data_points": (
                "BSP 2023: only 2% of adult Filipinos are financially literate on all 3 dimensions. "
                "53% have no emergency fund. Median household income: ~₱22k/month (PSA 2023). "
                "Ideal emergency fund: 3-6 months = ₱66k-₱132k for median household."
            ),
        },
        {
            "keyword": "home loan Philippines 2026",
            "angle": "actual rates from top 5 banks plus a monthly payment example",
            "category": "Loans",
            "img_query": "house keys home buying Philippines",
            "data_points": (
                "BDO: 6.5% fixed 1yr, 7.5% 3yr. BPI: 6.25% 1yr, 7.0% 3yr. "
                "Metrobank: 6.88% 1yr. Pag-IBIG: 3% (<₱750k) or 6.5% (>₱750k), up to ₱6M, 30yr. "
                "Down payment: 10-20%. Example: ₱3M at 6.5% for 20yr = ₱22,363/mo."
            ),
        },
        {
            "keyword": "SSS loan application online",
            "angle": "exact step-by-step process at my.sss.gov.ph with requirements",
            "category": "Government Services",
            "img_query": "online application form government",
            "data_points": (
                "Need: 36 contributions total, 6 within last 12 months. "
                "Max: avg monthly salary credit × 24 (cap ₱52,000). Interest: 10%/yr. "
                "Apply at my.sss.gov.ph. Processing: 3-5 business days. Disbursement via PESONet."
            ),
        },
        {
            "keyword": "Pag-IBIG housing loan 2026",
            "angle": "complete requirements checklist and monthly payment computation",
            "category": "Government Services",
            "img_query": "housing loan documents family home",
            "data_points": (
                "Need: 24 monthly contributions. Loan: up to ₱6M regular, ₱10M affordable. "
                "Rate: 3%/yr (≤₱750k), 6.5%/yr (>₱750k). Max term: 30 years. "
                "₱2M at 6.5% for 30yr = ₱12,639/mo. Processing: 15-20 working days."
            ),
        },
        {
            "keyword": "online lending apps Philippines safe",
            "angle": "SEC-registered vs illegal - a checklist to protect yourself",
            "category": "Loans",
            "img_query": "mobile phone lending app",
            "data_points": (
                "SEC-registered (2026): Tonik, Maya Credit, CIMB, Tala, Cashalo, Lendly. "
                "Red flags: requires contacts/gallery access, interest >15%/month, no SEC number. "
                "BSP limit: max 6%/month for digital lenders. SEC blocked 200+ apps in 2025."
            ),
        },
        {
            "keyword": "build credit history Philippines",
            "angle": "zero-to-700 roadmap for fresh graduates (month by month)",
            "category": "Credit Education",
            "img_query": "young professional career growth",
            "data_points": (
                "Timeline: 6 months for CIC record, 12-18 months for 650+. "
                "Starters: secured CC (BPI/BDO ₱10k deposit), postpaid plan (Globe/Smart). "
                "CIMB credit builder: ₱30k min. After 12 months: eligible for unsecured cards."
            ),
        },
        {
            "keyword": "emergency fund Philippines 2026",
            "angle": "best high-yield accounts to park your fund (rate comparison)",
            "category": "Financial Planning",
            "img_query": "savings piggy bank money coins",
            "data_points": (
                "Tonik: up to 5.5%/yr. Maya: 3.5%/yr. SeaBank: 5%/yr (promo). "
                "CIMB UpSave: 2.6%/yr. Traditional banks: 0.1-0.5%/yr. "
                "Inflation 2025: ~3.5%. Savings below 3.5%/yr lose purchasing power."
            ),
        },
        {
            "keyword": "car loan Philippines 2026",
            "angle": "bank vs dealer financing - which actually saves you money?",
            "category": "Loans",
            "img_query": "car purchase dealership keys",
            "data_points": (
                "Banks: BPI 6-8%/yr, BDO 7-10%/yr, EastWest 8-12%/yr. "
                "Dealer in-house: 12-18%/yr hidden as 'add-on'. "
                "₱800k loan 5yr: bank 7% = ₱15,842/mo, dealer 15% add-on = ₱19,333/mo. "
                "Savings choosing bank: ₱209,460 over 5 years. Down payment: 20-30%."
            ),
        },
        {
            "keyword": "GCash credit features 2026",
            "angle": "GCredit, GGives, GLoan - limits, rates, and CIC impact",
            "category": "Fintech",
            "img_query": "mobile payment digital wallet smartphone",
            "data_points": (
                "GCredit: ₱1k-₱30k limit, 5% fee. Reports to CIC since 2023. "
                "GGives: 3-12 months installment, 3.49% service fee. "
                "GLoan (via CIMB/Fuse): ₱5k-₱25k, 3.99-5.99%/mo, 6-12 months. "
                "Late payment: 5% penalty + negative CIC record."
            ),
        },
        {
            "keyword": "loan calculator Philippines",
            "angle": "how to calculate the TRUE cost of a loan (EIR vs add-on rate explained)",
            "category": "Financial Planning",
            "img_query": "calculator finance money planning",
            "data_points": (
                "Add-on 1.5%/mo on ₱100k for 12mo: total interest ₱18k, EIR = 32.4%/yr. "
                "Diminishing 1.5%/mo: total interest ₱9,750, EIR = 18%/yr. "
                "BSP requires EIR disclosure since 2019. Processing fees (1-3%) add to cost."
            ),
        },
        {
            "keyword": "bad credit loan Philippines",
            "angle": "realistic options that won't trap you deeper (and what to avoid)",
            "category": "Loans",
            "img_query": "financial difficulty stress help",
            "data_points": (
                "Options: SSS salary loan (no credit check), Pag-IBIG MPL, cooperative loans, pawnshop. "
                "Avoid: 5-6 lending (20%/month), unregistered apps. "
                "Rebuild: secured CC → 6 months on-time → better options. "
                "Banks have hardship programs: lower rate + extended term on request."
            ),
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
# Article generation (Gemini) & post-processing
# ---------------------------------------------------------------------------
def build_internal_links_ref(current_keyword):
    """Build internal links string for prompt, excluding current topic."""
    links = []
    for topic, path in EXISTING_ARTICLES.items():
        if current_keyword.lower() not in topic.lower():
            links.append(f'  - "{topic}": {WP_SITE}{path}')
    return "\n".join(links[:6])  # Max 6 links to keep prompt focused


def replace_internal_link_placeholders(html):
    """Replace [INTERNAL_LINK: topic] placeholders with real <a> tags."""
    def replacer(match):
        topic_hint = match.group(1).strip().lower()
        for topic, path in EXISTING_ARTICLES.items():
            if topic_hint in topic.lower() or topic.lower() in topic_hint:
                url = f"{WP_SITE}{path}"
                return f'<a href="{url}">{match.group(1).strip()}</a>'
        # No match found - just return the text without link
        return match.group(1).strip()

    return re.sub(r"\[INTERNAL_LINK:\s*([^\]]+)\]", replacer, html)


def generate_faq_schema(article_content):
    """Extract FAQ section from content and generate JSON-LD schema."""
    # Look for Q&A patterns in the content
    faq_items = []
    # Match <h3> followed by <p> patterns that look like Q&A
    pattern = r"<h3[^>]*>([^<]+\?)</h3>\s*<p>([^<]+(?:<[^/][^>]*>[^<]*</[^>]*>)*[^<]*)</p>"
    matches = re.findall(pattern, article_content, re.DOTALL)
    for question, answer in matches[:5]:
        clean_answer = re.sub(r"<[^>]+>", "", answer).strip()
        if len(clean_answer) > 30:
            faq_items.append({"question": question.strip(), "answer": clean_answer})

    if not faq_items:
        return ""

    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": item["question"],
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": item["answer"],
                },
            }
            for item in faq_items
        ],
    }
    return f'\n<script type="application/ld+json">\n{json.dumps(schema, ensure_ascii=False, indent=2)}\n</script>'


def generate_article(topic, image_data=None):
    """Use Gemini to generate a data-grounded, human-readable blog article."""
    GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

    # Build image placement instructions
    img_instructions = ""
    if image_data and len(image_data) > 0:
        img_tags = []
        for i, img in enumerate(image_data):
            img_tags.append(
                f'  Image {i + 1}: <figure><img src="{img["url"]}" alt="{img["alt"]}" '
                f'class="wp-image-{img["id"]}" style="width:100%;height:auto;" />'
                f'<figcaption>Photo by {img["photographer"]} on Pexels</figcaption></figure>'
            )
        img_list = "\n".join(img_tags)
        img_instructions = f"""
IMAGES (insert naturally between sections):
{img_list}
Place the first image after the opening paragraph, distribute the rest evenly."""

    # Build internal links reference
    internal_links = build_internal_links_ref(topic["keyword"])

    # Get data points
    data_points = topic.get("data_points", "")

    prompt = f"""You are a Filipino personal finance blogger writing for Credit Kaagapay (a free credit score & loan finder app). Write like a real person, not an AI.

TOPIC: {topic['keyword']}
ANGLE: {topic['angle']}
CATEGORY: {topic['category']}

REAL DATA TO USE (weave these into the article naturally):
{data_points}

EXISTING ARTICLES FOR INTERNAL LINKS (link to 2-3 of these where relevant):
{internal_links}
{img_instructions}

=== WRITING STYLE (THIS IS THE MOST IMPORTANT PART) ===

VOICE: Write like a knowledgeable friend who works in banking. Casual but credible. Use "you" constantly. Sprinkle in 1-2 Filipino words naturally (e.g., "kumusta", "pera", "sweldo").

BANNED OPENINGS (if you start with any of these, the article fails):
- "In the bustling..." / "In today's..." / "In the dynamic..."
- "As we all know..." / "It's no secret that..."
- "Whether you're a..." / "Are you looking for..."
- Any sentence that could describe any country (not specific to Philippines)

GOOD OPENINGS (pick one style):
- A specific peso amount scenario: "Last month, my friend applied for a ₱50,000 loan at BPI and got rejected. Here's what she did wrong."
- A surprising data point: "Only 2% of Filipino adults are financially literate, according to BSP. That's not a typo."
- A direct challenge: "You're probably paying way more interest than you need to. Let me show you the math."

STRUCTURE:
1. Hook paragraph (2-3 sentences, specific scenario or data)
2. Key Takeaways box (styled div with 4-5 bullet points of the most useful info)
3. Main content in 3-4 sections with H2 headings
4. At least ONE comparison table (HTML <table>) with real numbers
5. FAQ section: 3 questions as H3 with "?" - answer in the next <p>
6. CTA paragraph mentioning Credit Kaagapay app

PARAGRAPH RULES:
- Max 2-3 sentences per paragraph
- Every paragraph must contain either: a number, a bank name, a peso amount, or an action step
- If a paragraph is just "filler commentary" with no concrete info, delete it

FORMATTING:
- <h2> for main sections, <h3> for subsections and FAQ questions
- <table> with <thead>/<tbody> for comparisons (include ₱ amounts)
- <blockquote> for pro tips (max 2 per article)
- <strong> sparingly (max 2 per section)
- Key Takeaways: <div style="background:#f0f7ff;border-left:4px solid #2563eb;padding:20px;margin:20px 0;border-radius:8px;">
- Internal links: use <a href="URL">anchor text</a> directly

LENGTH: 1200-1500 words. Every word must earn its place.

OUTPUT (valid JSON only, no markdown fences):
{{
    "title": "under 60 chars, includes keyword, not clickbait",
    "meta_description": "under 155 chars, includes keyword, compelling",
    "excerpt": "2 sentences summarizing the key value",
    "content": "full HTML content",
    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
    "focus_keyword": "{topic['keyword']}"
}}"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.9,
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

    article = json.loads(text)

    # Post-processing
    content = article.get("content", "")

    # Replace any remaining [INTERNAL_LINK:] placeholders
    content = replace_internal_link_placeholders(content)

    # Generate and append FAQ schema
    faq_schema = generate_faq_schema(content)
    if faq_schema:
        content += faq_schema
        print("  FAQ Schema generated")

    article["content"] = content
    return article


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
