#!/usr/bin/env python3
"""Classify recent LIFE member news findings.

This script adds a lightweight review layer on top of `news_items`. If an
OpenAI API key is added later, this is the natural place to replace the local
triage rules with model calls. For now it stores transparent, conservative
classifications that keep source URLs auditable.
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse


GENERIC_PATHS = {
    "",
    "news",
    "nieuws",
    "blog",
    "resources",
    "events",
    "insights",
    "articles",
    "news-events",
}


@dataclass(frozen=True)
class Classification:
    is_newsworthy: int
    classification: str
    category: str
    summary_nl: str
    confidence: float
    review_reason: str


MANUAL_CLASSIFICATIONS = {
    "https://www.certe.nl/nieuws/hoogste-punt-bereikt-centraal-laboratorium-drachten": Classification(
        1,
        "newsworthy",
        "facilities",
        "Certe meldt dat het hoogste punt van het nieuwe centrale laboratorium in Drachten is bereikt.",
        0.82,
        "Concreet voortgangsnieuws over laboratoriuminfrastructuur.",
    ),
    "https://www.certe.nl/nieuws/nieuw-lid-raad-van-toezicht-certe": Classification(
        1,
        "newsworthy",
        "governance",
        "Certe kondigt een nieuw lid van de Raad van Toezicht aan.",
        0.78,
        "Bestuurlijke wijziging bij een LIFE-lid.",
    ),
    "https://www.certe.nl/nieuws/zelfmeten-een-fluitje-van-een-cent": Classification(
        1,
        "possibly_newsworthy",
        "patient_service",
        "Certe publiceert een item over zelfmeten voor patienten.",
        0.58,
        "Waarschijnlijk relevant als dienstverlening/communicatie, maar inhoudelijke impact moet worden nagelezen.",
    ),
    "https://www.ophtec.com/blog/ctrs-ringject-mdr-certified": Classification(
        1,
        "newsworthy",
        "certification",
        "Ophtec meldt dat de CTRs en Ringject MDR-gecertificeerd zijn.",
        0.9,
        "Regulatoire certificering is duidelijk nieuwswaardig in medtech.",
    ),
    "https://symeres.com/news/russell-thomas-chief-scientific-officer": Classification(
        1,
        "newsworthy",
        "leadership",
        "Symeres en Axxam benoemen Russell Thomas als Chief Scientific Officer voor hun gezamenlijke discovery-platform.",
        0.9,
        "Senior wetenschappelijke benoeming en strategische samenwerking.",
    ),
    "https://innocorepharma.com/news-events/webinar-replay-developing-long-acting-injectable-protein-therapeutics": Classification(
        1,
        "possibly_newsworthy",
        "webinar",
        "Innocore deelt een webinarreplay over long-acting injectable protein therapeutics.",
        0.62,
        "Inhoudelijk relevant, maar meer thought leadership dan bedrijfsnieuws.",
    ),
    "https://sttproducts.nl/nieuws-updates-en-ontwikkelingen-stt-products": Classification(
        1,
        "possibly_newsworthy",
        "company_update",
        "STT Products verwijst naar nieuws, updates en ontwikkelingen binnen het bedrijf.",
        0.52,
        "Artikelachtige URL, maar de scan kon nog geen specifiek nieuwsfeit isoleren.",
    ),
}


def classify(source_url: str, title: str, snippet: str) -> Classification:
    if source_url in MANUAL_CLASSIFICATIONS:
        return MANUAL_CLASSIFICATIONS[source_url]

    parsed = urlparse(source_url)
    path = parsed.path.strip("/").lower()
    parts = [part for part in path.split("/") if part]
    last = parts[-1] if parts else ""
    title_lower = title.lower()

    if path in GENERIC_PATHS or last in GENERIC_PATHS or not parts:
        return Classification(
            0,
            "noise",
            "overview_page",
            "Overzichtspagina of homepage; niet als afzonderlijk nieuwsitem behandelen.",
            0.86,
            "URL en titel wijzen op een indexpagina in plaats van een concreet artikel.",
        )

    if "event" in path or "webinar" in title_lower:
        return Classification(
            1,
            "possibly_newsworthy",
            "event",
            f"{title} lijkt een event- of webinaritem van het lid.",
            0.55,
            "Eventcontent kan relevant zijn, maar is minder hard bedrijfsnieuws.",
        )

    return Classification(
        1,
        "needs_review",
        "unknown",
        f"{title} is een artikelachtige pagina, maar vraagt menselijke controle.",
        0.45,
        "Artikelachtige URL zonder genoeg inhoudelijke extractie voor hoge zekerheid.",
    )


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS news_classifications (
            news_item_id INTEGER PRIMARY KEY,
            is_newsworthy INTEGER NOT NULL,
            classification TEXT NOT NULL,
            category TEXT NOT NULL,
            summary_nl TEXT NOT NULL,
            confidence REAL NOT NULL,
            review_reason TEXT NOT NULL,
            classified_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(news_item_id) REFERENCES news_items(id)
        )
        """
    )


def classify_recent(db_path: Path, csv_path: Path, since: str, until: str) -> tuple[int, int]:
    with sqlite3.connect(db_path) as conn:
        init_db(conn)
        rows = conn.execute(
            """
            SELECT id, member_name, item_date, relevance_score, title, source_url, reason, snippet
            FROM news_items
            WHERE item_date BETWEEN ? AND ?
            ORDER BY item_date DESC, relevance_score DESC, member_name
            """,
            (since, until),
        ).fetchall()

        output_rows = []
        for row in rows:
            news_item_id, member_name, item_date, relevance_score, title, source_url, reason, snippet = row
            result = classify(source_url, title, snippet)
            conn.execute(
                """
                INSERT INTO news_classifications (
                    news_item_id, is_newsworthy, classification, category,
                    summary_nl, confidence, review_reason, classified_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(news_item_id) DO UPDATE SET
                    is_newsworthy = excluded.is_newsworthy,
                    classification = excluded.classification,
                    category = excluded.category,
                    summary_nl = excluded.summary_nl,
                    confidence = excluded.confidence,
                    review_reason = excluded.review_reason,
                    classified_at = excluded.classified_at
                """,
                (
                    news_item_id,
                    result.is_newsworthy,
                    result.classification,
                    result.category,
                    result.summary_nl,
                    result.confidence,
                    result.review_reason,
                ),
            )
            output_rows.append(
                [
                    member_name,
                    item_date,
                    result.classification,
                    result.category,
                    result.confidence,
                    title,
                    source_url,
                    result.summary_nl,
                    result.review_reason,
                    relevance_score,
                    reason,
                ]
            )

        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with csv_path.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "member_name",
                    "item_date",
                    "classification",
                    "category",
                    "confidence",
                    "title",
                    "source_url",
                    "summary_nl",
                    "review_reason",
                    "heuristic_score",
                    "heuristic_reason",
                ]
            )
            writer.writerows(output_rows)

        newsworthy_count = sum(1 for row in output_rows if row[2] in {"newsworthy", "possibly_newsworthy"})
        return len(output_rows), newsworthy_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify recent LIFE news scan results.")
    parser.add_argument("--db", type=Path, default=Path("data/life_members.sqlite"))
    parser.add_argument("--csv", type=Path, default=Path("outputs/life_members/classified_recent_news.csv"))
    parser.add_argument("--days", type=int, default=61, help="Lookback window in days when --since is omitted.")
    parser.add_argument("--since", help="Start date in YYYY-MM-DD format. Defaults to today minus --days.")
    parser.add_argument("--until", help="End date in YYYY-MM-DD format. Defaults to today.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    today = datetime.now().date()
    since = args.since or (today - timedelta(days=args.days)).isoformat()
    until = args.until or today.isoformat()
    total, useful = classify_recent(args.db, args.csv, since, until)
    print(f"Classified {total} item(s); {useful} marked newsworthy or possibly newsworthy.")
    print(f"Window: {since} through {until}")
    print(f"CSV: {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
