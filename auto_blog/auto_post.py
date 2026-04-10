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

# Author info (E-E-A-T)
AUTHOR_NAME = "Tan, Erika Trizia"
AUTHOR_ROLE = "Marketing Manager at Credit Kaagapay"

# Existing articles for internal linking
EXISTING_ARTICLES = {
    "credit score": "/blog/ultimate-guide-credit-scores-philippines/",
    "CIC credit report": "/blog/how-to-read-your-cic-credit-report-in-the-philippines/",
    "personal loan": "/blog/personal-loan-philippines-best-options-smart-qualification/",
    "credit card rewards": "/blog/credit-card-rewards-philippines-maximize-your-perks/",
    "credit score vs credit report": "/blog/credit-score-vs-credit-report-in-the-philippines-whats-the-2/",
    "online lending scams": "/blog/how-to-avoid-online-lending-scams-in-the-philippines-2026-complete-guide/",
    "budgeting": "/blog/cost-of-living-budgeting-why-its-the-top-priority-for-millennials-gen-z-living-paycheck-to-paycheck/",
    "top credit cards": "/blog/top-5-credit-cards-in-the-philippines-2025-lowest-rates-no-annual-fees-for-life-naffl/",
    "online loan apps": "/blog/deep-dive-into-the-philippines-top-online-loan-apps/",
    "improve credit score": "/blog/5-simple-habits-that-improve-your-credit-score/",
    "cash loan manila": "/blog/cash-loan-manila-your-2026-guide-to-fast-fair-funds/",
    "what is credit report": "/blog/what-is-a-credit-report-and-why-does-it-matter/",
    "why good credit matters": "/blog/why-good-credit-matters/",
    "personal loan vs credit card": "/blog/personal-loan-vs-credit-card-whats-right-for-you/",
}


# ---------------------------------------------------------------------------
# 3-Tier Keyword System
# Tier 1 (60%): Product-related  |  Tier 2 (30%): Traffic  |  Tier 3 (10%): Brand
# ---------------------------------------------------------------------------
TIER_1_KEYWORDS = [
    "online loan philippines", "personal loan philippines", "cash loan philippines",
    "CIC credit report philippines", "bad credit loan philippines", "emergency loan philippines",
]

TIER_2_KEYWORDS = [
    "fast loan", "quick loan", "loan for unemployed", "OFW loan",
    "online loan app", "loan calculator PH",
]

TIER_3_KEYWORDS = [
    "salary loan", "credit score philippines", "student loan",
]

CORE_WORDS = [
    "cash loan", "online loan", "personal loan",
    "salary loan", "emergency loan",
    "credit loan", "money loan", "loan",
]

MODIFIERS = [
    "fast", "instant", "low interest", "legit",
    "best", "easy approval", "same day",
]

AUDIENCE_WORDS = [
    "no payslip", "unemployed", "with bad credit",
    "self employed", "OFW", "student",
]

GEO_WORDS = [
    "philippines", "manila", "cebu", "davao",
]

# ---------------------------------------------------------------------------
# Title Pattern System (long-tail, problem-specific titles)
# ---------------------------------------------------------------------------
TITLE_PATTERNS = [
    "how to get a loan without {constraint} in philippines",
    "loan for {audience} philippines",
    "best loan apps for {situation} philippines",
    "{amount} peso loan without {constraint}",
    "how to apply for a loan as a {audience} in the philippines",
    "where to get {situation} loan without {constraint} philippines",
    "{situation} cash loan for {audience} philippines",
]

TITLE_CONSTRAINTS = ["no payslip", "no valid id", "no credit check"]
TITLE_AUDIENCES = ["unemployed", "student", "first time borrower"]
TITLE_SITUATIONS = ["emergency", "instant", "same day"]
TITLE_AMOUNTS = ["5000", "10000", "20000", "50000"]

# News-style title patterns (used when article is news-based)
NEWS_TITLE_PATTERNS = [
    "What {event} Means for Borrowers in the Philippines",
    "How {event} Affects Loan Access in the Philippines",
    "{event}: What It Means for People Who Need Loans",
    "{event} and What Filipino Borrowers Should Know",
    "How {event} Could Change Lending in the Philippines",
]

# FAQ templates (appended to every article)
FAQ_TEMPLATES = [
    "Can I get a loan without {constraint} in the Philippines?",
    "What are the requirements for {keyword}?",
    "How fast can I get approved for a loan in the Philippines?",
    "Is it safe to apply for {keyword} online?",
    "What happens if I can't repay my {keyword} on time?",
    "How much can I borrow with {keyword}?",
]

CREDIT_KEYWORDS = [
    "credit score philippines free", "how to check CIC credit report",
    "improve credit score fast philippines",
    "credit card application first time philippines",
    "build credit history from zero philippines",
]

# Category-based data points (keyed by core word type)
CATEGORY_DATA_POINTS = {
    "loan": (
        "SSS salary loan: up to ₱52k, 10%/yr, 24 payments. "
        "Pag-IBIG MPL: up to 80% of savings, 10.5%/yr. "
        "BPI personal loan: ₱20k-₱2M, 1.2-1.6%/mo. CIMB: from 1.19%/mo. "
        "BSP max rate for digital lenders: 6%/month. SEC blocked 200+ illegal apps in 2025."
    ),
    "cash loan": (
        "Tonik Quick Loan: up to ₱50k, 1.59%/mo, disbursed in 1 hour. "
        "Maya Credit: ₱2k-₱30k, 3.5% flat fee. Cashalo: ₱1k-₱25k, 2.99%/mo. "
        "GCash GLoan: ₱5k-₱25k, 3.99-5.99%/mo. Tala: ₱1k-₱15k, service fee varies. "
        "Average Filipino emergency expense: ₱15k-₱30k. 53% have no emergency fund (BSP)."
    ),
    "online loan": (
        "SEC-registered online lenders (2026): Tonik, Maya, CIMB, Tala, Cashalo, Lendly. "
        "Red flags: requires contacts/gallery access, interest >15%/month, no SEC number. "
        "BSP limit: max 6%/month for digital lenders. Process: 5-30 min approval, same-day disbursement. "
        "Typical requirements: valid ID, selfie, phone number, bank/e-wallet account."
    ),
    "quick loan": (
        "Fastest approvals: Tonik (1 hour), Maya (30 min), GCash GLoan (5 min). "
        "Same-day disbursement via GCash, Maya, or bank transfer (PESONet/InstaPay). "
        "InstaPay limit: ₱50k/transaction. PESONet: no limit but next-day for some banks. "
        "Quick loans typically charge 2-5% higher rates than standard bank loans."
    ),
    "fast loan": (
        "Fastest approvals: Tonik (1 hour), Maya (30 min), GCash GLoan (5 min). "
        "Same-day disbursement via GCash, Maya, or bank transfer (PESONet/InstaPay). "
        "InstaPay limit: ₱50k/transaction. PESONet: no limit but next-day for some banks. "
        "Quick loans typically charge 2-5% higher rates than standard bank loans."
    ),
    "personal loan": (
        "BPI: ₱20k-₱2M, 1.2-1.6%/mo, min income ₱15k. "
        "BDO: ₱10k-₱3M, 1.39%/mo, min income ₱15k. "
        "CIMB: ₱30k-₱1M, from 1.19%/mo, no min income stated. "
        "Metrobank: ₱20k-₱1M, 1.5%/mo. Processing: 3-7 business days."
    ),
    "credit loan": (
        "CIC score range: 300-850. >700 = good. On-time payment = ~35% of score. "
        "Credit card interest: 2-3.5%/month (24-42% APR). "
        "Balance transfer: BPI 0.59%/mo, CIMB 0% for 3 months then 1.49%/mo. "
        "Annual fees: ₱1,500-₱5,000. First-year waiver common."
    ),
    "money loan": (
        "BSP 2023: only 2% of Filipino adults are financially literate on all 3 dimensions. "
        "53% have no emergency fund. Median household income: ~₱22k/month (PSA 2023). "
        "5-6 lending (informal): 20%/month interest — AVOID. "
        "Cooperative loans: 6-12%/yr, require membership (₱500-₱2k share capital)."
    ),
    "salary loan": (
        "SSS: up to ₱52k, 10%/yr, 24 payments. Need 36 contributions, 6 within last 12 months. "
        "Pag-IBIG MPL: up to 80% of savings, 10.5%/yr, max 24 months. Need 24 contributions. "
        "BPI salary loan: ₱20k-₱2M, 1.2-1.6%/mo. CIMB: ₱30k-₱1M, from 1.19%/mo. "
        "Apply SSS at my.sss.gov.ph. Processing: 3-5 business days. Disbursement via PESONet."
    ),
    "emergency loan": (
        "Options: SSS salary loan (no credit check, 10%/yr), Pag-IBIG MPL (10.5%/yr). "
        "Digital: Tonik Quick Loan (1 hour), GCash GLoan (5 min), Maya Credit (30 min). "
        "Avoid: 5-6 lending (20%/month), unregistered apps. "
        "Average Filipino emergency: ₱15k-₱30k. Ideal emergency fund: 3-6 months expenses."
    ),
    "credit": (
        "CIC score range: 300-850. >700 = good. On-time payment = ~35% of score. "
        "Utilization below 30% boosts score 20-40 points in 2-3 months. "
        "Each new inquiry drops score ~15 points. Negative records: fall off after 5 years. "
        "Free CIC report: request via creditinfo.gov.ph. Dispute errors: free, takes 30 days."
    ),
    "comparison": (
        "SSS: 10%/yr, up to ₱52k. Pag-IBIG: 10.5%/yr, up to 80% of savings. "
        "BPI: 1.2-1.6%/mo. CIMB: from 1.19%/mo. BDO: 1.39%/mo. "
        "GCash GLoan: 3.99-5.99%/mo. Maya Credit: 3.5% flat fee. "
        "Add-on rate 1.5%/mo = EIR 32.4%/yr. Diminishing 1.5%/mo = EIR 18%/yr."
    ),
}

# Angles by audience type
AUDIENCE_ANGLES = {
    "no payslip": "options that don't require payslip or employment certificate",
    "unemployed": "legitimate loan options for those between jobs (with real alternatives)",
    "with bad credit": "how to get approved even with a low CIC score, plus rebuilding tips",
    "no credit history": "first-timer guide to building credit from zero and getting approved",
    "self employed": "documentation tricks and best lenders for freelancers and business owners",
    "OFW": "best remittance-linked loan products and overseas-friendly application process",
    "student": "student-friendly options with low requirements and small amounts",
    "first time borrower": "step-by-step for your very first loan application in the Philippines",
    "low income": "micro-loans and government programs for below-median-income Filipinos",
}

# Image queries by core word
IMG_QUERIES = {
    "loan": "loan application documents office",
    "cash loan": "cash money peso bills",
    "online loan": "mobile phone lending app",
    "quick loan": "fast approval smartphone",
    "fast loan": "fast approval smartphone",
    "personal loan": "personal finance planning documents",
    "credit loan": "credit card bank application",
    "money loan": "money coins savings planning",
    "salary loan": "salary paycheck office desk",
    "emergency loan": "emergency financial help",
    "credit": "credit score report financial",
    "comparison": "comparison chart financial planning",
}

# Category mapping
CORE_CATEGORIES = {
    "loan": "Loans",
    "cash loan": "Loans",
    "online loan": "Loans",
    "quick loan": "Loans",
    "fast loan": "Loans",
    "personal loan": "Loans",
    "credit loan": "Credit Cards",
    "money loan": "Financial Planning",
    "salary loan": "Government Services",
    "emergency loan": "Loans",
    "credit": "Credit Education",
    "comparison": "Financial Planning",
}


def _generate_title_from_pattern(existing_titles):
    """Generate a long-tail title from TITLE_PATTERNS, ensuring no duplicates."""
    patterns = list(TITLE_PATTERNS)
    random.shuffle(patterns)

    for pattern in patterns:
        for _ in range(20):
            title = pattern.format(
                constraint=random.choice(TITLE_CONSTRAINTS),
                audience=random.choice(TITLE_AUDIENCES),
                situation=random.choice(TITLE_SITUATIONS),
                amount=random.choice(TITLE_AMOUNTS),
            )
            # Skip if too long
            if len(title) > 70:
                continue
            title_lower = title.lower()
            # Check not duplicate or too similar to existing
            if not any(title_lower in t or t in title_lower for t in existing_titles):
                return title
    return None


def _is_topic_duplicate(keyword, existing_titles):
    """Check if keyword is too similar to any existing title (70% word overlap)."""
    kw_words = set(keyword.lower().split())
    for title in existing_titles:
        title_words = set(title.split())
        if not kw_words or not title_words:
            continue
        overlap = len(kw_words & title_words) / max(len(kw_words), 1)
        if overlap >= 0.7:
            return True
        if keyword.lower() in title or title in keyword.lower():
            return True
    return False


def generate_topic(existing_titles):
    """Generate a topic using 3-tier keyword system (60/30/10)."""

    # 40% title patterns, 36% tier keywords, 24% matrix generator
    roll = random.random()

    # Tier A: Long-tail title patterns (40%)
    if roll < 0.4:
        title_kw = _generate_title_from_pattern(existing_titles)
        if title_kw:
            return _build_topic_from_keyword(title_kw)

    # Tier B: 3-tier keyword selection (36%)
    if roll < 0.76:
        tier_roll = random.random()
        if tier_roll < 0.6:
            tier_keywords = TIER_1_KEYWORDS[:]
        elif tier_roll < 0.9:
            tier_keywords = TIER_2_KEYWORDS[:]
        else:
            tier_keywords = TIER_3_KEYWORDS[:]

        random.shuffle(tier_keywords)
        for kw in tier_keywords:
            if not _is_topic_duplicate(kw, existing_titles):
                return _build_topic_from_keyword(kw)

    # Tier C: Matrix combination (24%)
    attempts = 0
    while attempts < 50:
        core = random.choice(CORE_WORDS)
        modifier = random.choice(MODIFIERS)
        audience = random.choice(AUDIENCE_WORDS)
        geo = random.choice(GEO_WORDS)

        keyword = f"{modifier} {core} {audience} {geo}"

        if not _is_topic_duplicate(keyword, existing_titles):
            return _build_topic_from_keyword(keyword, core=core, audience=audience, geo=geo)

        attempts += 1

    # Fallback
    title_kw = _generate_title_from_pattern(existing_titles)
    if title_kw:
        return _build_topic_from_keyword(title_kw)

    core = random.choice(CORE_WORDS)
    modifier = random.choice(MODIFIERS)
    audience = random.choice(AUDIENCE_WORDS)
    geo = random.choice(GEO_WORDS)
    keyword = f"{modifier} {core} {audience} {geo}"
    return _build_topic_from_keyword(keyword, core=core, audience=audience, geo=geo)


def _build_topic_from_keyword(keyword, core=None, audience=None, geo=None):
    """Build a complete topic dict from a keyword string."""
    kw_lower = keyword.lower()

    # Detect core word from keyword
    if core is None:
        core = "loan"  # default
        for cw in sorted(CORE_WORDS, key=len, reverse=True):  # longest match first
            if cw in kw_lower:
                core = cw
                break
        # Check credit-specific keywords
        if "credit score" in kw_lower or "CIC" in kw_lower or "credit history" in kw_lower:
            core = "credit"
        if " vs " in kw_lower or "comparison" in kw_lower:
            core = "comparison"

    # Detect audience
    if audience is None:
        for aw in AUDIENCE_WORDS:
            if aw in kw_lower:
                audience = aw
                break

    # Detect geo
    if geo is None:
        for gw in GEO_WORDS:
            if gw in kw_lower:
                geo = gw
                break

    # Build angle
    angle_parts = []
    if audience and audience in AUDIENCE_ANGLES:
        angle_parts.append(AUDIENCE_ANGLES[audience])
    else:
        angle_parts.append("practical guide with real bank rates and step-by-step application tips")
    if geo and geo != "philippines":
        angle_parts.append(f"with local options available in {geo.title()}")

    angle = " — ".join(angle_parts)

    # Get data points (match to closest core word)
    data_points = CATEGORY_DATA_POINTS.get(core, CATEGORY_DATA_POINTS["loan"])

    # Get image query
    img_query = IMG_QUERIES.get(core, "loan finance philippines")

    # Get category
    category = CORE_CATEGORIES.get(core, "Loans")

    return {
        "keyword": keyword,
        "angle": angle,
        "category": category,
        "img_query": img_query,
        "data_points": data_points,
    }


# ---------------------------------------------------------------------------
# News Scanning (Gemini-powered)
# ---------------------------------------------------------------------------
def scan_news():
    """Use Gemini to find trending Philippine finance/lending news and score relevance.

    Returns list of dicts: [{"headline": str, "summary": str, "score": int, "event": str}]
    Score 1-10: how relevant the news is to Filipino borrowers/loans/credit.
    """
    if not GEMINI_API_KEY:
        return []

    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    prompt = f"""You are a Philippine financial news analyst. Today is {current_date}.

Think of the most recent (last 7 days) news events in the Philippines related to:
- Banking, lending, fintech, digital loans
- BSP monetary policy, interest rate changes
- SEC enforcement against illegal lenders
- Government loan programs (SSS, Pag-IBIG, GSIS)
- Major bank announcements, new loan products
- Economic events affecting borrowers (inflation, wage hikes, layoffs)
- GCash, Maya, Tonik, or other fintech news

For each news item, provide:
- headline: the news headline
- summary: 1-2 sentence summary
- score: relevance score 1-10 (10 = directly impacts Filipino borrowers, 1 = barely related)
- event: short phrase describing the event (for use in article titles, e.g. "BSP Rate Cut", "New SSS Loan Rules")

Return ONLY valid JSON array, no markdown fences:
[{{"headline": "...", "summary": "...", "score": 8, "event": "..."}}]

Return 3-5 news items. If you cannot find any recent relevant news, return an empty array: []"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2000},
    }

    GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"]
    for model in GEMINI_MODELS:
        model_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        try:
            resp = requests.post(model_url, json=payload, timeout=60)
            if resp.status_code == 200:
                text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                if text.startswith("```"):
                    text = re.sub(r"^```(?:json)?\n?", "", text)
                    text = re.sub(r"\n?```$", "", text)
                news_items = json.loads(text)
                if isinstance(news_items, list):
                    # Validate and clamp scores
                    valid = []
                    for item in news_items:
                        if all(k in item for k in ("headline", "summary", "score", "event")):
                            item["score"] = max(1, min(10, int(item["score"])))
                            valid.append(item)
                    return valid
        except (json.JSONDecodeError, KeyError, ValueError, requests.RequestException) as e:
            print(f"  News scan failed with {model}: {e}")
            continue
    return []


def _build_news_topic(news_item):
    """Build a topic dict from a news item for news-based article generation."""
    event = news_item["event"]
    headline = news_item["headline"]
    summary = news_item["summary"]

    return {
        "keyword": event.lower(),
        "angle": f"news analysis: {summary}",
        "category": "Financial News",
        "img_query": "philippines finance news economy",
        "data_points": (
            f"NEWS: {headline}\n"
            f"SUMMARY: {summary}\n"
            "Connect this news to practical impact on Filipino borrowers. "
            "Include relevant loan rates and options from existing data."
        ),
        "is_news": True,
        "news_event": event,
        "news_headline": headline,
    }


# ---------------------------------------------------------------------------
# WordPress helpers
# ---------------------------------------------------------------------------
def get_existing_posts():
    """Fetch recent post titles to avoid duplicates."""
    try:
        resp = requests.get(
            f"{WP_API}/posts",
            params={"per_page": 100, "status": "publish"},
            timeout=30,
        )
        if resp.status_code == 200:
            return [p["title"]["rendered"].lower() for p in resp.json()]
    except Exception as e:
        print(f"Warning: Could not fetch existing posts: {e}")
    return []


def pick_topic(existing_titles):
    """Pick a topic using score-based news priority logic.

    - If any news has score >= 8: prioritize news content
    - If news score is 7-8: mix with SEO content (50/50)
    - If no news score >= 7: use SEO keyword strategy
    """
    # Scan for news
    print("Scanning for trending finance news...")
    news_items = scan_news()
    if news_items:
        # Sort by score descending
        news_items.sort(key=lambda x: x["score"], reverse=True)
        top_score = news_items[0]["score"]
        top_news = news_items[0]
        print(f"  Top news: \"{top_news['event']}\" (score: {top_score})")

        # Filter out news that overlaps with existing titles
        unused_news = [
            n for n in news_items
            if not any(n["event"].lower() in t for t in existing_titles)
        ]

        if unused_news:
            top_score = unused_news[0]["score"]
            top_news = unused_news[0]

            if top_score >= 8:
                # High-relevance news: always use news
                print(f"  Score >= 8 → using news article: {top_news['event']}")
                return _build_news_topic(top_news)
            elif top_score >= 7:
                # Medium relevance: 50/50 mix
                if random.random() < 0.5:
                    print(f"  Score 7-8 → mixing: chose news article: {top_news['event']}")
                    return _build_news_topic(top_news)
                else:
                    print(f"  Score 7-8 → mixing: chose SEO keyword article")
            else:
                print(f"  Score < 7 → using SEO keyword strategy")
        else:
            print("  All news topics already covered, using SEO keywords")
    else:
        print("  No relevant news found, using SEO keywords")

    # SEO keyword strategy
    return generate_topic(existing_titles)


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
        alt_text = f"{keyword} in the Philippines - Photo by {photographer} on Pexels"

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
    faq_items = []
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


def generate_article_schema(title, excerpt, keyword, post_url=None, image_url=None):
    """Generate Article JSON-LD schema for rich snippets."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": excerpt,
        "author": {
            "@type": "Person",
            "name": AUTHOR_NAME,
            "jobTitle": AUTHOR_ROLE,
            "worksFor": {
                "@type": "Organization",
                "name": "Credit Kaagapay",
                "url": WP_SITE,
            },
        },
        "publisher": {
            "@type": "Organization",
            "name": "Credit Kaagapay",
            "logo": {
                "@type": "ImageObject",
                "url": f"{WP_SITE}/wp-content/uploads/credit-kaagapay-logo.png",
            },
        },
        "datePublished": now,
        "dateModified": now,
        "keywords": keyword,
    }
    if image_url:
        schema["image"] = image_url
    if post_url:
        schema["mainEntityOfPage"] = {"@type": "WebPage", "@id": post_url}
    return f'\n<script type="application/ld+json">\n{json.dumps(schema, ensure_ascii=False, indent=2)}\n</script>'


def generate_article(topic, image_data=None):
    """Use Gemini to generate a data-grounded, human-readable blog article."""

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

    # Get current date for freshness signal
    current_date = datetime.now(timezone.utc).strftime("%B %Y")

    # Build FAQ hints from templates
    faq_hints = []
    constraint = random.choice(TITLE_CONSTRAINTS)
    for tmpl in random.sample(FAQ_TEMPLATES, 3):
        faq_hints.append(tmpl.format(constraint=constraint, keyword=topic['keyword']))
    faq_hint_text = "\n".join(f"  - {q}" for q in faq_hints)

    # Build title rules based on article type (news vs SEO)
    is_news = topic.get("is_news", False)
    if is_news:
        news_event = topic.get("news_event", "")
        title_rules_section = f"""=== TITLE RULES (NEWS-STYLE — CRITICAL) ===

This is a NEWS article about: {news_event}

Generate a title that follows one of these patterns:
- "What [event] Means for Borrowers in the Philippines"
- "How [event] Affects Loan Access in the Philippines"
- "[Event]: What It Means for People Who Need Loans"
- "[Event] and What Filipino Borrowers Should Know"
- "How [event] Could Change Lending in the Philippines"

Title rules:
- Keep it natural and news-like
- Must include "Philippines"
- Connect the event to borrowing, loans, or money problems
- Keep under 70 characters
- Do NOT use generic SEO keyword patterns — this is a news piece"""
    else:
        title_rules_section = """=== TITLE RULES (SEO — CRITICAL) ===

Generate a title that follows one of these patterns:
- "How to Get a Loan Without [constraint] in Philippines"
- "Loan for [audience] Philippines"
- "Best Loan Apps for [situation] Philippines"
- "[amount] Peso Loan Without [constraint]"

Parameter pools:
  Constraints: no payslip, no valid id, no credit check
  Audience: unemployed, student, first time borrower
  Situations: emergency, instant, same day

Title rules:
- Must be natural and readable
- Avoid generic keywords like "online loan philippines" as the full title
- Focus on a specific user problem
- Keep under 70 characters
- Must be meaningfully different from common titles"""

    prompt = f"""You are a Filipino personal finance blogger writing for Credit Kaagapay (a free credit score & loan finder app). Write like a real person, not an AI.

TOPIC: {topic['keyword']}
ANGLE: {topic['angle']}
CATEGORY: {topic['category']}
DATE: {current_date}

REAL DATA TO USE (weave these into the article naturally):
{data_points}

EXISTING ARTICLES FOR INTERNAL LINKS (link to 2-3 of these where relevant):
{internal_links}
{img_instructions}

{title_rules_section}

=== SEO REQUIREMENTS (CRITICAL FOR RANKING) ===

KEYWORD DENSITY:
- The EXACT phrase "{topic['keyword']}" MUST appear in the first 100 words / opening paragraph
- Use the exact keyword 3-5 times naturally throughout the article
- Include 3-4 LSI (related) keywords naturally. Examples for this topic: generate variations like "[keyword] near me", "[keyword] requirements", "[keyword] rates 2026", "best [keyword] options"
- Use the keyword or a close variant in at least 2 H2 headings

E-E-A-T (CRITICAL — this is YMYL financial content):
- Add "Updated {current_date}" near the top (e.g., inside the Key Takeaways box or right after the title)
- Every rate, amount, or requirement MUST reference the source (bank name, BSP, SSS, Pag-IBIG, SEC)
- Include a compliance notice at the end: "<p><em>Disclaimer: Always verify loan terms directly with the lender. Check that any lending company is registered with the <a href='https://www.sec.gov.ph'>SEC</a> before applying. Rates and requirements may change — this guide was last updated {current_date}.</em></p>"

=== WRITING STYLE ===

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
IMPORTANT: The opening paragraph MUST contain the exact keyword "{topic['keyword']}".

STRUCTURE:
1. Hook paragraph (2-3 sentences, MUST include exact keyword, specific scenario or data)
2. Author byline right after the hook: <p style="color:#6b7280;font-size:0.9em;margin:8px 0 16px;">By {AUTHOR_NAME}, {AUTHOR_ROLE}</p>
3. Key Takeaways box (styled div with "Updated {current_date}" badge + 4-5 bullet points)
4. Main content in 3-4 sections with H2 headings (use keyword variants in headings)
5. At least ONE comparison table (HTML <table>) with real numbers from named institutions
6. FAQ section: EXACTLY 3 questions as H3 with "?" - answer in the next <p>. Use these as guidance:
{faq_hint_text}
   FAQ RULES:
   - Questions MUST be relevant to the article topic
   - Include the main keyword or a close variation in at least 2 questions
   - Focus on real user concerns: approval chances, requirements, speed, safety
   - Each question must address a different concern (do NOT repeat similar questions)
7. STRONG CTA section with this exact HTML:
   <div style="background:linear-gradient(135deg,#2563eb,#1e40af);color:#fff;padding:24px;border-radius:12px;margin:24px 0;text-align:center;">
     <h3 style="color:#fff;margin:0 0 12px;">Before You Apply — Check Your Credit Score for FREE</h3>
     <p style="margin:0 0 16px;">Don't get rejected. Know your CIC credit score first with Credit Kaagapay — 100% free, no hidden fees.</p>
     <a href="https://play.google.com/store/apps/details?id=com.credit.kaagapay.ph" style="background:#fff;color:#2563eb;padding:12px 32px;border-radius:8px;text-decoration:none;font-weight:700;display:inline-block;">Check My Credit Score Now</a>
   </div>
8. SEC compliance disclaimer (see E-E-A-T section above)

PARAGRAPH RULES:
- Max 2-3 sentences per paragraph
- Every paragraph must contain either: a number, a bank name, a peso amount, or an action step
- If a paragraph is just "filler commentary" with no concrete info, delete it

FORMATTING:
- <h2> for main sections, <h3> for subsections and FAQ questions
- <table> with <thead>/<tbody> for comparisons (include ₱ amounts)
- <blockquote> for pro tips (max 2 per article)
- <strong> sparingly (max 2 per section)
- Key Takeaways: <div style="background:#f0f7ff;border-left:4px solid #2563eb;padding:20px;margin:20px 0;border-radius:8px;"><p style="margin:0 0 8px;font-size:0.85em;color:#6b7280;">Updated {current_date}</p><h3 style="margin:0 0 12px;">Key Takeaways</h3>...bullet points...</div>
- Internal links: use <a href="URL">anchor text</a> directly

LENGTH: 1500-1800 words. Every word must earn its place.

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
            "temperature": 0.7,
            "maxOutputTokens": 12000,
        },
    }

      # Model fallback: try each model in order until one works
    GEMINI_MODELS = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
    ]
    resp = None
    for model in GEMINI_MODELS:
        model_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        print(f"  Trying model: {model}")
        for attempt in range(3):
            resp = requests.post(model_url, json=payload, timeout=120)
            if resp.status_code == 200:
                print(f"  ✓ Success with {model}")
                break
            elif resp.status_code == 429:
                wait = 30 * (attempt + 1)
                print(f"  Rate limited on {model}, waiting {wait}s (attempt {attempt + 1}/3)...")
                time.sleep(wait)
            elif resp.status_code in (503, 500, 404):
                print(f"  {model} unavailable ({resp.status_code}): {resp.text[:200]}")
                break  # Try next model immediately
            else:
                print(f"  Gemini API error {resp.status_code}: {resp.text[:300]}")
                if attempt == 2:
                    break
                time.sleep(10)
        if resp and resp.status_code == 200:
            break
    if not resp or resp.status_code != 200:
        print(f"  All Gemini models failed. Last error: {resp.status_code if resp else 'no response'}")
        sys.exit(1)

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


def validate_article(article, topic):
    """Validate article quality before publishing. Returns (ok, issues)."""
    issues = []
    content = article.get("content", "")
    title = article.get("title", "")
    keyword = topic.get("keyword", "")

    plain_text = re.sub(r"<[^>]+>", " ", content)
    plain_text = re.sub(r"\s+", " ", plain_text).strip()
    word_count = len(plain_text.split())

    if word_count < 800:
        issues.append(f"Too thin: {word_count} words (minimum 800)")
    if len(title) > 70:
        issues.append(f"Title too long: {len(title)} chars (max 70)")
    if len(title) < 20:
        issues.append(f"Title too short: {len(title)} chars (min 20)")

    digit_ratio = sum(c.isdigit() for c in title) / max(len(title), 1)
    if digit_ratio > 0.3:
        issues.append(f"Title has too many digits ({digit_ratio:.0%})")

    if keyword.lower() not in plain_text.lower():
        issues.append(f"Focus keyword '{keyword}' not found in article body")

    h2_count = len(re.findall(r"<h2", content, re.IGNORECASE))
    if h2_count < 2:
        issues.append(f"Only {h2_count} H2 headings (minimum 2)")

    meta_desc = article.get("meta_description", "")
    if len(meta_desc) > 160:
        issues.append(f"Meta description too long: {len(meta_desc)} chars")
    if len(meta_desc) < 50:
        issues.append(f"Meta description too short: {len(meta_desc)} chars")

    ph_terms = ["philippines", "filipino", "peso", "₱", "bsp", "cic", "sec.gov.ph",
                 "bpi", "bdo", "metrobank", "gcash", "maya", "sss", "pag-ibig"]
    has_ph_context = any(term in plain_text.lower() for term in ph_terms)
    if not has_ph_context:
        issues.append("No Philippines-specific context found in article")

    ok = len(issues) == 0
    return ok, issues


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

    # Validate article quality before publishing
    ok, issues = validate_article(article, topic)
    if not ok:
        print("Article quality check FAILED:")
        for issue in issues:
            print(f"  ✗ {issue}")
        print("Publishing anyway with warnings...")
    else:
        print("Article quality check passed ✓")

    print("Publishing to WordPress...")
    post_id, post_url = publish_post(article, topic, featured_image_id=featured_id)
    print()
    print(f"Done! Article published at {post_url}")


if __name__ == "__main__":
    main()
