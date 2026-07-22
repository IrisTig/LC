#!/usr/bin/env python3
"""Scan LIFE member websites for vacancy and careers signals."""

from __future__ import annotations

import argparse
import csv
import html
import re
import sqlite3
import ssl
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


USER_AGENT = "LIFE-member-monitor/0.4 (+careers scan)"
CAREERS_PATHS = (
    "/careers",
    "/career",
    "/jobs",
    "/vacancies",
    "/vacatures",
    "/werken-bij",
    "/werkenbij",
    "/join-us",
    "/work-with-us",
)
JOB_TITLE_KEYWORDS = (
    "engineer",
    "scientist",
    "researcher",
    "technician",
    "developer",
    "manager",
    "specialist",
    "analyst",
    "operator",
    "intern",
    "stage",
    "phd",
    "postdoc",
    "nurse",
    "assistant",
    "lead",
    "director",
    "officer",
    "consultant",
)
NON_JOB_LINES = {
    "careers",
    "jobs",
    "vacancies",
    "open positions",
    "current vacancies",
    "see jobs",
    "apply",
    "contact",
    "privacy policy",
    "terms & conditions",
}


@dataclass(frozen=True)
class Member:
    name: str
    website_url: str


@dataclass(frozen=True)
class JobItem:
    member_name: str
    job_title: str
    location: str
    hours: str
    deadline: str
    source_url: str
    detected_at: str
    signal_summary: str


class TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if tag in {"br", "p", "div", "section", "article", "li", "h1", "h2", "h3", "h4", "h5"}:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if tag in {"p", "div", "section", "article", "li", "h1", "h2", "h3", "h4", "h5"}:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._parts.append(data)

    def text(self) -> str:
        cleaned = re.sub(r"[ \t\r\f\v]+", " ", "".join(self._parts))
        cleaned = re.sub(r"\n\s*\n+", "\n", cleaned)
        return html.unescape(cleaned).strip()


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def normalize_url(url: str, base_url: str | None = None) -> str:
    url = html.unescape(url).strip()
    if url.startswith("//"):
        return "https:" + url
    if base_url:
        return urljoin(base_url, url).rstrip("/")
    if re.match(r"^www\.", url, flags=re.IGNORECASE):
        return "https://" + url
    if not re.match(r"^https?://", url, flags=re.IGNORECASE):
        return "https://" + url
    return url.rstrip("/")


def fetch_html(url: str, timeout: int) -> str | None:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*;q=0.8"})
    try:
        with urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return None
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read(1_500_000).decode(charset, errors="replace")
    except URLError as exc:
        if "CERTIFICATE_VERIFY_FAILED" not in str(exc):
            return None
        try:
            with urlopen(request, timeout=timeout, context=ssl._create_unverified_context()) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read(1_500_000).decode(charset, errors="replace")
        except (HTTPError, URLError, TimeoutError, ssl.SSLError, ValueError):
            return None
    except (HTTPError, TimeoutError, ssl.SSLError, ValueError):
        return None


def extract_text(page_html: str) -> str:
    parser = TextParser()
    parser.feed(page_html)
    return parser.text()


def load_members(db_path: Path) -> list[Member]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT name, website_url
            FROM members
            WHERE website_url IS NOT NULL AND website_url != ''
            ORDER BY name, detail_slug
            """
        ).fetchall()
    return [Member(name=row[0], website_url=row[1]) for row in rows]


def candidate_careers_urls(website_url: str) -> list[str]:
    root = normalize_url(website_url)
    parsed = urlparse(root)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    urls = [normalize_url(path, origin) for path in CAREERS_PATHS]
    if any(part in parsed.path.lower() for part in ("career", "vacature", "job")):
        urls.insert(0, root)
    return list(dict.fromkeys(urls))


def is_probable_job_title(line: str) -> bool:
    clean = normalize_space(line)
    lower = clean.lower().strip(":-")
    if not clean or lower in NON_JOB_LINES:
        return False
    if len(clean) < 5 or len(clean) > 90:
        return False
    if re.search(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b", clean):
        return False
    if any(keyword in lower for keyword in JOB_TITLE_KEYWORDS):
        return True
    return bool(re.search(r"\b(scientific|research|process|quality|regulatory|clinical|product|software)\b", lower))


def find_detail(patterns: list[str], lines: list[str], start_index: int) -> str:
    for line in lines[start_index + 1 : start_index + 8]:
        lower = line.lower()
        if any(re.search(pattern, lower) for pattern in patterns):
            return normalize_space(line)
    return ""


def extract_deadline(lines: list[str], start_index: int) -> str:
    patterns = [
        r"apply before",
        r"deadline",
        r"closing date",
        r"reageer voor",
        r"solliciteer voor",
        r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b",
    ]
    return find_detail(patterns, lines, start_index)


def extract_location(lines: list[str], start_index: int) -> str:
    patterns = [r"groningen", r"\(nl\)", r"netherlands", r"nederland", r"hybrid", r"remote", r"assen", r"drachten"]
    return find_detail(patterns, lines, start_index)


def extract_hours(lines: list[str], start_index: int) -> str:
    patterns = [r"\b\d{1,2}\s*[-–]\s*\d{1,2}\s*h", r"\b\d{1,2}\s*h", r"full.?time", r"part.?time", r"p/w", r"per week"]
    return find_detail(patterns, lines, start_index)


def extract_jobs(member: Member, page_url: str, page_html: str) -> list[JobItem]:
    text = extract_text(page_html)
    lower_text = text.lower()
    if not any(keyword in lower_text for keyword in ("vacanc", "career", "job", "open position", "sollicit", "werken bij")):
        return []

    lines = [normalize_space(line) for line in text.splitlines() if normalize_space(line)]
    now = datetime.now(timezone.utc).isoformat()
    jobs: list[JobItem] = []
    seen_titles: set[str] = set()

    for index, line in enumerate(lines):
        if not is_probable_job_title(line):
            continue
        title_key = line.lower()
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        location = extract_location(lines, index)
        hours = extract_hours(lines, index)
        deadline = extract_deadline(lines, index)
        if not any([location, hours, deadline]):
            continue
        summary_parts = [part for part in [location, hours, deadline] if part]
        jobs.append(
            JobItem(
                member_name=member.name,
                job_title=line,
                location=location,
                hours=hours,
                deadline=deadline,
                source_url=page_url,
                detected_at=now,
                signal_summary=" | ".join(summary_parts) if summary_parts else "Vacature of carrierekans gevonden.",
            )
        )
    return jobs


def scan_member_jobs(member: Member, timeout: int) -> list[JobItem]:
    for url in candidate_careers_urls(member.website_url):
        page_html = fetch_html(url, timeout)
        if not page_html:
            continue
        jobs = extract_jobs(member, url, page_html)
        if jobs:
            return jobs
    return []


def write_csv(jobs: list[JobItem], csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "member_name",
                "job_title",
                "location",
                "hours",
                "deadline",
                "source_url",
                "detected_at",
                "signal_summary",
            ]
        )
        for job in sorted(jobs, key=lambda item: (item.member_name.lower(), item.job_title.lower())):
            writer.writerow(
                [
                    job.member_name,
                    job.job_title,
                    job.location,
                    job.hours,
                    job.deadline,
                    job.source_url,
                    job.detected_at,
                    job.signal_summary,
                ]
            )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan LIFE member websites for vacancies.")
    parser.add_argument("--db", type=Path, default=Path("data/life_members.sqlite"))
    parser.add_argument("--csv", type=Path, default=Path("outputs/life_members/member_jobs.csv"))
    parser.add_argument("--timeout", type=int, default=10)
    parser.add_argument("--member", help="Optional member name filter for testing.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if not args.db.exists():
        print(f"Database not found: {args.db}", file=sys.stderr)
        return 1

    members = load_members(args.db)
    if args.member:
        members = [member for member in members if args.member.lower() in member.name.lower()]

    all_jobs: list[JobItem] = []
    for index, member in enumerate(members, start=1):
        print(f"[{index:02d}/{len(members):02d}] {member.name}")
        jobs = scan_member_jobs(member, args.timeout)
        print(f"  found {len(jobs)} job(s)")
        all_jobs.extend(jobs)

    write_csv(all_jobs, args.csv)
    print(f"Saved {len(all_jobs)} job(s).")
    print(f"CSV: {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
