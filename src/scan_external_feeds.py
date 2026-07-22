#!/usr/bin/env python3
"""Scan external RSS feeds for regional life sciences context."""

from __future__ import annotations

import argparse
import csv
import html
import re
import ssl
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET


USER_AGENT = "LIFE-member-monitor/0.3 (+external RSS context scan)"
KEYWORDS = {
    "ai": "AI/data",
    "artificial intelligence": "AI/data",
    "biotech": "biotech",
    "campus": "campus",
    "clinical": "clinical",
    "diagnostic": "diagnostics",
    "drug": "drug development",
    "health": "health",
    "healthtech": "healthtech",
    "innovation": "innovation",
    "lifescience": "life sciences",
    "life science": "life sciences",
    "medical": "medical",
    "medicine": "drug development",
    "nanopore": "bio-nanotech",
    "patient": "patient care",
    "pharma": "pharma",
    "protein": "protein research",
    "rug": "RUG",
    "umcg": "UMCG",
    "zorg": "health",
}


@dataclass(frozen=True)
class FeedSource:
    source_name: str
    feed_url: str
    source_type: str
    notes: str


@dataclass(frozen=True)
class FeedItem:
    source_name: str
    item_date: date
    title: str
    source_url: str
    summary: str
    matched_topics: str
    relevance_score: int


def normalize_space(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def parse_date(value: str) -> date | None:
    if not value:
        return None
    value = value.strip()
    try:
        return parsedate_to_datetime(value).date()
    except (TypeError, ValueError, IndexError):
        pass
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value[:25], fmt).date()
        except ValueError:
            continue
    return None


def load_sources(path: Path) -> list[FeedSource]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        return [
            FeedSource(
                source_name=(row.get("source_name") or "").strip(),
                feed_url=(row.get("feed_url") or "").strip(),
                source_type=(row.get("source_type") or "rss").strip(),
                notes=(row.get("notes") or "").strip(),
            )
            for row in reader
            if (row.get("source_name") or "").strip() and (row.get("feed_url") or "").strip()
        ]


def fetch_feed(url: str, timeout: int) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, */*"})
    try:
        with urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
            return response.read(2_000_000)
    except URLError as exc:
        if "CERTIFICATE_VERIFY_FAILED" not in str(exc):
            raise
        with urlopen(request, timeout=timeout, context=ssl._create_unverified_context()) as response:
            return response.read(2_000_000)


def child_text(element: ET.Element, names: list[str]) -> str:
    for name in names:
        found = element.find(name)
        if found is not None and found.text:
            return normalize_space(found.text)
    for child in element:
        tag = child.tag.split("}", 1)[-1]
        if tag in names and child.text:
            return normalize_space(child.text)
    return ""


def child_link(element: ET.Element) -> str:
    link = child_text(element, ["link"])
    if link:
        return link
    for child in element:
        tag = child.tag.split("}", 1)[-1]
        if tag == "link":
            href = child.attrib.get("href")
            if href:
                return href.strip()
    return ""


def score_item(title: str, summary: str) -> tuple[int, str]:
    text = f"{title} {summary}".lower()
    topics: list[str] = []
    for keyword, topic in KEYWORDS.items():
        if keyword in text and topic not in topics:
            topics.append(topic)
    score = min(100, 20 + len(topics) * 12)
    return score, ", ".join(topics)


def parse_feed(source: FeedSource, xml_bytes: bytes, cutoff: date, through_date: date) -> list[FeedItem]:
    root = ET.fromstring(xml_bytes)
    raw_items = root.findall(".//item")
    if not raw_items:
        raw_items = root.findall(".//{http://www.w3.org/2005/Atom}entry")

    items: list[FeedItem] = []
    for raw in raw_items:
        title = child_text(raw, ["title"])
        source_url = child_link(raw)
        published = child_text(raw, ["pubDate", "published", "updated", "date"])
        item_date = parse_date(published)
        if not item_date or not (cutoff <= item_date <= through_date):
            continue
        summary = child_text(raw, ["description", "summary", "content"])
        score, topics = score_item(title, summary)
        items.append(
            FeedItem(
                source_name=source.source_name,
                item_date=item_date,
                title=title,
                source_url=source_url,
                summary=summary[:600],
                matched_topics=topics,
                relevance_score=score,
            )
        )
    return items


def write_csv(items: list[FeedItem], csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "source_name",
                "item_date",
                "relevance_score",
                "matched_topics",
                "title",
                "source_url",
                "summary",
            ]
        )
        for item in sorted(items, key=lambda row: (row.item_date, row.relevance_score), reverse=True):
            writer.writerow(
                [
                    item.source_name,
                    item.item_date.isoformat(),
                    item.relevance_score,
                    item.matched_topics,
                    item.title,
                    item.source_url,
                    item.summary,
                ]
            )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan external RSS feeds for LIFE dashboard context.")
    parser.add_argument("--sources", type=Path, default=Path("data/external_feeds.csv"))
    parser.add_argument("--csv", type=Path, default=Path("outputs/life_members/external_news.csv"))
    parser.add_argument("--days", type=int, default=61)
    parser.add_argument("--since", help="Start date in YYYY-MM-DD format. Defaults to today minus --days.")
    parser.add_argument("--until", help="End date in YYYY-MM-DD format. Defaults to today.")
    parser.add_argument("--timeout", type=int, default=15)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    today = datetime.now(timezone.utc).date()
    cutoff = date.fromisoformat(args.since) if args.since else today - timedelta(days=args.days)
    through_date = date.fromisoformat(args.until) if args.until else today
    sources = load_sources(args.sources)

    items: list[FeedItem] = []
    for source in sources:
        if source.source_type.lower() != "rss":
            continue
        try:
            xml_bytes = fetch_feed(source.feed_url, args.timeout)
            found = parse_feed(source, xml_bytes, cutoff, through_date)
            print(f"{source.source_name}: {len(found)} item(s)")
            items.extend(found)
        except (HTTPError, URLError, TimeoutError, ET.ParseError) as exc:
            print(f"Failed to scan {source.source_name}: {exc}", file=sys.stderr)

    write_csv(items, args.csv)
    print(f"Saved {len(items)} external item(s).")
    print(f"CSV: {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
