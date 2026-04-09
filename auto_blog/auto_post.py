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
# Keyword Matrix System
# (10 core) × (15 modifiers) × (10 audience) × (8 geo) = 12,000+ combos
# ---------------------------------------------------------------------------
CORE_WORDS = [
    "loan", "cash loan", "online loan", "quick loan", "fast loan",
    "personal loan", "credit loan", "money loan", "salary loan", "emergency loan",
    "CIC credit report", "loan calculator", "online loan app", "bad credit loan",
]

MODIFIERS = [
    "fast", "instant", "quick approval", "same day", "24 hours",
    "low interest", "legit", "safe", "best", "top",
    "easy approval", "no rejection", "guaranteed",
]

AUDIENCE_WORDS = [
    "no payslip", "unemployed", "with bad credit", "no credit history",
    "self employed", "OFW", "student", "first time borrower", "low income",
]

GEO_WORDS = [
    "philippines", "manila", "makati", "cebu",
    "davao", "quezon city", "pasig", "taguig",
]

# High-value keyword lists (priority selection)
HIGH_TRAFFIC_KEYWORDS = [
    "online loan philippines", "fast loan philippines", "cash loan philippines",
    "personal loan philippines", "loan app philippines", "quick cash loan",
    "instant loan approval", "emergency loan philippines",
    "CIC credit report philippines", "loan calculator philippines",
    "best online loan app philippines", "bad credit loan philippines",
]

HIGH_CONVERSION_KEYWORDS = [
    "loan no payslip philippines", "loan for unemployed philippines",
    "loan with bad credit philippines", "instant cash loan same day",
    "loan easy approval no documents", "guaranteed loan approval philippines",
    "loan for OFW philippines", "loan for students philippines",
]

GEO_KEYWORDS = [
    "cash loan manila", "personal loan cebu", "loan app makati",
    "fast loan davao", "emergency loan quezon city",
    "online loan pasig", "salary loan taguig",
]

APP_COMPETITOR_KEYWORDS = [
    "best loan app 2026 philippines", "legit loan app no rejection",
    "loan app low interest rate", "loan app instant approval philippines",
    "tala vs cashalo vs tonik 2026",
]

COMPARISON_KEYWORDS = [
    "SSS loan vs Pag-IBIG loan", "bank loan vs online loan philippines",
    "credit card vs personal loan philippines",
    "GCash GLoan vs Maya Credit 2026",
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
    "CIC credit report": (
        "CIC (Credit Information Corporation) collects data from all BSP-supervised banks and lenders. "
        "CIC score range: 300-850. Score >700 = good credit. Free report via creditinfo.gov.ph. "
        "Report includes: payment history (35%), credit utilization (30%), credit age (15%), new inquiries (10%), mix (10%). "
        "Dispute errors for free at CIC — takes 30 days. Negative records removed after 5 years. "
        "BPI, BDO, Metrobank, CIMB, Tonik all report to CIC monthly."
    ),
    "loan calculator": (
        "Add-on rate vs diminishing balance: 1.5%/mo add-on = ~32.4% EIR; 1.5%/mo diminishing = ~18% EIR. "
        "BPI personal loan: ₱50k at 1.2%/mo for 12 months = ₱4,633/mo total payment. "
        "CIMB: ₱50k at 1.19%/mo for 24 months = ₱2,595/mo. "
        "SSS salary loan: ₱20k at 10%/yr for 24 months = ₱920/mo. "
        "Rule of thumb: monthly payment should not exceed 30% of net monthly income."
    ),
    "online loan app": (
        "SEC-registered apps (2026): Tonik, Maya, CIMB, Tala, Cashalo, Lendly, UnionDigital. "
        "Tonik Quick Loan: ₱5k-₱50k, 1.59%/mo, 1-hour approval. "
        "Maya Credit: ₱2k-₱30k, 3.5% flat fee, 30-min approval. "
        "GCash GLoan: ₱5k-₱25k, 3.99-5.99%/mo, 5-min approval. "
        "Red flags: no SEC registration, requests contacts/gallery access, charges >6%/month (BSP limit). "
        "SEC blocked 200+ illegal lending apps in 2025."
    ),
    "bad credit loan": (
        "CIC score below 580 = poor credit. Lenders that accept low scores: Tonik, Tala, Cashalo, RFC. "
        "Tala: accepts first-time borrowers with no credit history, ₱1k-₱15k. "
        "RFC (Radiowealth Finance): accepts low CIC scores, ₱5k-₱500k, requires collateral for large amounts. "
        "Rebuilding tips: pay on time for 6 months (+40-60 points), reduce utilization below 30% (+20-40 points). "
        "Secured credit card (BPI, Metrobank): requires ₱5k-₱10k deposit, builds credit in 6-12 months."
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
    "CIC credit report": "credit report document financial review",
    "loan calculator": "calculator finance budget planning",
    "online loan app": "smartphone mobile app loan application",
    "bad credit loan": "credit score low financial help",
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
    "CIC credit report": "Credit Education",
    "loan calculator": "Financial Planning",
    "online loan app": "Loans",
    "bad credit loan": "Loans",
}


def generate_topic(existing_titles):
    """Generate a topic from the keyword matrix, prioritizing high-value keywords."""

    # Priority tiers: try high-value keywords first, then matrix combos
    priority_pools = [
        HIGH_TRAFFIC_KEYWORDS,
        HIGH_CONVERSION_KEYWORDS,
        CREDIT_KEYWORDS,
        COMPARISON_KEYWORDS,
        APP_COMPETITOR_KEYWORDS,
        GEO_KEYWORDS,
    ]

    # 60% chance to pick from priority pools, 40% from matrix generator
    use_priority = random.random() < 0.6

    if use_priority:
        # Flatten priority pools, shuffle, find unused keyword
        all_priority = []
        for pool in priority_pools:
            all_priority.extend(pool)
        random.shuffle(all_priority)

        for kw in all_priority:
            kw_lower = kw.lower()
            if not any(kw_lower in title for title in existing_titles):
                return _build_topic_from_keyword(kw)

    # Matrix combination: modifier + core + audience + geo
    attempts = 0
    while attempts < 50:
        core = random.choice(CORE_WORDS)
        modifier = random.choice(MODIFIERS)
        audience = random.choice(AUDIENCE_WORDS)
        geo = random.choice(GEO_WORDS)

        # Combine: "fast personal loan for OFW philippines"
        keyword = f"{modifier} {core} {audience} {geo}"

        kw_lower = keyword.lower()
        if not any(kw_lower in title for title in existing_titles):
            return _build_topic_from_keyword(keyword, core=core, audience=audience, geo=geo)

        attempts += 1

    # Fallback: random matrix combo regardless of duplicates
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
    """Pick a topic from the keyword matrix, avoiding recent duplicates."""
    return generate_topic(existing_titles)


# ---------------------------------------------------------------------------
# News-Jacking SEO: Fetch PH news → score loan relevance → generate news article
# ---------------------------------------------------------------------------

# Philippine news RSS feeds (financial, business, lifestyle)
NEWS_RSS_FEEDS = [
    "https://business.inquirer.net/feed",
    "https://www.philstar.com/rss/business",
    "https://www.bworldonline.com/feed",
    "https://mb.com.ph/category/business/feed",
    "https://news.abs-cbn.com/rss/business",
    "https://www.rappler.com/money/feed",
]


def fetch_ph_news(max_items=30):
    """Fetch recent news from Philippine RSS feeds. Returns list of {title, summary, url, source}."""
    import xml.etree.ElementTree as ET
    from email.utils import parsedate_to_datetime

    items = []
    cutoff_hours = 48  # grab news from last 48 hours
    now = datetime.now(timezone.utc)

    for feed_url in NEWS_RSS_FEEDS:
        source = feed_url.split("/")[2].replace("www.", "").replace("business.", "")
        try:
            resp = requests.get(feed_url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200:
                continue
            root = ET.fromstring(resp.content)
            channel = root.find("channel")
            if channel is None:
                continue
            for item in channel.findall("item")[:10]:
                title_el = item.find("title")
                desc_el = item.find("description")
                link_el = item.find("link")
                pubdate_el = item.find("pubDate")
                if title_el is None:
                    continue
                title = title_el.text or ""
                summary = re.sub(r"<[^>]+>", "", (desc_el.text or "") if desc_el is not None else "")[:300]
                url = link_el.text or "" if link_el is not None else ""
                # Check recency
                try:
                    pub_dt = parsedate_to_datetime(pubdate_el.text) if pubdate_el is not None else None
                    if pub_dt and (now - pub_dt).total_seconds() > cutoff_hours * 3600:
                        continue
                except Exception:
                    pass
                items.append({"title": title, "summary": summary, "url": url, "source": source})
                if len(items) >= max_items:
                    break
        except Exception as e:
            print(f"  RSS fetch failed ({source}): {e}")
        if len(items) >= max_items:
            break

    print(f"  Fetched {len(items)} news items from {len(NEWS_RSS_FEEDS)} feeds")
    return items


def score_news_for_loan_angle(news_items):
    """Use Gemini to score each news item for loan/credit relevance. Returns best item or None."""
    if not news_items:
        return None

    news_list = "\n".join(
        f"{i+1}. [{item['source']}] {item['title']} — {item['summary'][:150]}"
        for i, item in enumerate(news_items[:20])
    )

    prompt = f"""You are an SEO strategist for a Philippine personal finance website (Credit Kaagapay).
Review these recent Philippine news headlines and score each one (0-10) on how naturally it can be connected to a loan, credit score, or personal finance article.

Scoring guide:
- 9-10: Directly about loans, interest rates, BSP policy, SEC enforcement, digital lending, credit scores
- 7-8: About economic hardship, job loss, inflation, OFW remittances, tuition, medical bills — easy to bridge to loans
- 5-6: Business news, property, elections — possible but forced connection
- 0-4: Sports, entertainment, crime, weather — very hard to connect naturally

NEWS ITEMS:
{news_list}

Return ONLY valid JSON (no markdown):
{{"best_index": <1-based index of highest scoring item, or 0 if none score >=7>,
  "score": <score of best item>,
  "loan_angle": "<one sentence: how to bridge this news to a loan/credit topic>",
  "target_keyword": "<the most relevant loan keyword from this list: online loan philippines, personal loan philippines, emergency loan philippines, bad credit loan philippines, CIC credit report philippines, loan for unemployed philippines, cash loan philippines>"}}"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 500},
    }

    GEMINI_MODELS = ["gemini-2.0-flash", "gemini-1.5-flash"]
    for model in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        try:
            resp = requests.post(url, json=payload, timeout=30)
            if resp.status_code == 200:
                text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                text = re.sub(r"^```(?:json)?\n?", "", text)
                text = re.sub(r"\n?```$", "", text)
                result = json.loads(text)
                idx = result.get("best_index", 0)
                score = result.get("score", 0)
                if idx > 0 and score >= 7 and idx <= len(news_items):
                    chosen = news_items[idx - 1]
                    chosen["loan_angle"] = result.get("loan_angle", "")
                    chosen["target_keyword"] = result.get("target_keyword", "online loan philippines")
                    print(f"  Best news item (score {score}/10): {chosen['title'][:80]}")
                    print(f"  Loan angle: {chosen['loan_angle']}")
                    return chosen
                else:
                    print(f"  No news item scored >=7 (best score: {score})")
                    return None
        except Exception as e:
            print(f"  News scoring failed ({model}): {e}")
    return None


def build_news_topic(news_item):
    """Build a topic dict from a news item for news-jacking article generation."""
    keyword = news_item.get("target_keyword", "online loan philippines")
    core = "loan"
    for cw in sorted(CORE_WORDS, key=len, reverse=True):
        if cw.lower() in keyword.lower():
            core = cw
            break
    data_points = CATEGORY_DATA_POINTS.get(core, CATEGORY_DATA_POINTS["loan"])
    img_query = IMG_QUERIES.get(core, "loan finance philippines")
    category = CORE_CATEGORIES.get(core, "Loans")
    return {
        "keyword": keyword,
        "angle": news_item.get("loan_angle", "practical guide with real bank rates"),
        "category": category,
        "img_query": img_query,
        "data_points": data_points,
        "news_title": news_item["title"],
        "news_summary": news_item["summary"],
        "news_url": news_item["url"],
        "news_source": news_item["source"],
        "is_news_jacking": True,
    }


def pick_topic_with_news(existing_titles):
    """30% chance: use news-jacking strategy. 70%: use keyword matrix."""
    use_news = random.random() < 0.30
    if use_news:
        print("[Strategy] Trying News-Jacking SEO (30% chance triggered)...")
        news_items = fetch_ph_news()
        if news_items:
            best_news = score_news_for_loan_angle(news_items)
            if best_news:
                topic = build_news_topic(best_news)
                print(f"[Strategy] ✓ News-jacking topic selected: {topic['keyword']}")
                return topic
        print("[Strategy] No suitable news found, falling back to keyword matrix")
    else:
        print("[Strategy] Using keyword matrix strategy (70% default)")
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

    # Build news context block if this is a news-jacking article
    news_context = ""
    if topic.get("is_news_jacking"):
        news_context = f"""
NEWS HOOK (use this real news event as your opening hook — summarize it in 1-2 sentences, then bridge to the loan topic):
Headline: {topic.get('news_title', '')}
Summary: {topic.get('news_summary', '')}
Source: {topic.get('news_source', '')} ({topic.get('news_url', '')})
Bridge angle: {topic.get('angle', '')}

IMPORTANT: Start the article by referencing this real news event. Cite the source inline (e.g., "According to {topic.get('news_source', 'local reports')}..."). Then naturally transition to the loan/credit topic."""

    prompt = f"""You are a Filipino personal finance blogger writing for Credit Kaagapay (a free credit score & loan finder app). Write like a real person, not an AI.

TOPIC: {topic['keyword']}
ANGLE: {topic['angle']}
CATEGORY: {topic['category']}
DATE: {current_date}{news_context}

REAL DATA TO USE (weave these into the article naturally):
{data_points}

EXISTING ARTICLES FOR INTERNAL LINKS (link to 2-3 of these where relevant):
{internal_links}
{img_instructions}

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
6. FAQ section: 3 questions as H3 with "?" - answer in the next <p>
7. STRONG CTA section with this exact HTML:
   <div style="background:linear-gradient(135deg,#2563eb,#1e40af);color:#fff;padding:24px;border-radius:12px;margin:24px 0;text-align:center;">
     <h3 style="color:#fff;margin:0 0 12px;">Before You Apply — Check Your Credit Score for FREE</h3>
     <p style="margin:0 0 16px;">Don't get rejected. Know your CIC credit score first with Credit Kaagapay — 100% free, no hidden fees.</p>
     <a href="https://www.creditkaagapay.com/" style="background:#fff;color:#2563eb;padding:12px 32px;border-radius:8px;text-decoration:none;font-weight:700;display:inline-block;">Check My Credit Score Now</a>
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
            "temperature": 0.9,
            "maxOutputTokens": 12000,
        },
    }

      # Model fallback: try each model in order until one works
    GEMINI_MODELS = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
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

    # Generate and append Article schema
    featured_url = image_data[0]["url"] if image_data else None
    article_schema = generate_article_schema(
        title=article.get("title", ""),
        excerpt=article.get("excerpt", ""),
        keyword=topic["keyword"],
        image_url=featured_url,
    )
    content += article_schema
    print("  Article Schema generated")

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

    # Pick topic (30% news-jacking, 70% keyword matrix)
    topic = pick_topic_with_news(existing)
    print(f"Selected topic: {topic['keyword']}")
    if topic.get("is_news_jacking"):
        print(f"[News-Jacking] Based on: {topic.get('news_title', 'N/A')[:80]}")
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
