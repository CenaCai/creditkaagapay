#!/usr/bin/env python3
"""
keyword_recommendations.py — 生成关键词优化建议报告。

功能：
1. 分析关键词数据
2. 生成博客主题建议
3. 输出 Markdown 报告（可发送给用户）
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# 导入关键词客户端
try:
    from keyword_client import fetch_keywords, get_keyword_suggestions, get_top_keywords
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from keyword_client import fetch_keywords, get_keyword_suggestions, get_top_keywords


def generate_weekly_recommendations() -> str:
    """
    生成每周关键词优化建议报告。
    
    Returns:
        Markdown 格式的报告文本
    """
    print("📊 生成关键词优化建议...")
    
    # 获取关键词数据
    data = fetch_keywords()
    keywords = data.get("keywords", {})
    updated_at = data.get("updated_at", "N/A")
    total = data.get("total_keywords", 0)
    
    if not keywords:
        return "❌ 无法获取关键词数据"
    
    # 展平所有关键词
    all_kws = []
    for cat, items in keywords.items():
        for kw in items:
            kw["_category"] = cat
            all_kws.append(kw)
    
    # 1. 内容缺口：高搜索量但零排名
    content_gaps = [
        kw for kw in all_kws
        if kw.get("volume", 0) >= 200
        and kw.get("clicks", 0) == 0
        and kw.get("impressions", 0) == 0
        and kw.get("score", 0) >= 40
    ]
    content_gaps.sort(key=lambda x: x.get("volume", 0), reverse=True)
    
    # 2. 快速获胜：低竞争高分
    quick_wins = [
        kw for kw in all_kws
        if kw.get("difficulty", 100) <= 30
        and kw.get("score", 0) >= 50
        and kw.get("volume", 0) >= 100
    ]
    quick_wins.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    # 3. 交易意图：转化潜力高
    transactional = [
        kw for kw in all_kws
        if kw.get("intent") == "transactional"
        and kw.get("volume", 0) >= 100
    ]
    transactional.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    # 4. 已有排名但可提升：有展示但点击率低
    improve_ranking = [
        kw for kw in all_kws
        if kw.get("impressions", 0) >= 50
        and kw.get("position", 0) > 5  # 排名在5名之后
        and kw.get("position", 0) <= 20  # 但在前20名
    ]
    improve_ranking.sort(key=lambda x: x.get("impressions", 0), reverse=True)
    
    # 生成报告
    report = f"""# 📊 关键词优化建议报告

**更新时间:** {updated_at}  
**总关键词数:** {total}

---

## 🎯 本周建议写的博客主题

### 1. 内容缺口（高搜索量 + 零排名 = 机会）

以下是用户在搜索，但我们尚未覆盖或排名太低的主题：

| 关键词 | 搜索量 | 难度 | 评分 | 建议 |
|--------|--------|------|------|------|
"""
    
    for i, kw in enumerate(content_gaps[:10], 1):
        keyword = kw["keyword"]
        volume = kw.get("volume", 0)
        difficulty = kw.get("difficulty", 0)
        score = kw.get("score", 0)
        
        # 生成建议标题
        if "emergency" in keyword.lower():
            title_suggestion = f"How to Get an Emergency Loan in the Philippines (Complete Guide)"
        elif "ofw" in keyword.lower():
            title_suggestion = f"OFW Loan Philippines: Best Options and Requirements 2026"
        elif "unemployed" in keyword.lower() or "no payslip" in keyword.lower():
            title_suggestion = f"Loans Without Payslip in the Philippines: Legit Options"
        else:
            title_suggestion = f"{keyword.title()} - Complete Guide for Filipinos"
        
        report += f"| {keyword} | {volume} | {difficulty} | {score} | {title_suggestion[:50]}... |\n"
    
    report += f"""
**💡 建议:** 每周写 2-3 篇这类主题，快速填补内容缺口。

---

### 2. 快速获胜（低竞争 + 高评分 = 容易排名）

| 关键词 | 搜索量 | 难度 | 评分 | 竞争度 |
|--------|--------|------|------|--------|
"""
    
    for kw in quick_wins[:8]:
        keyword = kw["keyword"]
        volume = kw.get("volume", 0)
        difficulty = kw.get("difficulty", 0)
        score = kw.get("score", 0)
        
        # 竞争度评估
        if difficulty <= 20:
            competition = "🟢 极低"
        elif difficulty <= 30:
            competition = "🟡 低"
        else:
            competition = "🟠 中等"
        
        report += f"| {keyword} | {volume} | {difficulty} | {score} | {competition} |\n"
    
    report += f"""
**💡 建议:** 这类关键词容易排名，适合用来测试新内容或快速获取流量。

---

### 3. 交易意图关键词（转化潜力高）

用户准备申请贷款/信用卡时搜索的关键词：

| 关键词 | 搜索量 | 意图 | 建议 |
|--------|--------|------|------|
"""
    
    for kw in transactional[:8]:
        keyword = kw["keyword"]
        volume = kw.get("volume", 0)
        score = kw.get("score", 0)
        
        report += f"| {keyword} | {volume} | 💰 交易型 | 在文章中加入明显的 CTA（申请链接、下载按钮） |\n"
    
    report += f"""
**💡 建议:** 这类文章的 CTA 转化率通常较高，确保在开头和结尾都放置"检查信用分"按钮。

---

### 4. 已有排名可提升

以下关键词我们已有排名，但可以通过优化提升：

| 关键词 | 当前排名 | 展示次数 | 点击次数 | CTR | 建议 |
|--------|----------|----------|----------|-----|------|
"""
    
    for kw in improve_ranking[:8]:
        keyword = kw["keyword"]
        position = kw.get("position", 0)
        impressions = kw.get("impressions", 0)
        clicks = kw.get("clicks", 0)
        ctr = (clicks / impressions * 100) if impressions > 0 else 0
        
        suggestion = "优化标题和 meta description" if ctr < 5 else "增加内链和相关内容"
        
        report += f"| {keyword} | #{position:.1f} | {impressions} | {clicks} | {ctr:.1f}% | {suggestion} |\n"
    
    report += f"""
**💡 建议:** 排名在第5-20名的文章，通过优化可以进入前5，流量可提升3-5倍。

---

## 📈 总结与行动计划

### 本周优先写的主题（Top 5）：

"""
    
    # 综合考虑搜索量、竞争度、评分，选出最佳5个
    priority_keywords = []
    
    # 优先内容缺口
    for kw in content_gaps[:3]:
        priority_keywords.append((kw, "内容缺口 - 高搜索量无排名"))
    
    # 补充快速获胜
    for kw in quick_wins[:2]:
        if kw not in [k for k, _ in priority_keywords]:
            priority_keywords.append((kw, "快速获胜 - 低竞争高评分"))
    
    for i, (kw, reason) in enumerate(priority_keywords[:5], 1):
        keyword = kw["keyword"]
        volume = kw.get("volume", 0)
        difficulty = kw.get("difficulty", 0)
        score = kw.get("score", 0)
        
        report += f"{i}. **{keyword}**\n"
        report += f"   - 搜索量: {volume} | 难度: {difficulty} | 评分: {score}\n"
        report += f"   - 原因: {reason}\n\n"
    
    report += f"""
### 长期策略建议：

1. **每周写 2-3 篇"内容缺口"主题** - 快速填补用户需求
2. **每月写 1 篇"快速获胜"主题** - 轻松获取排名和流量
3. **交易意图文章加入强 CTA** - 在开头、中间、结尾都放置"免费查信用分"按钮
4. **优化已有文章** - 排名在第5-20名的文章，更新内容可提升排名

---

*报告生成时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*  
*数据来源: [Auto-keyword-of-financial-ph](https://github.com/CenaCai/Auto-keyword-of-financial-ph)*
"""
    
    return report


def save_recommendations_to_file(output_path: Optional[Path] = None) -> Path:
    """
    保存推荐报告到文件。
    
    Args:
        output_path: 输出路径，默认为当前目录下的 keyword_recommendations.md
    
    Returns:
        实际保存的文件路径
    """
    if output_path is None:
        output_path = Path(__file__).parent / "keyword_recommendations.md"
    
    report = generate_weekly_recommendations()
    output_path.write_text(report, encoding="utf-8")
    
    print(f"✅ 报告已保存: {output_path}")
    return output_path


# 测试入口
if __name__ == "__main__":
    report = generate_weekly_recommendations()
    print("\n" + "="*70)
    print(report)
    print("="*70)
    
    # 保存到文件
    save_recommendations_to_file()
