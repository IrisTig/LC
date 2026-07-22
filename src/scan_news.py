#!/usr/bin/env python3
"""Scan collected LIFE Cooperative member websites for recent news.

This is step 2 of the prototype. It reads members from the SQLite database,
visits their official websites, detects likely news/blog/press pages, and stores
dated items from the last two months.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import re
import sqlite3
import ssl
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.request import Request, urlopen


USER_AGENT = "LIFE-member-monitor/0.2 (+local prototype; respectful daily news scan)"
NEWS_PATHS = (
    "/news",
    "/nieuws",
    "/blog",
    "/blogs",
    "/press",
    "/pers",
    "/newsroom",
    "/media",
    "/insights",
    "/articles",
    "/actualiteiten",
    "/updates",
)
NEWS_LINK_KEYWORDS = (
    "news",
    "nieuws",
    "blog",
    "press",
    "pers",
    "newsroom",
    "media",
    "insight",
    "article",
    "actualiteit",
    "update",
    "event",
)
RELEVANCE_KEYWORDS = {
    "funding": 18,
    "investment": 18,
    "grant": 16,
    "subsidy": 16,
    "clinical": 14,
    "trial": 14,
    "fda": 14,
    "ce mark": 14,
    "partnership": 12,
    "collaboration": 12,
    "acquisition": 16,
    "merger": 16,
    "launch": 12,
    "product": 8,
    "diagnostic": 8,
    "therapy": 8,
    "innovation": 8,
    "patent": 10,
    "award": 8,
    "appoint": 8,
    "vacancy": 5,
    "financiering": 18,
    "investering": 18,
    "subsidie": 16,
    "klinisch": 14,
    "samenwerking": 12,
    "overname": 16,
    "fusie": 16,
    "lancering": 12,
    "octrooi": 10,
    "prijs": 8,
}
MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    "januari": 1,
    "februari": 2,
    "maart": 3,
    "mei": 5,
    "juni": 6,
    "juli": 7,
    "augustus": 8,
    "oktober": 10,
}


@dataclass(frozen=True)
class Member:
    member_id: int
    name: str
    website_url: str


@dataclass(frozen=True)
class Link:
    url: str
    text: str


@dataclass(frozen=True)
class NewsCandidate:
    member: Member
    source_url: str
    title: str
    item_date: date
    snippet: str
    relevance_score: int
    reason: str
    content_hash: str


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[Link] = []
        self.title = ""
        self.h1 = ""
        self._parts: list[str] = []
        self._current_link: str | None = None
        self._current_link_text: list[str] = []
        self._in_title = False
        self._in_h1 = False
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if tag == "a" and attrs_dict.get("href"):
            self._current_link = attrs_dict["href"]
            self._current_link_text = []
        if tag == "title":
            self._in_title = True
        if tag == "h1":
            self._in_h1 = True
        if tag in {"p", "br", "div", "section", "li", "article", "h1", "h2", "h3", "time"}:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if tag == "a" and self._current_link:
            text = normalize_space(" ".join(self._current_link_text))
            self.links.append(Link(self._current_link, text))
            self._current_link = None
            self._current_link_text = []
        if tag == "title":
            self._in_title = False
        if tag == "h1":
            self._in_h1 = False
        if tag in {"p", "div", "section", "li", "article", "h1", "h2", "h3", "time"}:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._current_link is not None:
            self._current_link_text.append(data)
        if self._in_title:
            self.title += data
        if self._in_h1:
            self.h1 += data
        self._parts.append(data)

    def text(self) -> str:
        cleaned = re.sub(r"[ \t\r\f\v]+", " ", "".join(self._parts))
        cleaned = re.sub(r"\n\s*\n+", "\n", cleaned)
        return cleaned.strip()


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def normalize_url(url: str, base_url: str | None = None) -> str | None:
    url = html.unescape(url).strip()
    if not url or url.lower().startswith(("mailto:", "tel:", "javascript:", "#")):
        return None
    if url.startswith("//"):
        url = "https:" + url
    elif base_url:
        url = urljoin(base_url, url)
    elif re.match(r"^www\.", url, flags=re.IGNORECASE):
        url = "https://" + url
    elif not re.match(r"^https?://", url, flags=re.IGNORECASE):
        url = "https://" + url
    url, _fragment = urldefrag(url)
    return url.rstrip("/")


def same_site(url: str, root: str) -> bool:
    url_host = urlparse(url).netloc.lower().replace("www.", "")
    root_host = urlparse(root).netloc.lower().replace("www.", "")
    return url_host == root_host


def fetch_html(url: str, timeout: int) -> str | None:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*;q=0.8"})
    try:
        with urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return None
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read(2_000_000).decode(charset, errors="replace")
    except (HTTPError, URLError, TimeoutError, ssl.SSLError, ValueError):
        return None


def parse_page(page_html: str) -> PageParser:
    parser = PageParser()
    parser.feed(page_html)
    return parser


def extract_dates(text: str, url: str) -> list[date]:
    dates: list[date] = []
    haystack = f"{url}\n{text[:6000]}"

    for match in re.finditer(r"\b(20\d{2})[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])\b", haystack):
        dates.append(safe_date(int(match.group(1)), int(match.group(2)), int(match.group(3))))
    for match in re.finditer(r"\b(0?[1-9]|[12]\d|3[01])[-/](0?[1-9]|1[0-2])[-/](20\d{2})\b", haystack):
        dates.append(safe_date(int(match.group(3)), int(match.group(2)), int(match.group(1))))
    month_pattern = "|".join(MONTHS)
    for match in re.finditer(
        rf"\b(0?[1-9]|[12]\d|3[01])\s+({month_pattern})\s+(20\d{{2}})\b",
        haystack,
        flags=re.IGNORECASE,
    ):
        dates.append(safe_date(int(match.group(3)), MONTHS[match.group(2).lower()], int(match.group(1))))
    for match in re.finditer(
        rf"\b({month_pattern})\s+(0?[1-9]|[12]\d|3[01]),?\s+(20\d{{2}})\b",
        haystack,
        flags=re.IGNORECASE,
    ):
        dates.append(safe_date(int(match.group(3)), MONTHS[match.group(1).lower()], int(match.group(2))))

    return [d for d in dates if d is not None]


def safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def score_relevance(text: str) -> tuple[int, str]:
    lower = text.lower()
    score = 10
    reasons: list[str] = []
    for keyword, points in RELEVANCE_KEYWORDS.items():
        if keyword in lower:
            score += points
            reasons.append(keyword)
    score = min(score, 100)
    reason = ", ".join(reasons[:6]) if reasons else "dated item on member site"
    return score, reason


def make_snippet(text: str, max_chars: int = 500) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    body = normalize_space(" ".join(lines[:8]))
    return body[:max_chars].rsplit(" ", 1)[0] if len(body) > max_chars else body


def title_from(parser: PageParser, url: str) -> str:
    title = normalize_space(parser.h1 or parser.title)
    if title:
        return re.sub(r"\s+[|-]\s+.*$", "", title).strip()
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    return slug.replace("-", " ").replace("_", " ").title() or url


def load_members(db_path: Path) -> list[Member]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, name, website_url
            FROM members
            WHERE website_url IS NOT NULL AND website_url != ''
            ORDER BY name, detail_slug
            """
        ).fetchall()
    return [Member(member_id=row[0], name=row[1], website_url=row[2]) for row in rows]


def init_db(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS news_scan_runs (
                id INTEGER PRIMARY KEY,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                cutoff_date TEXT NOT NULL,
                members_scanned INTEGER NOT NULL,
                items_found INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS news_items (
                id INTEGER PRIMARY KEY,
                member_id INTEGER NOT NULL,
                member_name TEXT NOT NULL,
                source_url TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                item_date TEXT NOT NULL,
                snippet TEXT NOT NULL,
                relevance_score INTEGER NOT NULL,
                reason TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                FOREIGN KEY(member_id) REFERENCES members(id)
            )
            """
        )


def candidate_seed_urls(root_url: str) -> list[str]:
    root = normalize_url(root_url)
    if not root:
        return []
    parsed = urlparse(root)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    urls = [root]
    urls.extend(normalize_url(path, origin) for path in NEWS_PATHS)
    return [url for url in urls if url]


def discover_candidate_urls(member: Member, timeout: int, max_pages: int) -> list[str]:
    seeds = candidate_seed_urls(member.website_url)
    discovered: list[str] = []
    seen: set[str] = set()

    for seed in seeds:
        if len(discovered) >= max_pages:
            break
        if seed in seen:
            continue
        seen.add(seed)
        page_html = fetch_html(seed, timeout)
        if not page_html:
            continue
        discovered.append(seed)
        parser = parse_page(page_html)
        for link in parser.links:
            url = normalize_url(link.url, seed)
            if not url or url in seen or not same_site(url, member.website_url):
                continue
            combined = f"{url} {link.text}".lower()
            if any(keyword in combined for keyword in NEWS_LINK_KEYWORDS):
                seen.add(url)
                discovered.append(url)
                if len(discovered) >= max_pages:
                    break
    return discovered


def scan_member(
    member: Member,
    cutoff: date,
    through_date: date,
    timeout: int,
    max_pages: int,
    delay: float,
) -> list[NewsCandidate]:
    candidates: list[NewsCandidate] = []
    for url in discover_candidate_urls(member, timeout, max_pages):
        page_html = fetch_html(url, timeout)
        if not page_html:
            continue
        parser = parse_page(page_html)
        text = parser.text()
        dates = [
            item_date
            for item_date in extract_dates(text, url)
            if cutoff <= item_date <= through_date
        ]
        if not dates:
            time.sleep(delay)
            continue
        item_date = max(dates)
        title = title_from(parser, url)
        snippet = make_snippet(text)
        score, reason = score_relevance(f"{title}\n{snippet}")
        content_hash = hashlib.sha256(normalize_space(text).encode("utf-8")).hexdigest()
        candidates.append(
            NewsCandidate(
                member=member,
                source_url=url,
                title=title,
                item_date=item_date,
                snippet=snippet,
                relevance_score=score,
                reason=reason,
                content_hash=content_hash,
            )
        )
        time.sleep(delay)
    return candidates


def save_news(
    db_path: Path,
    candidates: list[NewsCandidate],
    started_at: str,
    cutoff: date,
    through_date: date,
    members_scanned: int,
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        for item in candidates:
            conn.execute(
                """
                INSERT INTO news_items (
                    member_id, member_name, source_url, title, item_date, snippet,
                    relevance_score, reason, content_hash, first_seen_at, last_seen_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_url) DO UPDATE SET
                    member_id = excluded.member_id,
                    member_name = excluded.member_name,
                    title = excluded.title,
                    item_date = excluded.item_date,
                    snippet = excluded.snippet,
                    relevance_score = excluded.relevance_score,
                    reason = excluded.reason,
                    content_hash = excluded.content_hash,
                    last_seen_at = excluded.last_seen_at
                """,
                (
                    item.member.member_id,
                    item.member.name,
                    item.source_url,
                    item.title,
                    item.item_date.isoformat(),
                    item.snippet,
                    item.relevance_score,
                    item.reason,
                    item.content_hash,
                    now,
                    now,
                ),
            )
        conn.execute(
            """
            INSERT INTO news_scan_runs (
                started_at, finished_at, cutoff_date, members_scanned, items_found
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (started_at, now, f"{cutoff.isoformat()}..{through_date.isoformat()}", members_scanned, len(candidates)),
        )
    return len(candidates)


def export_csv(db_path: Path, csv_path: Path, cutoff: date, through_date: date) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn, csv_path.open("w", newline="", encoding="utf-8-sig") as file:
        rows = conn.execute(
            """
            SELECT member_name, item_date, relevance_score, title, source_url, reason, snippet
            FROM news_items
            WHERE item_date BETWEEN ? AND ?
            ORDER BY item_date DESC, relevance_score DESC, member_name
            """,
            (cutoff.isoformat(), through_date.isoformat()),
        ).fetchall()
        writer = csv.writer(file)
        writer.writerow(["member_name", "item_date", "relevance_score", "title", "source_url", "reason", "snippet"])
        writer.writerows(rows)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan LIFE member websites for recent news.")
    parser.add_argument("--db", type=Path, default=Path("data/life_members.sqlite"))
    parser.add_argument("--csv", type=Path, default=Path("outputs/life_members/recent_news.csv"))
    parser.add_argument("--days", type=int, default=61, help="Lookback window in days.")
    parser.add_argument("--since", help="Start date in YYYY-MM-DD format. Defaults to today minus --days.")
    parser.add_argument("--until", help="End date in YYYY-MM-DD format. Defaults to today.")
    parser.add_argument("--timeout", type=int, default=10, help="Per-request timeout in seconds.")
    parser.add_argument("--max-pages-per-member", type=int, default=14)
    parser.add_argument("--delay", type=float, default=0.15)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if not args.db.exists():
        print(f"Database not found: {args.db}", file=sys.stderr)
        return 1

    init_db(args.db)
    today = datetime.now().date()
    cutoff = date.fromisoformat(args.since) if args.since else today - timedelta(days=args.days)
    through_date = date.fromisoformat(args.until) if args.until else today
    started_at = datetime.now(timezone.utc).isoformat()
    members = load_members(args.db)
    all_candidates: list[NewsCandidate] = []

    for index, member in enumerate(members, start=1):
        print(f"[{index:02d}/{len(members):02d}] {member.name}: {member.website_url}")
        found = scan_member(member, cutoff, through_date, args.timeout, args.max_pages_per_member, args.delay)
        print(f"  found {len(found)} recent dated item(s)")
        all_candidates.extend(found)

    saved = save_news(args.db, all_candidates, started_at, cutoff, through_date, len(members))
    export_csv(args.db, args.csv, cutoff, through_date)
    print(f"Saved {saved} news item(s) since {cutoff.isoformat()}.")
    print(f"CSV: {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
