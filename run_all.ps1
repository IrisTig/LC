$ErrorActionPreference = "Stop"

python src/collect_members.py --delay 0.2
python src/scan_news.py --days 61 --timeout 8 --max-pages-per-member 8 --delay 0.1
python src/classify_news.py

Write-Host "Done. Outputs are in outputs/life_members."
