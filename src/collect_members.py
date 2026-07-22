#!/usr/bin/env python3
"""Collect LIFE Cooperative members into a local SQLite database.

Step 1 of the monitor: only collect cooperative members and their official
websites. Later steps can use the same database to scan member sites for news.
"""

from __future__ import annotations

import argparse
import csv
import html
import re
import sqlite3
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


BASE_URL = "https://lifecooperative.nl"
MEMBERS_URL = f"{BASE_URL}/en/members"
USER_AGENT = "LIFE-member-monitor/0.1 (+local prototype; respectful daily check)"


@dataclass(frozen=True)
class MemberLink:
    name: str
    detail_url: str


@dataclass(frozen=True)
class Member:
    name: str
    detail_slug: str
    detail_url: str
    website_url: str | None
    description: str


class TextExtractor(HTMLParser):
    """Small dependency-free text extractor for simple CMS pages."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if tag in {"p", "br", "div", "section", "li", "h1", "h2", "h3"}:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if tag in {"p", "div", "section", "li", "h1", "h2", "h3"}:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._parts.append(data)

    def text(self) -> str:
        cleaned = re.sub(r"[ \t\r\f\v]+", " ", "".join(self._parts))
        cleaned = re.sub(r"\n\s*\n+", "\n", cleaned)
        return cleaned.strip()


def fetch_html(url: str, timeout: int = 30) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def normalize_url(url: str | None, base_url: str = BASE_URL) -> str | None:
    if not url:
        return None
    url = html.unescape(url).strip()
    if not url or url.lower().startswith(("mailto:", "tel:", "#")):
        return None
    if url.startswith("//"):
        return "https:" + url
    if re.match(r"^www\.", url, flags=re.IGNORECASE):
        return "https://" + url
    if not re.match(r"^https?://", url, flags=re.IGNORECASE):
        parsed = urlparse(url)
        if parsed.netloc or "." in parsed.path.split("/")[0]:
            return "https://" + url.lstrip("/")
        return urljoin(base_url, url)
    return url


def extract_text(page_html: str) -> str:
    parser = TextExtractor()
    parser.feed(page_html)
    return parser.text()


def extract_member_links(listing_html: str) -> list[MemberLink]:
    pattern = re.compile(
        r'<a\s+href="(?P<href>/en/members/[^"]+)"[^>]*aria-label="Go to the page of (?P<name>[^"]+)"',
        flags=re.IGNORECASE,
    )
    links: list[MemberLink] = []
    seen: set[str] = set()
    for match in pattern.finditer(listing_html):
        detail_url = urljoin(BASE_URL, html.unescape(match.group("href")))
        if detail_url in seen:
            continue
        seen.add(detail_url)
        links.append(MemberLink(name=html.unescape(match.group("name")).strip(), detail_url=detail_url))
    return links


def extract_next_url(listing_html: str) -> str | None:
    match = re.search(r'<link\s+href="([^"]+)"\s+rel="next"', listing_html, flags=re.IGNORECASE)
    return normalize_url(match.group(1)) if match else None


def extract_website_url(detail_html: str) -> str | None:
    website_label = re.search(
        r"Website:\s*<a\b[^>]*href=\"([^\"]+)\"",
        detail_html,
        flags=re.IGNORECASE,
    )
    if website_label:
        return normalize_url(website_label.group(1))

    content_html = re.split(r"<footer\b", detail_html, maxsplit=1, flags=re.IGNORECASE)[0]
    for href in re.findall(r"<a\b[^>]*href=\"([^\"]+)\"", content_html, flags=re.IGNORECASE):
        url = normalize_url(href)
        if url and "lifecooperative.nl" not in urlparse(url).netloc:
            return url
    return None


def extract_description(detail_html: str, name: str) -> str:
    content_html = re.split(r"<footer\b", detail_html, maxsplit=1, flags=re.IGNORECASE)[0]
    text = extract_text(content_html)
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    useful: list[str] = []
    in_content = False
    for line in lines:
        if line == name:
            in_content = True
            continue
        if line.lower().startswith("website:"):
            break
        if line == "Contact information":
            break
        if line == "Read more":
            continue
        if in_content and line not in {"Members", "Contact information"} and line not in useful:
            useful.append(line)

    description = " ".join(useful)
    description = re.sub(r"\s+", " ", description).strip()
    if description:
        return description

    # Fallback keeps the database useful even if the page template changes.
    without_website = re.split(r"\bWebsite:\b", text, maxsplit=1, flags=re.IGNORECASE)[0]
    return re.sub(r"\s+", " ", without_website).strip()


def collect_member_links(delay_seconds: float) -> list[MemberLink]:
    links: list[MemberLink] = []
    seen_detail_urls: set[str] = set()
    next_url: str | None = MEMBERS_URL

    while next_url:
        listing_html = fetch_html(next_url)
        for link in extract_member_links(listing_html):
            if link.detail_url not in seen_detail_urls:
                links.append(link)
                seen_detail_urls.add(link.detail_url)
        next_url = extract_next_url(listing_html)
        if next_url:
            time.sleep(delay_seconds)

    return links


def collect_members(delay_seconds: float) -> list[Member]:
    members: list[Member] = []
    for link in collect_member_links(delay_seconds):
        detail_html = fetch_html(link.detail_url)
        members.append(
            Member(
                name=link.name,
                detail_slug=urlparse(link.detail_url).path.rstrip("/").split("/")[-1],
                detail_url=link.detail_url,
                website_url=extract_website_url(detail_html),
                description=extract_description(detail_html, link.name),
            )
        )
        time.sleep(delay_seconds)
    return members


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        existing_columns = [
            row[1]
            for row in conn.execute("PRAGMA table_info(members)").fetchall()
        ]
        if existing_columns and "detail_slug" not in existing_columns:
            conn.execute("DROP TABLE members")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                detail_slug TEXT NOT NULL UNIQUE,
                detail_url TEXT NOT NULL UNIQUE,
                website_url TEXT,
                description TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT 'lifecooperative.nl',
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS collection_runs (
                id INTEGER PRIMARY KEY,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                member_count INTEGER NOT NULL
            )
            """
        )


def save_members(db_path: Path, members: Iterable[Member], started_at: str) -> int:
    now = datetime.now(timezone.utc).isoformat()
    count = 0
    with sqlite3.connect(db_path) as conn:
        for member in members:
            conn.execute(
                """
                INSERT INTO members (
                    name, detail_slug, detail_url, website_url, description, first_seen_at, last_seen_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(detail_url) DO UPDATE SET
                    detail_url = excluded.detail_url,
                    detail_slug = excluded.detail_slug,
                    name = excluded.name,
                    website_url = excluded.website_url,
                    description = excluded.description,
                    last_seen_at = excluded.last_seen_at
                """,
                (
                    member.name,
                    member.detail_slug,
                    member.detail_url,
                    member.website_url,
                    member.description,
                    now,
                    now,
                ),
            )
            count += 1
        conn.execute(
            """
            INSERT INTO collection_runs (started_at, finished_at, member_count)
            VALUES (?, ?, ?)
            """,
            (started_at, now, count),
        )
    return count


def export_csv(db_path: Path, csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn, csv_path.open("w", newline="", encoding="utf-8") as file:
        rows = conn.execute(
            """
            SELECT name, detail_slug, website_url, detail_url, description, last_seen_at
            FROM members
            ORDER BY name, detail_slug
            """
        ).fetchall()
        writer = csv.writer(file)
        writer.writerow(["name", "detail_slug", "website_url", "detail_url", "description", "last_seen_at"])
        writer.writerows(rows)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect LIFE Cooperative members.")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/life_members.sqlite"),
        help="SQLite database path.",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("outputs/life_members/life_members.csv"),
        help="CSV export path.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between requests in seconds.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    started_at = datetime.now(timezone.utc).isoformat()
    init_db(args.db)

    try:
        members = collect_members(args.delay)
    except (HTTPError, URLError, TimeoutError) as exc:
        print(f"Failed to collect members: {exc}", file=sys.stderr)
        return 1

    count = save_members(args.db, members, started_at)
    export_csv(args.db, args.csv)
    missing_websites = sum(1 for member in members if not member.website_url)

    print(f"Collected {count} LIFE Cooperative members.")
    print(f"Database: {args.db}")
    print(f"CSV: {args.csv}")
    if missing_websites:
        print(f"Members without extracted website: {missing_websites}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
