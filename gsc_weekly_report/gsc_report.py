#!/usr/bin/env python3
"""
Credit Kaagapay - GSC SEO 周报生成器
从 Google Search Console API 拉取数据，生成中文 HTML 周报。
使用 Service Account 认证，无需手动 OAuth。
"""

import json
import os
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Google API imports
# ---------------------------------------------------------------------------
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
except ImportError:
    print("缺少依赖，请运行: pip install google-api-python-client google-auth")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SITE_URL = "https://www.creditkaagapay.com/"
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reports"
CRED_FILE = BASE_DIR / "credentials.json"
TEMPLATE_FILE = BASE_DIR / "report_template.html"

# For GitHub Actions: allow credential JSON via environment variable
CRED_ENV = os.environ.get("GSC_CREDENTIALS_JSON")


def get_service():
    """Build authenticated GSC service."""
    if CRED_ENV:
        info = json.loads(CRED_ENV)
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    elif CRED_FILE.exists():
        creds = service_account.Credentials.from_service_account_file(str(CRED_FILE), scopes=SCOPES)
    else:
        print(f"错误: 找不到凭证文件 {CRED_FILE}")
        print("请将 Service Account JSON 文件放到该路径，或设置 GSC_CREDENTIALS_JSON 环境变量。")
        sys.exit(1)
    return build("searchconsole", "v1", credentials=creds)


def fetch_data(service, start_date, end_date, dimensions, row_limit=25):
    """Query GSC API."""
    body = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": dimensions,
        "rowLimit": row_limit,
    }
    resp = service.searchanalytics().query(siteUrl=SITE_URL, body=body).execute()
    return resp.get("rows", [])


def date_range_this_week():
    """Return (start, end) for the past 7 days (offset by 3 days for GSC delay)."""
    today = datetime.utcnow().date()
    end = today - timedelta(days=3)
    start = end - timedelta(days=6)
    return str(start), str(end)


def date_range_last_week():
    """Return (start, end) for the week before this_week."""
    today = datetime.utcnow().date()
    end = today - timedelta(days=10)
    start = end - timedelta(days=6)
    return str(start), str(end)


def pct_change(cur, prev):
    """Calculate percentage change, return formatted string."""
    if prev == 0:
        return "+∞" if cur > 0 else "0%"
    change = (cur - prev) / prev * 100
    sign = "+" if change > 0 else ""
    return f"{sign}{change:.1f}%"


def arrow(cur, prev, invert=False):
    """Return arrow emoji. For position, lower is better so invert=True."""
    if cur == prev:
        return "➡️"
    if invert:
        return "🟢 ↓" if cur < prev else "🔴 ↑"
    return "🟢 ↑" if cur > prev else "🔴 ↓"


def generate_report(service, output_path=None):
    """Pull data and generate HTML report."""
    tw_start, tw_end = date_range_this_week()
    lw_start, lw_end = date_range_last_week()

    print(f"本周数据: {tw_start} ~ {tw_end}")
    print(f"上周数据: {lw_start} ~ {lw_end}")

    # --- Fetch all data ---
    tw_queries = fetch_data(service, tw_start, tw_end, ["query"], row_limit=50)
    lw_queries = fetch_data(service, lw_start, lw_end, ["query"], row_limit=50)
    tw_pages = fetch_data(service, tw_start, tw_end, ["page"], row_limit=20)
    lw_pages = fetch_data(service, lw_start, lw_end, ["page"], row_limit=20)
    tw_totals = fetch_data(service, tw_start, tw_end, [], row_limit=1)
    lw_totals = fetch_data(service, lw_start, lw_end, [], row_limit=1)

    # --- Overall metrics ---
    tw_t = tw_totals[0] if tw_totals else {"clicks": 0, "impressions": 0, "ctr": 0, "position": 0}
    lw_t = lw_totals[0] if lw_totals else {"clicks": 0, "impressions": 0, "ctr": 0, "position": 0}

    overview = {
        "clicks": int(tw_t.get("clicks", 0)),
        "clicks_prev": int(lw_t.get("clicks", 0)),
        "impressions": int(tw_t.get("impressions", 0)),
        "impressions_prev": int(lw_t.get("impressions", 0)),
        "ctr": tw_t.get("ctr", 0) * 100,
        "ctr_prev": lw_t.get("ctr", 0) * 100,
        "position": tw_t.get("position", 0),
        "position_prev": lw_t.get("position", 0),
    }

    # --- Keywords table ---
    lw_query_map = {}
    for r in lw_queries:
        lw_query_map[r["keys"][0]] = r

    keywords = []
    for r in tw_queries[:30]:
        q = r["keys"][0]
        prev = lw_query_map.get(q, {})
        keywords.append({
            "query": q,
            "clicks": int(r.get("clicks", 0)),
            "impressions": int(r.get("impressions", 0)),
            "ctr": r.get("ctr", 0) * 100,
            "position": r.get("position", 0),
            "clicks_change": pct_change(r.get("clicks", 0), prev.get("clicks", 0)),
            "position_prev": prev.get("position", 0),
            "position_arrow": arrow(r.get("position", 0), prev.get("position", 0), invert=True),
        })

    # --- Pages table ---
    lw_page_map = {}
    for r in lw_pages:
        lw_page_map[r["keys"][0]] = r

    pages = []
    for r in tw_pages[:10]:
        url = r["keys"][0]
        prev = lw_page_map.get(url, {})
        short_url = url.replace(SITE_URL, "/")
        if len(short_url) > 60:
            short_url = short_url[:57] + "..."
        pages.append({
            "url": url,
            "short_url": short_url,
            "clicks": int(r.get("clicks", 0)),
            "impressions": int(r.get("impressions", 0)),
            "ctr": r.get("ctr", 0) * 100,
            "position": r.get("position", 0),
            "clicks_change": pct_change(r.get("clicks", 0), prev.get("clicks", 0)),
            "position_arrow": arrow(r.get("position", 0), prev.get("position", 0), invert=True),
        })

    # --- Build HTML ---
    report_data = {
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "period": f"{tw_start} ~ {tw_end}",
        "period_prev": f"{lw_start} ~ {lw_end}",
        "overview": overview,
        "keywords": keywords,
        "pages": pages,
    }

    html = build_html(report_data)

    # --- Save ---
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        output_path = REPORTS_DIR / f"weekly_report_{tw_end}.html"
    else:
        output_path = Path(output_path)

    output_path.write_text(html, encoding="utf-8")
    print(f"报告已生成: {output_path}")
    return str(output_path)


def build_html(data):
    """Generate HTML report from data dict."""
    template_path = TEMPLATE_FILE
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")
    else:
        print("警告: 模板文件不存在，使用内置简化模板")
        template = FALLBACK_TEMPLATE

    o = data["overview"]

    # Build keywords rows
    kw_rows = ""
    for i, kw in enumerate(data["keywords"], 1):
        kw_rows += f"""<tr>
            <td>{i}</td>
            <td class="query">{kw['query']}</td>
            <td>{kw['clicks']}</td>
            <td class="change">{kw['clicks_change']}</td>
            <td>{kw['impressions']}</td>
            <td>{kw['ctr']:.1f}%</td>
            <td>{kw['position']:.1f} {kw['position_arrow']}</td>
        </tr>"""

    # Build pages rows
    pg_rows = ""
    for i, pg in enumerate(data["pages"], 1):
        pg_rows += f"""<tr>
            <td>{i}</td>
            <td class="page-url" title="{pg['url']}">{pg['short_url']}</td>
            <td>{pg['clicks']}</td>
            <td class="change">{pg['clicks_change']}</td>
            <td>{pg['impressions']}</td>
            <td>{pg['ctr']:.1f}%</td>
            <td>{pg['position']:.1f} {pg['position_arrow']}</td>
        </tr>"""

    # Replacements
    html = template
    html = html.replace("{{GENERATED_AT}}", data["generated_at"])
    html = html.replace("{{PERIOD}}", data["period"])
    html = html.replace("{{PERIOD_PREV}}", data["period_prev"])
    html = html.replace("{{CLICKS}}", f"{o['clicks']:,}")
    html = html.replace("{{CLICKS_CHANGE}}", pct_change(o["clicks"], o["clicks_prev"]))
    html = html.replace("{{CLICKS_ARROW}}", arrow(o["clicks"], o["clicks_prev"]))
    html = html.replace("{{IMPRESSIONS}}", f"{o['impressions']:,}")
    html = html.replace("{{IMPRESSIONS_CHANGE}}", pct_change(o["impressions"], o["impressions_prev"]))
    html = html.replace("{{IMPRESSIONS_ARROW}}", arrow(o["impressions"], o["impressions_prev"]))
    html = html.replace("{{CTR}}", f"{o['ctr']:.2f}%")
    html = html.replace("{{CTR_CHANGE}}", pct_change(o["ctr"], o["ctr_prev"]))
    html = html.replace("{{CTR_ARROW}}", arrow(o["ctr"], o["ctr_prev"]))
    html = html.replace("{{POSITION}}", f"{o['position']:.1f}")
    html = html.replace("{{POSITION_CHANGE}}", pct_change(o["position_prev"], o["position"]))
    html = html.replace("{{POSITION_ARROW}}", arrow(o["position"], o["position_prev"], invert=True))
    html = html.replace("{{KEYWORD_ROWS}}", kw_rows)
    html = html.replace("{{PAGE_ROWS}}", pg_rows)

    return html


FALLBACK_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>GSC周报</title></head>
<body><h1>Credit Kaagapay SEO 周报</h1>
<p>报告周期: {{PERIOD}}</p>
<p>点击: {{CLICKS}} ({{CLICKS_CHANGE}}), 展示: {{IMPRESSIONS}} ({{IMPRESSIONS_CHANGE}})</p>
<p>CTR: {{CTR}} ({{CTR_CHANGE}}), 排名: {{POSITION}} ({{POSITION_CHANGE}})</p>
<h2>关键词</h2><table border="1">{{KEYWORD_ROWS}}</table>
<h2>热门页面</h2><table border="1">{{PAGE_ROWS}}</table>
<p>生成时间: {{GENERATED_AT}}</p></body></html>"""


def main():
    parser = argparse.ArgumentParser(description="Credit Kaagapay GSC 周报生成器")
    parser.add_argument("--output", "-o", help="输出文件路径（默认自动命名）")
    parser.add_argument("--test", action="store_true", help="测试 API 连接")
    args = parser.parse_args()

    service = get_service()

    if args.test:
        print("测试 API 连接...")
        try:
            sites = service.sites().list().execute()
            print(f"已连接！可访问的站点:")
            for s in sites.get("siteEntry", []):
                print(f"  - {s['siteUrl']} (权限: {s['permissionLevel']})")
        except Exception as e:
            print(f"连接失败: {e}")
            sys.exit(1)
        return

    generate_report(service, output_path=args.output)


if __name__ == "__main__":
    main()
