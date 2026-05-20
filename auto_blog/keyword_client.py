#!/usr/bin/env python3
"""
keyword_client.py — 从 Auto-keyword-of-financial-ph 仓库读取关键词数据。

功能：
1. 从 GitHub raw 文件读取 keywords.json
2. 选择高价值关键词（根据评分、搜索量、意图）
3. 提供关键词建议接口
"""

import json
import random
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# 关键词数据源 URL
KEYWORDS_JSON_URL = "https://raw.githubusercontent.com/CenaCai/Auto-keyword-of-financial-ph/main/keywords.json"

# 本地缓存路径
CACHE_FILE = Path(__file__).parent / "keywords_cache.json"
CACHE_TTL_SECONDS = 3600  # 1小时缓存

# 已发布文章追踪记录
PUBLISHED_TRACKER_FILE = Path(__file__).parent / "published_keywords.json"

# 周次记录（用于轮换）
CURRENT_WEEK = datetime.now(timezone.utc).isocalendar()[1]
ROTATION_FILE = Path(__file__).parent / "keyword_rotation.json"


def _load_published_tracker() -> dict:
    """加载已发布文章追踪记录。"""
    if PUBLISHED_TRACKER_FILE.exists():
        try:
            with open(PUBLISHED_TRACKER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"published_keywords": {}, "last_checked": None}


def _save_published_tracker(data: dict):
    """保存已发布文章追踪记录。"""
    with open(PUBLISHED_TRACKER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def refresh_published_from_wp(
    wp_site: str,
    wp_username: str,
    wp_password: str,
    limit: int = 100
) -> set:
    """
    从 WordPress API 获取已发布文章的标题，提取关键词。
    
    Args:
        wp_site: WordPress 站点 URL
        wp_username: 用户名
        wp_password: 应用密码
        limit: 获取的文章数量
    
    Returns:
        已发布关键词集合
    """
    import requests
    
    api = f"{wp_site}/wp-json/wp/v2/posts"
    params = {"status": "publish", "per_page": limit}
    
    try:
        resp = requests.get(api, params=params, auth=(wp_username, wp_password), timeout=30)
        if resp.status_code != 200:
            print(f"  ⚠️ WP API 失败: {resp.status_code}")
            return set()
        
        posts = resp.json()
        keywords = set()
        
        for post in posts:
            title = post.get("title", {}).get("rendered", "")
            if title:
                # 清理 HTML 标签
                import re
                clean_title = re.sub(r"<[^>]+>", "", title).strip()
                # 转为小写存储
                keywords.add(clean_title.lower())
        
        # 保存到追踪文件
        tracker = _load_published_tracker()
        tracker["published_keywords"] = {k: True for k in keywords}
        tracker["last_checked"] = datetime.now(timezone.utc).isoformat()
        tracker["count"] = len(keywords)
        _save_published_tracker(tracker)
        
        print(f"  ✅ 已追踪 {len(keywords)} 篇已发布文章")
        return keywords
    
    except Exception as e:
        print(f"  ⚠️ WP 获取失败: {e}")
        return set()


def get_published_keywords() -> set:
    """获取已发布的关键词集合。"""
    tracker = _load_published_tracker()
    return set(tracker.get("published_keywords", {}).keys())



def _load_rotation() -> dict:
    """加载关键词轮换记录。"""
    if ROTATION_FILE.exists():
        try:
            with open(ROTATION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"week": CURRENT_WEEK, "used_keywords": [], "content_gaps_used": []}



def _save_rotation(data: dict):
    """保存关键词轮换记录。"""
    global CURRENT_WEEK
    current_week = datetime.now(timezone.utc).isocalendar()[1]
    
    # 新一周开始时重置
    if data.get("week") != current_week:
        data = {"week": current_week, "used_keywords": [], "content_gaps_used": []}
    
    with open(ROTATION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def mark_keyword_used(keyword: str, is_content_gap: bool = False):
    """标记关键词已使用。"""
    data = _load_rotation()
    
    if is_content_gap:
        if "content_gaps_used" not in data:
            data["content_gaps_used"] = []
        if keyword not in data["content_gaps_used"]:
            data["content_gaps_used"].append(keyword)
    else:
        if "used_keywords" not in data:
            data["used_keywords"] = []
        if keyword not in data["used_keywords"]:
            data["used_keywords"].append(keyword)
    
    _save_rotation(data)
    print(f"  📝 已标记: {keyword} (内容缺口:{is_content_gap})")


def get_rotation_report() -> dict:
    """获取本周轮换报告。"""
    data = _load_rotation()
    return {
        "week": data.get("week", CURRENT_WEEK),
        "content_gaps_used": data.get("content_gaps_used", []),
        "other_used": data.get("used_keywords", []),
        "total_content_gaps": len(data.get("content_gaps_used", [])),
        "total_other": len(data.get("used_keywords", [])),
    }


def can_use_keyword(
    keyword: str,
    exclude_list: list = None,
    require_fresh: bool = False
) -> bool:
    """
    检查关键词是否可用。
    
    Args:
        keyword: 要检查的关键词
        exclude_list: 额外排除列表
        require_fresh: 是否要求本周未使用过
    
    Returns:
        True 如果关键词可用
    """
    # 检查排除列表
    if exclude_list and keyword.lower() in [k.lower() for k in exclude_list]:
        return False
    
    # 检查轮换记录（本周已使用）
    rotation = _load_rotation()
    all_used = (
        rotation.get("content_gaps_used", []) +
        rotation.get("used_keywords", [])
    )
    if keyword.lower() in [k.lower() for k in all_used]:
        if require_fresh:
            return False
    
    return True


def fetch_keywords(force_refresh: bool = False) -> dict:
    """
    从 GitHub 获取关键词数据（带本地缓存）。
    
    Args:
        force_refresh: 强制刷新缓存
    
    Returns:
        keywords.json 的完整数据
    """
    # 检查缓存
    if not force_refresh and CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
            
            # 检查缓存是否过期
            cached_time = cached.get("cached_at", "")
            if cached_time:
                cached_dt = datetime.fromisoformat(cached_time)
                if (datetime.now(timezone.utc) - cached_dt).total_seconds() < CACHE_TTL_SECONDS:
                    return cached
        except Exception as e:
            print(f"  ⚠️ 缓存读取失败: {e}")
    
    # 从 GitHub 获取
    print(f"  📥 从 GitHub 获取关键词数据...")
    try:
        resp = requests.get(KEYWORDS_JSON_URL, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            # 添加缓存时间戳
            data["cached_at"] = datetime.now(timezone.utc).isoformat()
            # 保存缓存
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  ✅ 获取成功: {data.get('total_keywords', 0)} 个关键词")
            return data
        else:
            print(f"  ❌ GitHub 请求失败: {resp.status_code}")
    except Exception as e:
        print(f"  ❌ 获取失败: {e}")
    
    # 返回空数据
    return {"keywords": {}, "total_keywords": 0}


def get_top_keywords(
    category: Optional[str] = None,
    min_score: int = 40,
    min_volume: int = 100,
    limit: int = 20,
    intent: Optional[str] = None,
    exclude_keywords: list = None,
) -> list:
    """
    获取高价值关键词列表。
    
    Args:
        category: 分类筛选 (product, traffic, credit, longtail, other)
        min_score: 最低评分
        min_volume: 最低搜索量
        limit: 返回数量限制
        intent: 意图筛选 (informational, transactional)
        exclude_keywords: 排除的关键词列表
    
    Returns:
        关键词列表，按评分排序
    """
    data = fetch_keywords()
    keywords = data.get("keywords", {})
    
    exclude_set = set(kw.lower() for kw in (exclude_keywords or []))
    
    all_keywords = []
    
    # 收集关键词
    categories = [category] if category else keywords.keys()
    for cat in categories:
        if cat not in keywords:
            continue
        for kw in keywords[cat]:
            # 筛选条件
            if kw.get("score", 0) < min_score:
                continue
            if kw.get("volume", 0) < min_volume:
                continue
            if intent and kw.get("intent") != intent:
                continue
            if kw["keyword"].lower() in exclude_set:
                continue
            
            kw["_category"] = cat
            all_keywords.append(kw)
    
    # 按评分排序
    all_keywords.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    return all_keywords[:limit]


def get_keyword_suggestions(
    focus: str = "content_gap",
    limit: int = 10
) -> dict:
    """
    获取关键词建议报告。
    
    Args:
        focus: 关注点
            - "content_gap": 内容缺口（高分低排名 = 有机会但未覆盖）
            - "quick_wins": 快速获胜（低竞争高分）
            - "high_volume": 高搜索量
            - "transactional": 交易意图（转化潜力高）
        limit: 每类建议数量
    
    Returns:
        建议报告字典
    """
    data = fetch_keywords()
    keywords = data.get("keywords", {})
    
    # 展平所有关键词
    all_kws = []
    for cat, items in keywords.items():
        for kw in items:
            kw["_category"] = cat
            all_kws.append(kw)
    
    suggestions = {
        "focus": focus,
        "updated_at": data.get("updated_at", "N/A"),
        "total_keywords": data.get("total_keywords", 0),
        "recommendations": [],
        "reason": ""
    }
    
    if focus == "content_gap":
        # 内容缺口：高搜索量 + 零点击/展示 = 有需求但我们没排名
        candidates = [
            kw for kw in all_kws
            if kw.get("volume", 0) >= 200
            and kw.get("clicks", 0) == 0
            and kw.get("impressions", 0) == 0
            and kw.get("score", 0) >= 40
        ]
        candidates.sort(key=lambda x: x.get("volume", 0), reverse=True)
        suggestions["recommendations"] = candidates[:limit]
        suggestions["reason"] = "高搜索量但零点击 = 有用户需求，我们尚未覆盖或排名太低"
    
    elif focus == "quick_wins":
        # 快速获胜：低难度 + 高分
        candidates = [
            kw for kw in all_kws
            if kw.get("difficulty", 100) <= 30
            and kw.get("score", 0) >= 50
        ]
        candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
        suggestions["recommendations"] = candidates[:limit]
        suggestions["reason"] = "低竞争 + 高评分 = 容易排名的机会"
    
    elif focus == "high_volume":
        # 高搜索量
        candidates = [
            kw for kw in all_kws
            if kw.get("volume", 0) >= 300
        ]
        candidates.sort(key=lambda x: x.get("volume", 0), reverse=True)
        suggestions["recommendations"] = candidates[:limit]
        suggestions["reason"] = "高搜索量 = 流量潜力大"
    
    elif focus == "transactional":
        # 交易意图
        candidates = [
            kw for kw in all_kws
            if kw.get("intent") == "transactional"
            and kw.get("volume", 0) >= 100
        ]
        candidates.sort(key=lambda x: (x.get("score", 0), x.get("volume", 0)), reverse=True)
        suggestions["recommendations"] = candidates[:limit]
        suggestions["reason"] = "交易意图 = 用户准备申请贷款/信用卡，转化潜力高"
    
    return suggestions


def pick_keyword_for_blog(
    strategy: str = "balanced",
    exclude_recent: list = None,
    force_content_gap: bool = False,
    refresh_wp: bool = False,
    wp_site: str = "",
    wp_username: str = "",
    wp_password: str = ""
) -> dict:
    """
    为博客文章选择关键词。
    
    Args:
        strategy: 选择策略
            - "balanced": 平衡策略（搜索量 + 评分 + 竞争度平衡）
            - "quick_win": 快速获胜（低竞争优先）
            - "high_potential": 高潜力（高搜索量优先）
            - "transactional": 交易意图优先
            - "content_gap": 强制内容缺口（高搜索量 + 零排名）
        exclude_recent: 最近用过的关键词（避免重复）
        force_content_gap: 强制使用内容缺口关键词（每周前2-3篇优先）
        refresh_wp: 是否从 WordPress 刷新已发布文章列表
        wp_site: WordPress 站点 URL
        wp_username: WordPress 用户名
        wp_password: WordPress 密码
    
    Returns:
        选中的关键词数据（含选择理由）
    """
    exclude_set = set(kw.lower() for kw in (exclude_recent or []))
    
    # 可选：从 WordPress 刷新已发布文章
    if refresh_wp and wp_site and wp_username and wp_password:
        published = refresh_published_from_wp(wp_site, wp_username, wp_password)
        exclude_set.update(published)
    else:
        # 加载本地已发布追踪
        published = get_published_keywords()
        exclude_set.update(k.lower() for k in published)
    
    # 加载本周轮换记录
    rotation = _load_rotation()
    used_this_week = (
        rotation.get("content_gaps_used", []) +
        rotation.get("used_keywords", [])
    )
    exclude_set.update(k.lower() for k in used_this_week)
    
    # 本周内容缺口配额检查
    content_gaps_quota = 3  # 每周至少3篇内容缺口
    content_gaps_used = len(rotation.get("content_gaps_used", []))
    
    # 强制内容缺口 or 还没用完配额
    if force_content_gap or strategy == "content_gap" or content_gaps_used < content_gaps_quota:
        # 获取内容缺口关键词
        data = fetch_keywords()
        all_kws = []
        for cat, items in data.get("keywords", {}).items():
            for kw in items:
                kw["_category"] = cat
                all_kws.append(kw)
        
        # 内容缺口：高搜索量 + 零点击/展示
        candidates = [
            kw for kw in all_kws
            if kw.get("volume", 0) >= 200
            and kw.get("clicks", 0) == 0
            and kw.get("score", 0) >= 40
        ]
        candidates.sort(key=lambda x: x.get("volume", 0), reverse=True)
        
        # 排除已使用的
        candidates = [kw for kw in candidates if kw["keyword"].lower() not in exclude_set]
        
        if candidates:
            selected = random.choices(candidates, weights=[kw.get("score", 50) for kw in candidates], k=1)[0]
            is_content_gap = True
            reason_template = f"内容缺口 (本周已用:{content_gaps_used}/{content_gaps_quota})"
        else:
            # 没内容缺口了，用普通关键词
            candidates = get_top_keywords(min_score=45, min_volume=150, limit=50)
            candidates = [kw for kw in candidates if kw["keyword"].lower() not in exclude_set]
            if not candidates:
                candidates = get_top_keywords(min_score=30, min_volume=50, limit=20)
            selected = random.choices(candidates, weights=[kw.get("score", 50) for kw in candidates], k=1)[0]
            is_content_gap = False
            reason_template = "降级选择：无内容缺口可用"
    else:
        # 根据策略获取候选
        if strategy == "quick_win":
            candidates = get_top_keywords(min_score=50, min_volume=100, limit=30)
            reason_template = "低竞争高分关键词，容易排名"
        elif strategy == "high_potential":
            candidates = get_top_keywords(min_score=40, min_volume=300, limit=30)
            reason_template = "高搜索量关键词，流量潜力大"
        elif strategy == "transactional":
            candidates = get_top_keywords(min_score=40, min_volume=100, intent="transactional", limit=30)
            reason_template = "交易意图关键词，转化潜力高"
        else:  # balanced
            candidates = get_top_keywords(min_score=45, min_volume=150, limit=50)
            reason_template = "平衡搜索量、评分和竞争度"
        
        # 排除已使用的
        candidates = [kw for kw in candidates if kw["keyword"].lower() not in exclude_set]
        
        if not candidates:
            # 降级：使用宽松条件
            candidates = get_top_keywords(min_score=30, min_volume=50, limit=20)
            candidates = [kw for kw in candidates if kw["keyword"].lower() not in exclude_set]
            reason_template = "降级选择：宽松条件"
        
        selected = random.choices(candidates, weights=[kw.get("score", 50) for kw in candidates], k=1)[0]
        is_content_gap = False
    
    # 标记关键词已使用
    mark_keyword_used(selected["keyword"], is_content_gap=is_content_gap)
    
    return {
        "keyword": selected["keyword"],
        "score": selected.get("score", 0),
        "volume": selected.get("volume", 0),
        "difficulty": selected.get("difficulty", 50),
        "intent": selected.get("intent", "informational"),
        "category": selected.get("_category", "other"),
        "sources": selected.get("sources", []),
        "is_content_gap": is_content_gap,
        "content_gaps_used_this_week": content_gaps_used,
        "reason": f"{reason_template} (评分:{selected.get('score',0)}, 搜索量:{selected.get('volume',0)}, 难度:{selected.get('difficulty',0)})",
        "data_points": _generate_data_points(selected),
    }


def _generate_data_points(kw: dict) -> str:
    """
    根据关键词生成数据点提示。
    """
    keyword = kw.get("keyword", "").lower()
    
    # 根据关键词类型返回相关数据
    if "emergency" in keyword:
        return (
            "Emergency loan options: SSS salary loan (10%/yr), Pag-IBIG MPL (10.5%/yr). "
            "Digital: Tonik Quick Loan (1 hour), GCash GLoan (5 min), Maya Credit (30 min). "
            "Average Filipino emergency expense: ₱15k-₱30k. 53% have no emergency fund (BSP)."
        )
    elif "ofw" in keyword:
        return (
            "OFW loan options: BDO OFW Loan, BPI Balikbayani, Pag-IBIG OFW Housing Loan. "
            "Requirements: POEA contract, proof of remittance, valid ID. "
            "Average OFW remittance: ₱30k-₱50k/month. "
            "Interest rates: 10-15%/yr for secured, 18-24%/yr for unsecured."
        )
    elif "student" in keyword:
        return (
            "Student loan options: SSS Calamity Loan (if parent is member), "
            "Student-friendly apps: Tala (₱1k-₱15k), Cashalo (₱1k-₱25k). "
            "Requirements: valid ID, student ID accepted by some apps. "
            "Tip: Start with small amounts to build credit history."
        )
    elif "unemployed" in keyword or "no payslip" in keyword:
        return (
            "No-payslip options: Digital lenders (GCash GLoan, Maya Credit, Tala, Cashalo). "
            "Requirements: valid ID, active bank/e-wallet account, good credit score. "
            "Tip: Pag-IBIG contributions can substitute for income proof. "
            "Warning: Avoid 5-6 lenders (20%/month interest)."
        )
    elif "bad credit" in keyword:
        return (
            "Bad credit options: Secured loans (use collateral), co-maker loans, "
            "digital lenders with alternative scoring (Tala, Cashalo). "
            "Rebuild credit: Pay existing debts on time, keep utilization below 30%. "
            "CIC score >700 = good. Each on-time payment improves score by ~5-10 points."
        )
    elif "credit score" in keyword or "cic" in keyword:
        return (
            "CIC score range: 300-850. >700 = good. On-time payment = ~35% of score. "
            "Free CIC report: creditinfo.gov.ph. Dispute errors: free, takes 30 days. "
            "Utilization below 30% boosts score 20-40 points in 2-3 months. "
            "Each new inquiry drops score ~15 points. Negative records: fall off after 5 years."
        )
    elif "quick" in keyword or "instant" in keyword or "fast" in keyword:
        return (
            "Fastest approvals: Tonik (1 hour), Maya (30 min), GCash GLoan (5 min). "
            "Same-day disbursement via GCash, Maya, or bank transfer (InstaPay/PESONet). "
            "InstaPay limit: ₱50k/transaction. PESONet: no limit but next-day for some banks. "
            "Quick loans typically charge 2-5% higher rates than standard bank loans."
        )
    else:
        # 通用贷款数据
        return (
            "SSS salary loan: up to ₱52k, 10%/yr, 24 payments. "
            "Pag-IBIG MPL: up to 80% of savings, 10.5%/yr. "
            "BPI personal loan: ₱20k-₱2M, 1.2-1.6%/mo. CIMB: from 1.19%/mo. "
            "BSP max rate for digital lenders: 6%/month. SEC blocked 200+ illegal apps in 2025."
        )


# 测试入口
if __name__ == "__main__":
    print("="*60)
    print("关键词建议测试")
    print("="*60)
    
    # 测试不同策略
    for strategy in ["balanced", "quick_win", "high_potential", "transactional"]:
        print(f"\n📊 策略: {strategy}")
        result = pick_keyword_for_blog(strategy)
        if result:
            print(f"  关键词: {result['keyword']}")
            print(f"  评分: {result['score']} | 搜索量: {result['volume']} | 难度: {result['difficulty']}")
            print(f"  意图: {result['intent']} | 分类: {result['category']}")
            print(f"  理由: {result['reason']}")
        else:
            print("  ❌ 未找到合适关键词")
    
    # 内容缺口建议
    print("\n" + "="*60)
    print("📋 内容缺口建议")
    print("="*60)
    gaps = get_keyword_suggestions("content_gap", limit=5)
    print(f"  更新时间: {gaps['updated_at']}")
    print(f"  理由: {gaps['reason']}")
    for i, kw in enumerate(gaps['recommendations'], 1):
        print(f"  {i}. {kw['keyword']} (搜索量:{kw['volume']}, 评分:{kw['score']})")
