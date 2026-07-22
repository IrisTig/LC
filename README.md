# LIFE Member Monitor

Daily monitor for LIFE Cooperative members and recent news on their official
websites.

The current version does three things:

1. Collects members from `https://lifecooperative.nl/en/members`.
2. Scans member websites for dated news/blog/press-like pages.
3. Classifies findings into `newsworthy`, `possibly_newsworthy`, or `noise`.

Extra website URLs that are not exposed on the LIFE member pages can be added in:

```text
data/member_websites.csv
```

The collector uses those URLs only when the scraped member record has no website.

## Outputs

The scripts write:

```text
data/life_members.sqlite
outputs/life_members/life_members.csv
outputs/life_members/recent_news.csv
outputs/life_members/recent_news_articles.csv
outputs/life_members/classified_recent_news.csv
```

## Run Locally

Use Python 3.12 or newer.

```powershell
.\run_all.ps1
```

On Windows you can schedule those commands with Task Scheduler. In GitHub, the
included workflow runs them daily.

On macOS/Linux:

```bash
bash run_all.sh
```

## Backfill 2026

Run this once when setting up the repository to collect all detected 2026 news
up to today:

```bash
python src/collect_members.py
python src/scan_news.py --since 2026-01-01 --timeout 8 --max-pages-per-member 12 --delay 0.1
python src/classify_news.py --since 2026-01-01
```

After that, the daily GitHub Actions workflow only scans the last 7 days. Items
are stored by unique `source_url`, so already-seen news is updated rather than
duplicated.

## Dashboard

Install the dashboard dependencies:

```bash
pip install -r requirements.txt
```

Run:

```bash
streamlit run src/dashboard.py
```

The dashboard reads CSV files from:

```text
outputs/life_members/
```

You can also upload CSV files from a downloaded GitHub Actions artifact in the
dashboard sidebar.

## Run In GitHub Actions

Create a GitHub repository, copy this folder into it, and push.

Example:

```bash
git init
git add .
git commit -m "Add LIFE member monitor"
git branch -M main
git remote add origin https://github.com/YOUR-ACCOUNT/life-member-monitor.git
git push -u origin main
```

The workflow is in:

```text
.github/workflows/daily-scan.yml
```

It runs daily and can also be started manually with **Run workflow** in the
GitHub Actions tab.

After each run, download the artifact named:

```text
life-member-monitor-output
```

## Notes

- The pipeline scripts use only Python standard-library modules; the dashboard
  uses `pandas` and `streamlit`.
- The classifier is a transparent local triage layer, not yet a live OpenAI API
  classifier.
- The scanner visits member websites from the LIFE member detail pages plus
  supplemental URLs in `data/member_websites.csv`.
- Some member websites block simple HTTP clients or require JavaScript. Those
  can be handled later with Playwright.
- Keep request delays conservative when running this daily.

## Next Improvements

- Add OpenAI API classification using `OPENAI_API_KEY`.
- Store results in Postgres instead of SQLite.
- Send a daily summary by email or Teams.
- Add better article extraction for sites with JavaScript-heavy pages.
