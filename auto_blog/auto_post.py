#!/usr/bin/env python3
"""
Credit Kaagapay - Auto Blog Poster  (v2.1 — Rule-Optimised)
Uses Google Gemini (with multi-model fallback) to generate SEO blog articles
with Pexels images, then publishes to WordPress.

Rule version : v2.1
Goal         : Generate SEO articles for a Philippines loan website focused on
               ranking, capturing search intent, and driving conversions.

Model Priority (按长文处理和写作能力排序):
1. Gemini 2.5 Flash Lite (最优先 - 最好的长文处理和写作能力)
2. Gemini 3.1 Flash Lite (次优先 - 次好的能力)
3. Gemini 3 Flash (备选 - 基础能力)
4. Groq Llama 3.3 70B (最后备选 - 如果 Gemini 都没额度)
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
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")

PEXELS_API = "https://api.pexels.com/v1"

# Author info (E-E-A-T)
AUTHOR_NAME = "Zia Tan"
AUTHOR_ROLE = "Philippines Fintech Industry Analyst at Credit Kaagapay"

# ---------------------------------------------------------------------------
# Existing articles for internal linking  (v2.1 §7 — 5 required links)
# ---------------------------------------------------------------------------
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

# Internal link types required by v2.1 §7
INTERNAL_LINK_TYPES = [
    "loan_amount_page",
    "loan_type_page",
    "comparison_page",
    "related_article",
    "homepage",
]

# ---------------------------------------------------------------------------
# v2.1 §1 — KEYWORD SELECTION
# Distribution: core 60%, scenario 30%, random mix 10%
# ---------------------------------------------------------------------------
KEYWORD_DISTRIBUTION = {
    "core_keywords": 0.6,
    "scenario_keywords": 0.3,
    "random_mix": 0.1,
}

# Core keywords (product-focused, high-intent)
CORE_KEYWORDS = [
    "online loan philippines", "personal loan philippines", "cash loan philippines",
    "CIC credit report philippines", "bad credit loan philippines", "emergency loan philippines",
    "fast loan philippines", "quick loan philippines", "salary loan philippines",
    "OFW loan philippines", "loan calculator PH", "loan for unemployed philippines",
]

# v2.1 §1 — Scenario keywords (real-life user problems)
SCENARIO_KEYWORDS = [
    "pay bills installment philippines",
    "buy load using credit philippines",
    "gcash loan without payslip",
    "maya credit rejected what to do",
    "emergency cash today philippines",
    "meralco bill installment loan",
    "globe load pay later philippines",
]

# v2.1 §1 — Keyword selection rules
# - title must be a specific question
# - must include a real-life scenario
# - avoid broad keywords (e.g. "online loan philippines")
# - prefer: how / can / where / best

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
# Title Pattern System — v2.1 §1: title must be a specific question,
# prefer how / can / where / best
# ---------------------------------------------------------------------------
TITLE_PATTERNS = [
    "how to get a loan without {constraint} in philippines",
    "can you get a {situation} loan as a {audience} in philippines",
    "where to find {situation} cash loan for {audience} philippines",
    "best loan apps for {situation} in philippines",
    "{amount} peso loan without {constraint}: options for filipinos",
    "how to apply for a loan as a {audience} in the philippines",
    "where to get {situation} loan without {constraint} philippines",
    "how can {audience} get approved for a loan in philippines",
]

TITLE_CONSTRAINTS = ["no payslip", "no valid id", "no credit check"]
TITLE_AUDIENCES = ["unemployed", "student", "first time borrower", "OFW", "self employed"]
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

# v2.1 §4 — Optional Filipino words for conversational tone
OPTIONAL_FILIPINO_WORDS = ["kumusta", "pera", "sweldo"]

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
    "low income": "micro-loans and cooperative options for those earning below ₱15k/month",
}

# Image queries by core word
IMG_QUERIES = {
    "loan": "loan application documents office",
    "cash loan": "cash money peso bills",
    "online loan": "mobile phone lending app",
    "quick loan": "fast transaction speed clock",
    "fast loan": "fast transaction speed clock",
    "personal loan": "professional office meeting",
    "credit loan": "credit card financial planning",
    "money loan": "money finance savings",
    "salary loan": "salary payment office",
    "emergency loan": "emergency help support",
    "credit": "credit score financial",
    "comparison": "comparison chart analysis",
}

CORE_CATEGORIES = {
    "loan": "Loans",
    "cash loan": "Loans",
    "online loan": "Loans",
    "quick loan": "Loans",
    "fast loan": "Loans",
    "personal loan": "Loans",
    "credit loan": "Credit",
    "money loan": "Loans",
    "salary loan": "Loans",
    "emergency loan": "Loans",
    "credit": "Credit",
    "comparison": "Guides",
}


# ---------------------------------------------------------------------------
# v2.1 §1 — Keyword Selection Logic
# ---------------------------------------------------------------------------
def select_keyword():
    """Select a keyword based on v2.1 distribution: 60% core, 30% scenario, 10% random mix."""
    roll = random.random()

    if roll < KEYWORD_DISTRIBUTION["core_keywords"]:
        # 60% — core keywords
        keyword = random.choice(CORE_KEYWORDS)
        source = "core"
    elif roll < KEYWORD_DISTRIBUTION["core_keywords"] + KEYWORD_DISTRIBUTION["scenario_keywords"]:
        # 30% — scenario keywords
        keyword = random.choice(SCENARIO_KEYWORDS)
        source = "scenario"
    else:
        # 10% — random mix (combine core + modifier + audience + geo)
        parts = [random.choice(CORE_WORDS)]
        if random.random() < 0.6:
            parts.insert(0, random.choice(MODIFIERS))
        if random.random() < 0.5:
            parts.append(random.choice(AUDIENCE_WORDS))
        parts.append(random.choice(GEO_WORDS))
        keyword = " ".join(parts)
        source = "random_mix"

    print(f"  Keyword source: {source} → \"{keyword}\"")
    return keyword


def build_topic_from_keyword(keyword):
    """Build a topic dict from a selected keyword."""
    # Determine core word for data points and category
    matched_core = "loan"
    for core in CORE_WORDS:
        if core in keyword.lower():
            matched_core = core
            break

    # Determine audience angle
    matched_audience = None
    for aud, angle in AUDIENCE_ANGLES.items():
        if aud in keyword.lower():
            matched_audience = aud
            break

    angle = AUDIENCE_ANGLES.get(matched_audience, "general loan guide for Filipino borrowers")

    return {
        "keyword": keyword,
        "angle": angle,
        "category": CORE_CATEGORIES.get(matched_core, "Loans"),
        "img_query": IMG_QUERIES.get(matched_core, "loan application philippines"),
        "data_points": CATEGORY_DATA_POINTS.get(matched_core, CATEGORY_DATA_POINTS["loan"]),
        "is_news": False,
    }


# ---------------------------------------------------------------------------
# Gemini Multi-Model Support with Fallback
# ---------------------------------------------------------------------------
def call_gemini_api(prompt, max_tokens=12000, temperature=0.7):
    """
    调用 Gemini API，按优先级自动故障转移。

    模型优先级（按长文处理和写作能力排序）：
    1. gemini-2.5-flash-lite (最优先)
    2. gemini-3.1-flash-lite (次优先)
    3. gemini-3-flash (备选)
    4. Groq Llama 3.3 70B (最后备选)
    """

    gemini_models = [
        "gemini-2.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3-flash",
    ]

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }

    for model in gemini_models:
        if not GEMINI_API_KEY:
            print(f"  ⚠️  GEMINI_API_KEY 未配置，跳过 {model}")
            continue

        model_url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={GEMINI_API_KEY}"
        )

        for attempt in range(3):
            try:
                print(f"  尝试模型: {model} (尝试 {attempt + 1}/3)")
                resp = requests.post(model_url, json=payload, timeout=120)

                if resp.status_code == 200:
                    print(f"  ✅ {model} 成功")
                    return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

                elif resp.status_code == 429:
                    wait = 30 * (attempt + 1)
                    print(f"  ⚠️  {model} 配额已用尽，等待 {wait}s 后尝试下一个模型...")
                    time.sleep(wait)
                    break

                elif resp.status_code in (503, 500):
                    wait = 30 * (attempt + 1)
                    print(f"  ⚠️  {model} 不可用 ({resp.status_code})，等待 {wait}s...")
                    time.sleep(wait)

                elif resp.status_code == 404:
                    print(f"  ⚠️  {model} 不存在 (404)，跳到下一个模型")
                    break

                else:
                    print(f"  ❌ Gemini API 错误 {resp.status_code}: {resp.text[:200]}")
                    if attempt < 2:
                        time.sleep(30)

            except requests.RequestException as e:
                print(f"  ❌ 请求失败: {e}")
                if attempt < 2:
                    time.sleep(30)

    print("\n  ⚠️  所有 Gemini 模型都失败，尝试 Groq Llama 3.3 70B 作为最后备选...")
    return call_groq_api(prompt, max_tokens, temperature)


def call_groq_api(prompt, max_tokens=12000, temperature=0.7):
    """调用 Groq API 作为最后备选。"""
    if not GROQ_API_KEY:
        print("  ❌ GROQ_API_KEY 未配置")
        return None

    model_url = "https://api.groq.com/openai/v1/chat/completions"

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    for attempt in range(3):
        try:
            print(f"  尝试 Groq Llama 3.3 70B (尝试 {attempt + 1}/3)")
            resp = requests.post(model_url, json=payload, headers=headers, timeout=120)

            if resp.status_code == 200:
                print("  ✅ Groq 成功")
                return resp.json()["choices"][0]["message"]["content"].strip()

            elif resp.status_code == 429:
                wait = 30 * (attempt + 1)
                print(f"  ⚠️  Groq 配额已用尽，等待 {wait}s...")
                time.sleep(wait)

            else:
                print(f"  ❌ Groq API 错误 {resp.status_code}: {resp.text[:200]}")
                if attempt < 2:
                    time.sleep(30)

        except requests.RequestException as e:
            print(f"  ❌ 请求失败: {e}")
            if attempt < 2:
                time.sleep(30)

    print("  ❌ Groq 也失败了，无法生成文章")
    return None


# ---------------------------------------------------------------------------
# v2.1 §2 — QUERY EXPANSION (MANDATORY)
# Generate 10 real user search questions BEFORE writing the article.
# All questions become H2 headings.
# ---------------------------------------------------------------------------
def generate_query_expansion(keyword):
    """Generate 10 real user search questions for the keyword (v2.1 §2)."""
    prompt = f"""You are a Philippine personal finance SEO expert.

For the keyword: "{keyword}"

Generate exactly 10 real user search questions that Filipinos would type into Google.

Requirements:
- Must be real user search queries (natural language, not keyword-stuffed)
- Must include intent: approval chances, speed, requirements, safety, amounts
- Must include Philippines context (mention GCash, Maya, SSS, Pag-IBIG, BSP, SEC, peso amounts, etc.)
- Questions should cover different user intents (informational, transactional, navigational)
- Use question words: how, can, where, best, what, is it safe, how much, how fast

Return ONLY a valid JSON array of 10 question strings, no markdown fences:
["question 1", "question 2", ...]"""

    text = call_gemini_api(prompt, max_tokens=2000, temperature=0.5)
    if not text:
        return []

    try:
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
        questions = json.loads(text)
        if isinstance(questions, list) and len(questions) >= 5:
            return questions[:10]
    except (json.JSONDecodeError, ValueError) as e:
        print(f"  Query expansion JSON parse failed: {e}")

    return []


# ---------------------------------------------------------------------------
# News Scanning (Gemini-powered) — v2.1 §9
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

Think of the most recent (last 24 hours) news events in the Philippines related to:
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

Return 3-5 news items. If you cannot find any news from the last 24 hours, return an empty array: []"""

    text = call_gemini_api(prompt, max_tokens=2000, temperature=0.3)
    if not text:
        return []

    try:
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\n?", "", text)
            text = re.sub(r"\n?```$", "", text)

        news_items = json.loads(text)
        if isinstance(news_items, list):
            valid = []
            for item in news_items:
                if all(k in item for k in ("headline", "summary", "score", "event")):
                    item["score"] = max(1, min(10, int(item["score"])))
                    valid.append(item)
            return valid
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"  News scan JSON parse failed: {e}")

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
        "news_score": news_item["score"],
    }


# ---------------------------------------------------------------------------
# WordPress helpers
# ---------------------------------------------------------------------------
def search_pexels_images(query, count=3):
    """Search Pexels for images matching the query."""
    if not PEXELS_API_KEY:
        print("  Warning: PEXELS_API_KEY not set, skipping image search")
        return []

    try:
        resp = requests.get(
            f"{PEXELS_API}/search",
            params={"query": query, "per_page": count, "page": 1},
            headers={"Authorization": PEXELS_API_KEY},
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json().get("photos", [])
    except Exception as e:
        print(f"  Pexels search failed: {e}")
    return []


def download_and_strip_image(photo_url):
    """Download image and strip EXIF data."""
    try:
        resp = requests.get(photo_url, timeout=30)
        if resp.status_code != 200:
            return None, None

        img_bytes = resp.content
        content_type = resp.headers.get("Content-Type", "image/jpeg")

        try:
            from PIL import Image

            img = Image.open(io.BytesIO(img_bytes))
            clean = Image.new(img.mode, img.size)
            clean.putdata(list(img.getdata()))
            buf = io.BytesIO()
            fmt = "JPEG" if "jpeg" in content_type or "jpg" in content_type else "PNG"
            clean.save(buf, format=fmt, quality=85, optimize=True)
            return buf.getvalue(), content_type
        except ImportError:
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
        photo_url = photo.get("src", {}).get("large", photo.get("src", {}).get("original", ""))
        photographer = photo.get("photographer", "Pexels")
        alt_text = f"{keyword} in the Philippines - Photo by {photographer} on Pexels"

        print(f"  Downloading image {i + 1}/{len(photos)} from Pexels...")
        img_bytes, content_type = download_and_strip_image(photo_url)
        if not img_bytes:
            continue

        slug = re.sub(r"[^a-z0-9]+", "-", keyword.lower()).strip("-")
        ext = "jpg" if "jpeg" in (content_type or "") else "png"
        filename = f"{slug}-{i + 1}.{ext}"

        print(f"  Uploading {filename} to WordPress...")
        media_id, media_url = upload_to_wordpress(img_bytes, filename, alt_text, content_type)
        if media_id:
            results.append({"id": media_id, "url": media_url, "alt": alt_text, "photographer": photographer})
            print(f"  ✅ Uploaded: {media_url}")

    return results


# ---------------------------------------------------------------------------
# Article generation — v2.1 compliant prompt & post-processing
# ---------------------------------------------------------------------------
def build_internal_links_ref(current_keyword):
    """Build internal links string for prompt, excluding current topic.
    v2.1 §7 requires 5 internal links of different types."""
    links = []
    for topic, path in EXISTING_ARTICLES.items():
        if current_keyword.lower() not in topic.lower():
            links.append(f'  - "{topic}": {WP_SITE}{path}')
    return "\n".join(links[:8])  # Provide 8 options so the model can pick 5


def replace_internal_link_placeholders(html):
    """Replace [Internal Link: description] placeholders with real <a> tags."""
    def replacer(match):
        topic_hint = match.group(1).strip().lower()
        for topic, path in EXISTING_ARTICLES.items():
            if topic_hint in topic.lower() or topic.lower() in topic_hint:
                url = f"{WP_SITE}{path}"
                return f'<a href="{url}">{match.group(1).strip()}</a>'
        return match.group(1).strip()

    # Support both formats: [Internal Link: ...] and [INTERNAL_LINK: ...]
    html = re.sub(r"\[Internal Link:\s*([^\]]+)\]", replacer, html, flags=re.IGNORECASE)
    html = re.sub(r"\[INTERNAL_LINK:\s*([^\]]+)\]", replacer, html)
    return html


def generate_faq_schema(article_content):
    """Extract FAQ section from content and generate JSON-LD schema."""
    faq_items = []
    pattern = r"<h3[^>]*>([^<]+\?)</h3>\s*<p>([^<]+(?:<[^/][^>]*>[^<]*</[^>]*>)*[^<]*)</p>"
    matches = re.findall(pattern, article_content, re.DOTALL)
    for question, answer in matches[:8]:
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


def generate_article(topic, image_data=None, expanded_questions=None):
    """Generate a v2.1-compliant blog article using Gemini with multi-model fallback.

    v2.1 required sections:
      title, quick_answer, introduction, h2_sections (8+), comparison_section,
      real_life_scenario, faq (5+), cta_blocks (3), author_and_update, sec_disclaimer

    v2.1 writing style:
      conversational_philippines, 2-3 sentence paragraphs,
      every 2-3 paragraphs include peso_amount / platform_name / actionable_step
    """

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

    # Build internal links reference (v2.1 §7 — 5 required)
    internal_links = build_internal_links_ref(topic["keyword"])

    # Get data points
    data_points = topic.get("data_points", "")

    # Current date for freshness signal
    current_date = datetime.now(timezone.utc).strftime("%B %Y")

    # Build expanded questions section (v2.1 §2)
    expanded_q_section = ""
    if expanded_questions and len(expanded_questions) >= 5:
        q_list = "\n".join(f"  {i+1}. {q}" for i, q in enumerate(expanded_questions))
        expanded_q_section = f"""
=== QUERY EXPANSION (v2.1 §2 — MANDATORY) ===
The following 10 real user search questions were generated for this keyword.
You MUST convert ALL of them into H2 headings in the article:

{q_list}

Each H2 heading should be one of these questions (you may rephrase slightly for readability).
This ensures the article covers all user intents and maximises featured snippet opportunities."""

    # Build title rules based on article type (news vs SEO)
    is_news = topic.get("is_news", False)
    news_score = topic.get("news_score", 0)

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
        title_rules_section = """=== TITLE RULES (SEO — CRITICAL, v2.1 §1) ===

Generate a title that is a SPECIFIC QUESTION. Preferred question words: how / can / where / best.

Patterns:
- "How to Get a Loan Without [constraint] in Philippines?"
- "Can You Get a [situation] Loan as a [audience] in Philippines?"
- "Where to Find [situation] Cash Loan for [audience] Philippines?"
- "Best Loan Apps for [situation] in Philippines"
- "[amount] Peso Loan Without [constraint]: Options for Filipinos"

Parameter pools:
  Constraints: no payslip, no valid id, no credit check
  Audience: unemployed, student, first time borrower, OFW, self employed
  Situations: emergency, instant, same day

Title rules:
- MUST be a specific question (v2.1 §1)
- MUST include a real-life scenario
- Avoid broad keywords (e.g. "online loan philippines") as the full title
- Must be natural and readable
- Keep under 70 characters"""

    # v2.1 §9 — News strategy: determine article type
    news_strategy_note = ""
    if is_news:
        if news_score >= 8:
            news_strategy_note = """
=== NEWS STRATEGY (v2.1 §9 — score >= 8: PRIORITIZE NEWS) ===
This is a HIGH-RELEVANCE news article. Structure:
1. news_summary (what happened)
2. impact_on_borrowers (how this affects Filipino borrowers)
3. loan_solution (what borrowers can do now)
4. cta (apply / check credit score)
RULE: Must connect news to borrowing solutions. Avoid pure news reporting."""
        elif news_score >= 7:
            news_strategy_note = """
=== NEWS STRATEGY (v2.1 §9 — score 7-8: HYBRID) ===
This is a HYBRID article (news + SEO). Balance news reporting with SEO content.
Include news summary but also cover evergreen loan information."""

    # -----------------------------------------------------------------------
    # BUILD THE MAIN PROMPT — v2.1 compliant
    # -----------------------------------------------------------------------
    prompt = f"""You are a Filipino personal finance blogger writing for Credit Kaagapay (a free credit score & loan finder app). Write like a real person, not an AI.

TOPIC: {topic['keyword']}
ANGLE: {topic['angle']}
CATEGORY: {topic['category']}
DATE: {current_date}

REAL DATA TO USE (weave these into the article naturally):
{data_points}

EXISTING ARTICLES FOR INTERNAL LINKS (you MUST link to at least 5 of these — v2.1 §7):
{internal_links}
  - Homepage: {WP_SITE}
Use format: <a href="URL">descriptive anchor text</a>
Link types required: loan_amount_page, loan_type_page, comparison_page, related_article, homepage
{img_instructions}

{title_rules_section}
{expanded_q_section}
{news_strategy_note}

=== ARTICLE STRUCTURE (v2.1 §3 — ALL sections REQUIRED) ===

You MUST include ALL of the following sections in this exact order:

1. **TITLE** — specific question (v2.1 §1)

2. **QUICK ANSWER** (2-3 sentences) — direct answer for Google featured snippet.
   Place this right after the title in a styled box:
   <div style="background:#e8f5e9;border-left:4px solid #4caf50;padding:16px;margin:16px 0;border-radius:8px;">
   <strong>Quick Answer:</strong> [2-3 sentence direct answer]</div>

3. **INTRODUCTION** — must include the keyword AND Philippines context (mention GCash / Meralco / Maya / SSS / Pag-IBIG)

4. **H2 SECTIONS** — minimum 8 H2 headings, ALL must be question-based format.
   {"Use the expanded questions provided above as H2 headings." if expanded_questions else "Generate 8+ question-based H2 headings covering different user intents."}

5. **COMPARISON SECTION** — HTML <table> comparing at least 4 loan options with real numbers (rates, amounts, speed, requirements)

6. **REAL-LIFE SCENARIO** — a specific, relatable story of a Filipino borrower (use a name, situation, peso amounts, platform used, outcome). Make it feel real.
   Wrap in: <div style="background:#fff3e0;border-left:4px solid #ff9800;padding:16px;margin:16px 0;border-radius:8px;">
   <strong>Real Story:</strong> ...</div>

7. **FAQ** — minimum 5 questions as H3 with "?" — answer in the next <p>.
   - Must include the main keyword in at least 2 questions
   - Cover: approval chances, requirements, speed, safety, amounts

8. **CTA BLOCKS** — exactly 3 CTAs (v2.1 §6):
   - CTA 1 (MIDDLE of article — apply_now type):
     <div style="background:linear-gradient(135deg,#2563eb,#1e40af);color:#fff;padding:24px;border-radius:12px;margin:24px 0;text-align:center;">
     <h3 style="color:#fff;margin:0 0 12px;">Ready to Apply? Check Your Approval Odds First</h3>
     <p style="margin:0 0 16px;">Know your CIC credit score before applying — 100% free with Credit Kaagapay.</p>
     <a href="https://play.google.com/store/apps/details?id=com.credit.kaagapay.ph" style="background:#fff;color:#2563eb;padding:12px 32px;border-radius:8px;text-decoration:none;font-weight:700;display:inline-block;">Check My Credit Score Now</a></div>

   - CTA 2 (END of article — compare_loans type):
     <div style="background:linear-gradient(135deg,#059669,#047857);color:#fff;padding:24px;border-radius:12px;margin:24px 0;text-align:center;">
     <h3 style="color:#fff;margin:0 0 12px;">Compare Loan Options Side by Side</h3>
     <p style="margin:0 0 16px;">Find the best rates and fastest approval for your situation.</p>
     <a href="https://play.google.com/store/apps/details?id=com.credit.kaagapay.ph" style="background:#fff;color:#059669;padding:12px 32px;border-radius:8px;text-decoration:none;font-weight:700;display:inline-block;">Compare Loans Now</a></div>

   - CTA 3 (FLEXIBLE placement — check_credit type):
     <div style="background:#f0f7ff;border:2px solid #2563eb;padding:20px;border-radius:12px;margin:20px 0;text-align:center;">
     <p style="margin:0 0 12px;font-weight:600;color:#1e40af;">Not sure if you'll get approved?</p>
     <a href="https://play.google.com/store/apps/details?id=com.credit.kaagapay.ph" style="color:#2563eb;font-weight:700;text-decoration:underline;">Check your free credit score →</a></div>

   RULES: CTAs must be naturally embedded. Must NOT appear only at the end.

9. **AUTHOR & UPDATE** — byline after introduction:
   <p style="color:#6b7280;font-size:0.9em;margin:8px 0 16px;">By {AUTHOR_NAME}, {AUTHOR_ROLE} | Updated {current_date}</p>

10. **SEC DISCLAIMER** — at the very end:
    <p><em>Disclaimer: Always verify loan terms directly with the lender. Check that any lending company is registered with the <a href='https://www.sec.gov.ph'>SEC</a> before applying. Rates and requirements may change — this guide was last updated {current_date}.</em></p>

=== WRITING STYLE (v2.1 §4) ===

TONE: conversational_philippines — write like a knowledgeable friend who works in banking.
Use "you" constantly. Sprinkle in 1-2 Filipino words naturally (kumusta, pera, sweldo).

PARAGRAPH RULES:
- Max 2-3 sentences per paragraph
- Every 2-3 paragraphs MUST include at least one of:
  * A peso amount (₱)
  * A platform name (GCash, Maya, Tala, Tonik, SSS, Pag-IBIG, BPI, etc.)
  * An actionable step (apply at..., check your..., download..., visit...)
- If a paragraph has none of these, DELETE it

GOALS: easy_to_read, fast_answers, action_oriented

BANNED OPENINGS:
- "In the bustling..." / "In today's..." / "In the dynamic..."
- "As we all know..." / "It's no secret that..."
- "Whether you're a..." / "Are you looking for..."
- Any sentence that could describe any country (not specific to Philippines)

GOOD OPENINGS:
- A specific peso amount scenario: "Last month, my friend applied for a ₱50,000 loan at BPI and got rejected."
- A surprising data point: "Only 2% of Filipino adults are financially literate, according to BSP."
- A direct challenge: "You're probably paying way more interest than you need to."
IMPORTANT: The opening paragraph MUST contain the exact keyword "{topic['keyword']}".

=== E-E-A-T (v2.1 §8 — YMYL financial content) ===

- Include 2-3 references per article from: BSP, SSS, Pag-IBIG, banks (BPI, BDO, etc.), SEC
- Do NOT overload every paragraph with references
- Include update date (already in author byline)
- Include SEC disclaimer (already in section 10)

=== SEO BOOST (v2.1 §5) ===

Required checklist:
✅ Quick answer (featured snippet)
✅ 8+ H2 questions
✅ 5+ FAQ
✅ 1 real scenario
✅ 1 comparison section
✅ 3 CTAs (middle, end, flexible)
✅ 5 internal links

KEYWORD DENSITY:
- The EXACT phrase "{topic['keyword']}" MUST appear in the first 100 words
- Use the exact keyword 3-5 times naturally throughout
- Include 3-4 LSI keywords naturally
- Use the keyword or variant in at least 2 H2 headings

FORMATTING:
- <h2> for main sections (question-based), <h3> for FAQ questions
- <table> with <thead>/<tbody> for comparisons
- <blockquote> for pro tips (max 2)
- <strong> sparingly (max 2 per section)
- Key Takeaways box: <div style="background:#f0f7ff;border-left:4px solid #2563eb;padding:20px;margin:20px 0;border-radius:8px;"><p style="margin:0 0 8px;font-size:0.85em;color:#6b7280;">Updated {current_date}</p><h3 style="margin:0 0 12px;">Key Takeaways</h3>...bullet points...</div>

LENGTH: 1800-2200 words. Every word must earn its place.

OUTPUT (valid JSON only, no markdown fences):
{{
    "title": "under 70 chars, specific question, includes keyword",
    "meta_description": "under 155 chars, includes keyword, compelling",
    "excerpt": "2 sentences summarizing the key value",
    "content": "full HTML content with ALL required sections",
    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
    "focus_keyword": "{topic['keyword']}"
}}"""

    # Use multi-model fallback
    text = call_gemini_api(prompt, max_tokens=16000, temperature=0.7)

    if not text:
        print("  ❌ 无法生成文章（所有模型都失败）")
        return None

    # Parse JSON response
    try:
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\n?", "", text)
            text = re.sub(r"\n?```$", "", text)

        article = json.loads(text)

        # Post-process content
        article["content"] = replace_internal_link_placeholders(article["content"])

        # Add FAQ schema
        faq_schema = generate_faq_schema(article["content"])
        if faq_schema:
            article["content"] += faq_schema

        # Add article schema
        article_schema = generate_article_schema(
            article["title"],
            article["excerpt"],
            article["focus_keyword"],
        )
        article["content"] += article_schema

        return article

    except json.JSONDecodeError as e:
        print(f"  ❌ JSON 解析失败: {e}")
        print(f"  响应内容: {text[:500]}")
        return None


# ---------------------------------------------------------------------------
# v2.1 §9 — News Strategy: decide article type based on news score
# ---------------------------------------------------------------------------
def decide_article_type(news_items):
    """Decide whether to write a news, hybrid, or SEO article (v2.1 §9).

    Logic:
    - if score >= 8: prioritize news article
    - if score 7-8: hybrid (news + SEO)
    - if score < 7: fallback to keyword SEO
    """
    if not news_items:
        return "seo", None

    # Sort by score descending
    sorted_news = sorted(news_items, key=lambda x: x["score"], reverse=True)
    top_news = sorted_news[0]

    if top_news["score"] >= 8:
        print(f"  📰 News score {top_news['score']} >= 8 → PRIORITIZE NEWS article")
        return "news", top_news
    elif top_news["score"] >= 7:
        print(f"  📰 News score {top_news['score']} 7-8 → HYBRID article (news + SEO)")
        return "hybrid", top_news
    else:
        print(f"  📰 News score {top_news['score']} < 7 → FALLBACK to keyword SEO")
        return "seo", None


# ---------------------------------------------------------------------------
# Main workflow
# ---------------------------------------------------------------------------
def main():
    """Main workflow: select topic, expand queries, generate article, upload images, publish."""
    print("\n" + "=" * 70)
    print("Credit Kaagapay - Auto Blog Poster (v2.1 Rule-Optimised)")
    print("=" * 70)

    # Check configuration
    if not WP_USERNAME or not WP_APP_PASSWORD:
        print("❌ Error: WP_USERNAME or WP_APP_PASSWORD not set")
        sys.exit(1)

    if not GEMINI_API_KEY and not GROQ_API_KEY:
        print("❌ Error: Neither GEMINI_API_KEY nor GROQ_API_KEY is set")
        sys.exit(1)

    print(f"\n✅ Configuration loaded")
    print(f"  WordPress: {WP_SITE}")
    print(f"  Gemini API: {'✅' if GEMINI_API_KEY else '❌'}")
    print(f"  Groq API: {'✅' if GROQ_API_KEY else '❌'}")
    print(f"  Pexels API: {'✅' if PEXELS_API_KEY else '❌'}")

    # -----------------------------------------------------------------------
    # Step 1: Scan for news (v2.1 §9)
    # -----------------------------------------------------------------------
    print("\n📰 Scanning for trending news...")
    news_items = scan_news()
    if news_items:
        print(f"  Found {len(news_items)} news items:")
        for ni in news_items:
            print(f"    - [{ni['score']}] {ni['headline']}")
    else:
        print("  No relevant news found")

    # -----------------------------------------------------------------------
    # Step 2: Decide article type (v2.1 §9)
    # -----------------------------------------------------------------------
    print("\n🎯 Deciding article type (v2.1 §9 news strategy)...")
    article_type, selected_news = decide_article_type(news_items)

    # -----------------------------------------------------------------------
    # Step 3: Select topic / keyword (v2.1 §1)
    # -----------------------------------------------------------------------
    print(f"\n🎯 Selecting topic (type: {article_type})...")
    topic = None

    if article_type in ("news", "hybrid") and selected_news:
        topic = _build_news_topic(selected_news)
        print(f"  Selected NEWS topic: {topic['keyword']}")
    else:
        # SEO article — use v2.1 keyword selection
        keyword = select_keyword()
        topic = build_topic_from_keyword(keyword)
        print(f"  Selected SEO topic: {topic['keyword']}")

    if not topic:
        print("❌ Failed to select topic")
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Step 4: Query Expansion (v2.1 §2 — MANDATORY)
    # -----------------------------------------------------------------------
    print(f"\n🔍 Generating query expansion (v2.1 §2 — 10 questions)...")
    expanded_questions = generate_query_expansion(topic["keyword"])
    if expanded_questions:
        print(f"  ✅ Generated {len(expanded_questions)} questions:")
        for i, q in enumerate(expanded_questions):
            print(f"    {i+1}. {q}")
    else:
        print("  ⚠️ Query expansion failed, will generate H2s inline")

    # -----------------------------------------------------------------------
    # Step 5: Fetch and upload images
    # -----------------------------------------------------------------------
    print(f"\n🖼️  Fetching images for: {topic['img_query']}")
    image_data = fetch_and_upload_images(topic["img_query"], topic["keyword"], count=3)
    print(f"  Uploaded {len(image_data)} images")

    # -----------------------------------------------------------------------
    # Step 6: Generate article (v2.1 compliant)
    # -----------------------------------------------------------------------
    print(f"\n✍️  Generating v2.1-compliant article...")
    article = generate_article(topic, image_data, expanded_questions)

    if not article:
        print("❌ Failed to generate article")
        sys.exit(1)

    print(f"  ✅ Article generated: {article['title']}")

    # -----------------------------------------------------------------------
    # Step 7: Publish to WordPress
    # -----------------------------------------------------------------------
    print(f"\n📤 Publishing to WordPress...")
    auth = (WP_USERNAME, WP_APP_PASSWORD)

    # Convert tag names to tag IDs
    tag_names = article.get("tags", [])
    tag_ids = []
    for tag_name in tag_names:
        if isinstance(tag_name, int):
            tag_ids.append(tag_name)
            continue
        if not isinstance(tag_name, str) or not tag_name.strip():
            continue
        try:
            search_resp = requests.get(
                f"{WP_API}/tags",
                params={"search": tag_name.strip(), "per_page": 1},
                auth=auth,
                timeout=15,
            )
            if search_resp.status_code == 200 and search_resp.json():
                tag_ids.append(search_resp.json()[0]["id"])
            else:
                create_resp = requests.post(
                    f"{WP_API}/tags",
                    json={"name": tag_name.strip()},
                    auth=auth,
                    timeout=15,
                )
                if create_resp.status_code == 201:
                    tag_ids.append(create_resp.json()["id"])
                else:
                    print(f"  ⚠️ Could not create tag '{tag_name}': {create_resp.status_code}")
        except Exception as e:
            print(f"  ⚠️ Tag lookup/create error for '{tag_name}': {e}")

    print(f"  📌 Resolved {len(tag_ids)} tag IDs from {len(tag_names)} tag names")

    # Set featured image
    featured_media_id = 0
    if image_data and len(image_data) > 0:
        featured_media_id = image_data[0]["id"]
        print(f"  🖼️ Setting featured image: media ID {featured_media_id}")

    post_data = {
        "title": article["title"],
        "content": article["content"],
        "excerpt": article["excerpt"],
        "meta_description": article.get("meta_description", ""),
        "status": "publish",
        "categories": [1],
        "tags": tag_ids,
    }

    if featured_media_id:
        post_data["featured_media"] = featured_media_id

    try:
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
            print(f"  ✅ Published! Post ID: {post_id}")
            print(f"  URL: {post_url}")
        else:
            print(f"  ❌ WordPress publish error {resp.status_code}: {resp.text[:300]}")
            sys.exit(1)

    except Exception as e:
        print(f"  ❌ Publish failed: {e}")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("✅ v2.1 Article published successfully!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
