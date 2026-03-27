# Credit Kaagapay SEO Tools

https://www.creditkaagapay.com/

## GSC Weekly Report (SEO 周报)

每周一自动从 Google Search Console 拉取数据，生成中文 HTML 周报。

### 报告内容

- 总点击量 / 展示量 / CTR / 平均排名（含周环比变化）
- Top 30 关键词排名变化
- Top 10 热门页面表现

### 运行方式

**GitHub Actions (推荐)**：每周一 UTC 08:00 自动运行，报告自动 commit 到 `gsc_weekly_report/reports/`。

**手动运行**：
```bash
cd gsc_weekly_report
pip install -r requirements.txt
python gsc_report.py          # 生成周报
python gsc_report.py --test   # 测试 API 连接
```

### 配置

1. 在 Google Cloud Console 创建 Service Account 并启用 Search Console API
2. 在 GSC Settings → Users and permissions 添加 Service Account 邮箱（Restricted 权限）
3. 将 Service Account JSON 密钥内容添加到 GitHub Repo → Settings → Secrets → `GSC_CREDENTIALS_JSON`
4. 或将 JSON 文件保存为 `gsc_weekly_report/credentials.json`（本地运行时）

### 文件结构

```
gsc_weekly_report/
├── gsc_report.py          # 主脚本
├── report_template.html   # HTML 报告模板
├── requirements.txt       # Python 依赖
├── credentials.json       # Service Account 密钥 (不提交到 Git)
└── reports/               # 生成的报告
    └── weekly_report_YYYY-MM-DD.html
```
