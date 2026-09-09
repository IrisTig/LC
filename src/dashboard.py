#!/usr/bin/env python3
"""Streamlit dashboard for LIFE Cooperative communication teams."""

from __future__ import annotations

import html as html_lib
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
import streamlit as st


OUTPUT_DIR = Path("outputs/life_members")
DASHBOARD_DATA_DIR = Path("dashboard_data")
CLASSIFIED_NEWS_PATHS = [
    DASHBOARD_DATA_DIR / "classified_recent_news.csv",
    OUTPUT_DIR / "classified_recent_news.csv",
]
RECENT_NEWS_PATHS = [
    DASHBOARD_DATA_DIR / "recent_news.csv",
    OUTPUT_DIR / "recent_news.csv",
]
MEMBERS_PATHS = [
    DASHBOARD_DATA_DIR / "life_members.csv",
    OUTPUT_DIR / "life_members.csv",
]
EXTERNAL_NEWS_PATHS = [
    DASHBOARD_DATA_DIR / "external_news.csv",
    OUTPUT_DIR / "external_news.csv",
]
MEMBER_JOBS_PATHS = [
    DASHBOARD_DATA_DIR / "member_jobs.csv",
    OUTPUT_DIR / "member_jobs.csv",
]

NEWSWORTHY = ["newsworthy", "possibly_newsworthy", "needs_review"]
NOISE = ["noise"]

CLASS_LABELS = {
    "newsworthy": "Nieuwswaardig",
    "possibly_newsworthy": "Mogelijk interessant",
    "needs_review": "Checken",
    "noise": "Ruis",
}

CATEGORY_LABELS = {
    "certification": "Certificering",
    "clinical": "Klinisch",
    "company_update": "Bedrijfsupdate",
    "event": "Event",
    "facilities": "Faciliteiten",
    "funding": "Financiering",
    "governance": "Bestuur",
    "leadership": "Leiderschap",
    "overview_page": "Overzichtspagina",
    "partnership": "Samenwerking",
    "patient_service": "Patientenzorg",
    "product": "Product",
    "research": "Onderzoek",
    "unknown": "Onbekend",
    "webinar": "Webinar",
}

TREND_SIGNALS = [
    {
        "theme": "Lifelines zoekt nieuwe deelnemers",
        "angle": "Lifelines nodigt voor het eerst in twintig jaar nieuwe deelnemers uit, met steun vanuit Nationaal Programma Groningen.",
        "newsletter_use": "Sterk haakje voor onderzoek, preventie, data en maatschappelijke impact in Noord-Nederland.",
        "source": "LIFE Cooperative nieuws",
        "url": "https://lifecooperative.nl/",
    },
    {
        "theme": "Innovation Award 2026",
        "angle": "Vijf innovaties maken kans op de LIFE Science Innovation Award: Flux Robotics, Limosa Immunodiagnostics, SPCTR, MimeCure en GlycanScan International.",
        "newsletter_use": "Gebruik als leden-/ecosysteemverhaal richting event, jury, partners en regionale zichtbaarheid.",
        "source": "LIFE Cooperative nieuws",
        "url": "https://lifecooperative.nl/",
    },
    {
        "theme": "Nieuwe SDI-subsidieronde",
        "angle": "ZonMw opent naar verwachting de laatste oproep binnen PharmaNL Shared Development Infrastructure.",
        "newsletter_use": "Relevant voor leden die werken aan ontwikkeling, opschaling en productie van innovatieve geneesmiddelen.",
        "source": "LIFE Cooperative nieuws",
        "url": "https://lifecooperative.nl/",
    },
    {
        "theme": "Van visie naar uitvoering",
        "angle": "Regionale life sciences willen zichtbare economische impact laten zien.",
        "newsletter_use": "Gebruik dit als kapstok voor ledenverhalen over groei, samenwerking en valorisatie.",
        "source": "LIFE Science Conference 2026",
        "url": "https://campusgroningen.nl/nieuws/life-science-conference-2026",
    },
    {
        "theme": "HealthTech als arbeidsmarktverhaal",
        "angle": "Groningen profileert healthtech landelijk richting technisch talent.",
        "newsletter_use": "Koppel vacature-, stage- en talentverhalen van leden aan dit bredere narratief.",
        "source": "Provincie Groningen",
        "url": "https://www.provinciegroningen.nl/actueel/nieuws/nieuwsartikel/groningen-lanceert-landelijke-healthtech-arbeidsmarktcampagne/",
    },
    {
        "theme": "Campus als innovatie-infrastructuur",
        "angle": "Laboratoria, campusruimte en nabijheid van UMCG/RUG blijven een sterk regionaal voordeel.",
        "newsletter_use": "Maak korte items over faciliteiten, labs, verhuizingen en gedeelde infrastructuur.",
        "source": "Campus Groningen",
        "url": "https://campusgroningen.nl/en/news",
    },
    {
        "theme": "Drug development en advanced delivery",
        "angle": "Groningen laat activiteit zien rond innovatieve geneesmiddelen en toedieningsvormen.",
        "newsletter_use": "Bundel ledennieuws over therapieontwikkeling, delivery, trials en translatie.",
        "source": "Campus Groningen",
        "url": "https://campusgroningen.nl/en/news/groningen-hosts-the-dutch-medicines-winter-afternoon-full-of-innovation",
    },
    {
        "theme": "AI, imaging en bio-nanotechnologie",
        "angle": "Onderzoeksnieuws rond AI, medische beeldvorming en nanopore/protein-analyse sluit aan op ledeninnovatie.",
        "newsletter_use": "Gebruik dit voor rubrieken rond technologie, data en nieuwe diagnostiek.",
        "source": "University of Groningen",
        "url": "https://www.rug.nl/fse/news/news-archive?lang=en",
    },
    {
        "theme": "Breed RUG-nieuws als context",
        "angle": "De algemene RUG-nieuwspagina bundelt universiteitsbreed nieuws, dossiers, events en RSS.",
        "newsletter_use": "Gebruik dit als vroege signalering voor onderzoek, talent, maatschappelijke impact en mogelijke koppelingen met leden.",
        "source": "RUG latest news",
        "url": "https://www.rug.nl/about-ug/latest-news/news/",
    },
]


st.set_page_config(
    page_title="LIFE Cooperative redactie-dashboard",
    page_icon="LC",
    layout="wide",
)


st.markdown(
    """
    <style>
    :root {
        --life-blue: #009fe3;
        --life-blue-dark: #14577a;
        --life-teal: #40c7bf;
        --life-mint: #dff7f3;
        --life-ink: #173244;
        --life-muted: #647887;
        --life-line: rgba(20, 87, 122, .16);
        --life-soft: rgba(0, 159, 227, .10);
        --life-paper: #f4fbfd;
        --life-white: #ffffff;
    }
    .stApp {
        background:
            radial-gradient(circle at 92% 8%, rgba(64, 199, 191, .18), transparent 26rem),
            linear-gradient(180deg, #ffffff 0%, var(--life-paper) 42%, #eef8fb 100%);
        color: var(--life-ink);
    }
    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 4rem;
        max-width: 1440px;
    }
    [data-testid="stSidebar"] {
        background: #eaf7fb;
        border-right: 1px solid var(--life-line);
    }
    header[data-testid="stHeader"] {
        background: transparent;
    }
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    #MainMenu {
        display: none;
    }
    [data-testid="stSidebar"] * {
        color: var(--life-ink);
    }
    [data-testid="stSidebar"] [data-baseweb="select"],
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section,
    [data-testid="stSidebar"] input {
        background: var(--life-white);
        border-radius: 8px;
    }
    .lc-nav {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1.25rem;
        width: 100%;
        padding: 1.05rem 1.35rem;
        margin: .25rem 0 2.2rem 0;
        background: var(--life-white);
        border-radius: 999px;
        box-shadow: 0 14px 34px rgba(20, 87, 122, .10);
    }
    .lc-brand {
        display: flex;
        align-items: center;
        gap: .58rem;
        min-width: 220px;
    }
    .lc-mark {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 3.25rem;
        height: 2.2rem;
        border-radius: 999px;
        background: #d70846;
        color: #fff;
        font-weight: 900;
        font-size: 1.05rem;
        font-style: italic;
        letter-spacing: -.04em;
        transform: skew(-8deg);
    }
    .lc-wordmark {
        display: flex;
        flex-direction: column;
        line-height: 1;
    }
    .lc-wordmark strong {
        color: #18385a;
        font-size: 1.3rem;
        letter-spacing: -.02em;
    }
    .lc-wordmark span {
        color: var(--life-muted);
        font-size: .62rem;
        margin-top: .17rem;
    }
    .lc-nav-links {
        display: flex;
        align-items: center;
        gap: 2.2rem;
        color: #18385a;
        font-weight: 600;
        font-size: .98rem;
    }
    .lc-nav-cta {
        border-radius: 999px;
        background: #d70846;
        color: #fff;
        padding: .68rem 1.15rem;
        font-weight: 800;
        white-space: nowrap;
    }
    .life-hero {
        display: grid;
        grid-template-columns: minmax(0, 1.25fr) minmax(260px, .75fr);
        gap: 2rem;
        align-items: end;
        padding: 2.35rem 0 2.1rem 0;
        border-bottom: 1px solid var(--life-line);
        margin-bottom: 1.35rem;
    }
    .life-kicker {
        color: var(--life-blue-dark);
        font-weight: 800;
        letter-spacing: .09em;
        text-transform: uppercase;
        font-size: .78rem;
        margin-bottom: .6rem;
    }
    .life-hero h1 {
        color: var(--life-ink);
        font-size: clamp(2.45rem, 5.2vw, 5.4rem);
        line-height: .96;
        margin: 0;
        letter-spacing: 0;
        max-width: 980px;
    }
    .life-subtitle {
        max-width: 760px;
        color: var(--life-muted);
        font-size: 1.12rem;
        margin-top: 1rem;
    }
    .life-hero-panel {
        background: var(--life-mint);
        border-radius: 8px;
        padding: 1.25rem 1.35rem;
        border: 1px solid rgba(64, 199, 191, .36);
    }
    .life-hero-panel strong {
        display: block;
        color: var(--life-blue-dark);
        font-size: .92rem;
        margin-bottom: .45rem;
    }
    .life-hero-panel span {
        color: var(--life-ink);
        font-size: .98rem;
    }
    .metric-card {
        border: 1px solid var(--life-line);
        background: var(--life-white);
        box-shadow: 0 18px 38px rgba(20, 87, 122, .08);
        padding: 1.1rem 1.15rem;
        border-radius: 8px;
        min-height: 122px;
    }
    .metric-label {
        color: var(--life-muted);
        font-size: .86rem;
        margin-bottom: .35rem;
    }
    .metric-value {
        color: var(--life-blue-dark);
        font-size: 2.2rem;
        font-weight: 700;
        line-height: 1;
    }
    .metric-note {
        margin-top: .45rem;
        color: var(--life-muted);
        font-size: .82rem;
    }
    .section-title {
        margin: 1.4rem 0 .5rem 0;
        font-size: 1.35rem;
        font-weight: 700;
        color: var(--life-ink);
    }
    .story-card {
        border: 1px solid var(--life-line);
        border-left: 5px solid var(--life-blue);
        border-radius: 8px;
        padding: 1.05rem 1.15rem;
        margin-bottom: .9rem;
        background: var(--life-white);
        box-shadow: 0 14px 28px rgba(20, 87, 122, .06);
    }
    .story-meta {
        color: var(--life-blue-dark);
        font-size: .82rem;
        font-weight: 700;
        margin-bottom: .25rem;
    }
    .story-title {
        color: var(--life-ink);
        font-weight: 700;
        font-size: 1.08rem;
        margin-bottom: .28rem;
    }
    .story-summary {
        color: var(--life-muted);
        margin-bottom: .45rem;
    }
    .pill {
        display: inline-block;
        border: 1px solid rgba(0, 159, 227, .26);
        background: rgba(0, 159, 227, .08);
        border-radius: 999px;
        padding: .18rem .54rem;
        margin-right: .25rem;
        color: var(--life-blue-dark);
        font-size: .76rem;
    }
    .copy-box {
        border: 1px dashed rgba(0, 159, 227, .42);
        background: #eef9fd;
        padding: .9rem 1rem;
        border-radius: 8px;
        white-space: pre-wrap;
        color: var(--life-ink);
    }
    .trend-card {
        border: 1px solid var(--life-line);
        border-radius: 8px;
        padding: 1rem;
        height: 100%;
        background: var(--life-white);
        box-shadow: 0 14px 28px rgba(20, 87, 122, .05);
    }
    .trend-card h4 {
        color: var(--life-blue-dark);
        margin-top: 0;
        margin-bottom: .4rem;
    }
    .coverage-good {
        color: #13795b;
        font-weight: 700;
    }
    .coverage-missing {
        color: #b42318;
        font-weight: 700;
    }
    div[data-testid="stMetric"] {
        background: var(--life-white);
        border: 1px solid var(--life-line);
        border-radius: 8px;
        padding: .75rem .9rem;
        box-shadow: 0 12px 24px rgba(20, 87, 122, .05);
    }
    h1, h2, h3, h4, h5, h6,
    .stMarkdown, .stText, label, p {
        color: var(--life-ink);
    }
    .stCaptionContainer, [data-testid="stCaptionContainer"] {
        color: var(--life-muted);
    }
    button[kind="secondary"], a[data-testid="stLinkButton"] {
        border-radius: 999px;
        border-color: var(--life-blue) !important;
        color: var(--life-blue-dark) !important;
        background: #ffffff !important;
    }
    button[kind="secondary"]:hover, a[data-testid="stLinkButton"]:hover {
        border-color: var(--life-blue-dark) !important;
        color: #ffffff !important;
        background: var(--life-blue-dark) !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: .35rem;
        border-bottom: 1px solid var(--life-line);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 999px 999px 0 0;
        color: var(--life-blue-dark);
        font-weight: 700;
    }
    .stTabs [aria-selected="true"] {
        background: var(--life-blue);
        color: #ffffff;
    }
    .light-table-wrap {
        width: 100%;
        overflow-x: auto;
        border: 1px solid var(--life-line);
        border-radius: 8px;
        background: var(--life-white);
        box-shadow: 0 14px 28px rgba(20, 87, 122, .05);
    }
    .light-table {
        width: 100%;
        border-collapse: collapse;
        font-size: .9rem;
    }
    .light-table th {
        background: #eaf7fb;
        color: var(--life-blue-dark);
        font-weight: 800;
        text-align: left;
        padding: .72rem .8rem;
        border-bottom: 1px solid var(--life-line);
        white-space: nowrap;
    }
    .light-table td {
        color: var(--life-ink);
        padding: .68rem .8rem;
        border-bottom: 1px solid rgba(20, 87, 122, .10);
        vertical-align: top;
        max-width: 520px;
    }
    .light-table tr:nth-child(even) td {
        background: #f8fcfe;
    }
    .light-table tr:last-child td {
        border-bottom: 0;
    }
    .light-table a {
        color: var(--life-blue-dark);
        font-weight: 700;
        text-decoration: none;
    }
    .light-table a:hover {
        text-decoration: underline;
    }
    @media (max-width: 760px) {
        .lc-nav {
            align-items: flex-start;
            border-radius: 18px;
            flex-direction: column;
        }
        .lc-nav-links {
            gap: .8rem;
            flex-wrap: wrap;
        }
        .life-hero {
            grid-template-columns: 1fr;
            gap: 1rem;
            padding-top: 1.25rem;
        }
        .life-hero h1 {
            font-size: 2.5rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def read_csv(source) -> pd.DataFrame:
    if source is None:
        return pd.DataFrame()
    return pd.read_csv(source)


def load_default_or_upload(label: str, default_paths: list[Path]) -> pd.DataFrame:
    uploaded = st.sidebar.file_uploader(label, type=["csv"])
    if uploaded is not None:
        return read_csv(uploaded)
    for default_path in default_paths:
        if default_path.exists():
            return read_csv(default_path)
    return pd.DataFrame()


def clean_news(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    if "item_date" in df.columns:
        df["item_date"] = pd.to_datetime(df["item_date"], errors="coerce")
    for column in ["confidence", "heuristic_score"]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    for column in ["classification", "category", "member_name", "title", "summary_nl"]:
        if column in df.columns:
            df[column] = df[column].fillna("").astype(str)
    return df


def clean_external_news(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    if "item_date" in df.columns:
        df["item_date"] = pd.to_datetime(df["item_date"], errors="coerce")
    if "relevance_score" in df.columns:
        df["relevance_score"] = pd.to_numeric(df["relevance_score"], errors="coerce")
    for column in ["source_name", "matched_topics", "title", "summary"]:
        if column in df.columns:
            df[column] = df[column].fillna("").astype(str)
    return df


def clean_jobs(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    if "detected_at" in df.columns:
        df["detected_at"] = pd.to_datetime(df["detected_at"], errors="coerce")
    for column in ["member_name", "job_title", "location", "hours", "deadline", "signal_summary"]:
        if column in df.columns:
            df[column] = df[column].fillna("").astype(str)
    return df


def display_class(value: str) -> str:
    return CLASS_LABELS.get(value, value.replace("_", " ").title())


def display_category(value: str) -> str:
    return CATEGORY_LABELS.get(value, value.replace("_", " ").title())


def render_lc_nav() -> None:
    st.markdown(
        """
        <div class="lc-nav">
            <div class="lc-brand">
                <div class="lc-mark">LIFE</div>
                <div class="lc-wordmark">
                    <strong>Cooperative</strong>
                    <span>there's more to healthy ageing</span>
                </div>
            </div>
            <div class="lc-nav-links">
                <span>Programs</span>
                <span>Members</span>
                <span>Events</span>
                <span>News</span>
                <span>About us</span>
            </div>
            <div class="lc-nav-cta">Redactie</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def format_cell(value) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return ""
        return value.date().isoformat()
    return str(value)


def render_light_table(
    df: pd.DataFrame,
    columns: list[str],
    labels: dict[str, str] | None = None,
    link_columns: set[str] | None = None,
    max_rows: int = 80,
) -> None:
    labels = labels or {}
    link_columns = link_columns or set()
    if df.empty or not columns:
        st.info("Geen rijen om te tonen.")
        return

    visible = df[columns].head(max_rows).copy()
    header = "".join(f"<th>{html_lib.escape(labels.get(col, col))}</th>" for col in columns)
    rows: list[str] = []
    for _, row in visible.iterrows():
        cells: list[str] = []
        for col in columns:
            value = format_cell(row.get(col, ""))
            if col in link_columns and value:
                safe_url = html_lib.escape(value, quote=True)
                cells.append(f'<td><a href="{safe_url}" target="_blank" rel="noopener">Open link</a></td>')
            else:
                cells.append(f"<td>{html_lib.escape(value)}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")

    st.markdown(
        f"""
        <div class="light-table-wrap">
            <table class="light-table">
                <thead><tr>{header}</tr></thead>
                <tbody>{''.join(rows)}</tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if len(df) > max_rows:
        st.caption(f"Toont {max_rows} van {len(df)} rijen.")


def useful_news(news: pd.DataFrame) -> pd.DataFrame:
    if news.empty or "classification" not in news.columns:
        return news.iloc[0:0].copy()
    useful = news[news["classification"].isin(NEWSWORTHY)].copy()
    sort_cols = [col for col in ["item_date", "confidence"] if col in useful.columns]
    if sort_cols:
        useful = useful.sort_values(sort_cols, ascending=False)
    return useful


def apply_filters(news: pd.DataFrame) -> pd.DataFrame:
    if news.empty:
        return news

    filtered = news.copy()
    st.sidebar.markdown("### Filters")

    if "classification" in filtered.columns:
        values = sorted(filtered["classification"].dropna().unique())
        default = [value for value in values if value not in NOISE] or values
        selected = st.sidebar.multiselect(
            "Redactiestatus",
            values,
            default=default,
            format_func=display_class,
        )
        filtered = filtered[filtered["classification"].isin(selected)]

    if "category" in filtered.columns:
        values = sorted(filtered["category"].dropna().unique())
        selected = st.sidebar.multiselect(
            "Thema",
            values,
            default=values,
            format_func=display_category,
        )
        filtered = filtered[filtered["category"].isin(selected)]

    if "member_name" in filtered.columns:
        values = sorted(filtered["member_name"].dropna().unique())
        selected = st.sidebar.multiselect("Lid", values, default=values)
        filtered = filtered[filtered["member_name"].isin(selected)]

    if "item_date" in filtered.columns and filtered["item_date"].notna().any():
        min_date = filtered["item_date"].min().date()
        max_date = filtered["item_date"].max().date()
        selected_dates = st.sidebar.date_input(
            "Periode",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
        if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
            start_date, end_date = selected_dates
            filtered = filtered[
                (filtered["item_date"].dt.date >= start_date)
                & (filtered["item_date"].dt.date <= end_date)
            ]

    search = st.sidebar.text_input("Zoek in titel/samenvatting")
    if search:
        haystack_cols = [col for col in ["title", "summary_nl", "member_name", "category"] if col in filtered.columns]
        mask = pd.Series(False, index=filtered.index)
        for col in haystack_cols:
            mask = mask | filtered[col].astype(str).str.contains(search, case=False, na=False)
        filtered = filtered[mask]

    return filtered


def render_hero(news: pd.DataFrame, members: pd.DataFrame) -> None:
    useful = useful_news(news)
    total_members = len(members) if not members.empty else 0
    followed_members = (
        int(members["website_url"].notna().sum())
        if not members.empty and "website_url" in members.columns
        else 0
    )
    coverage = round((followed_members / total_members) * 100) if total_members else 0

    st.markdown(
        """
        <div class="life-hero">
            <div>
                <div class="life-kicker">LIFE Cooperative · Redactie-dashboard</div>
                <h1>Nieuws en signalen uit Life Science, Health en MedTech.</h1>
                <div class="life-subtitle">
                    Voor het communicatieteam: vind ledennieuws, vacatures, regionale haakjes en concrete input voor nieuwsbrieven.
                </div>
            </div>
            <div class="life-hero-panel">
                <strong>Impact van echte verbinding</strong>
                <span>
                    Dagelijks zicht op leden, trends en kansen om de noordelijke Life Sciences & Health-sector sterker te vertellen.
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(4)
    metrics = [
        ("Leden", total_members, "Totaal in de monitor"),
        ("Websites gevolgd", followed_members, f"{coverage}% coverage"),
        ("Items gevonden", len(news), "Binnen geselecteerde dataset"),
        ("Nieuwsbriefkandidaten", len(useful), "Nieuwswaardig, mogelijk of checken"),
    ]
    for col, (label, value, note) in zip(cols, metrics):
        col.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
                <div class="metric-note">{note}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_story_cards(news: pd.DataFrame, limit: int = 8) -> None:
    if news.empty:
        st.info("Geen nieuwsbriefkandidaten in de huidige selectie.")
        return

    for _, row in news.head(limit).iterrows():
        date_value = row.get("item_date")
        date_text = date_value.date().isoformat() if pd.notna(date_value) else "Geen datum"
        member = row.get("member_name", "Onbekend lid")
        title = row.get("title", "Zonder titel")
        summary = row.get("summary_nl", "")
        category = display_category(row.get("category", "unknown"))
        classification = display_class(row.get("classification", ""))
        source = row.get("source_url", "")
        reason = row.get("review_reason", "")

        st.markdown(
            f"""
            <div class="story-card">
                <div class="story-meta">{date_text} · {member}</div>
                <div class="story-title">{title}</div>
                <div class="story-summary">{summary}</div>
                <span class="pill">{classification}</span>
                <span class="pill">{category}</span>
                <span class="pill">{reason}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if source:
            st.link_button("Open bron", source)


def render_newsletter_copy(news: pd.DataFrame) -> None:
    if news.empty:
        return
    lines = ["Concept nieuwsbriefselectie", ""]
    for _, row in news.head(6).iterrows():
        date_value = row.get("item_date")
        date_text = date_value.date().isoformat() if pd.notna(date_value) else ""
        member = row.get("member_name", "Onbekend lid")
        title = row.get("title", "Zonder titel")
        summary = row.get("summary_nl", "")
        source = row.get("source_url", "")
        lines.append(f"- {member} ({date_text}): {title}")
        if summary:
            lines.append(f"  {summary}")
        if source:
            lines.append(f"  Bron: {source}")
        lines.append("")
    st.markdown('<div class="copy-box">' + "\n".join(lines) + "</div>", unsafe_allow_html=True)


def render_editorial_view(news: pd.DataFrame) -> None:
    useful = useful_news(news)
    st.markdown('<div class="section-title">Nieuwsbriefselectie</div>', unsafe_allow_html=True)
    left, right = st.columns([1.35, 1])
    with left:
        render_story_cards(useful)
    with right:
        st.markdown("#### Kopij om mee te starten")
        st.caption("Gebruik dit als ruwe selectie; check altijd de bron voordat je publiceert.")
        render_newsletter_copy(useful)


def render_analytics(news: pd.DataFrame) -> None:
    if news.empty:
        st.info("Geen data om te analyseren.")
        return

    left, right = st.columns(2)
    if "item_date" in news.columns and news["item_date"].notna().any():
        monthly = (
            news.assign(month=news["item_date"].dt.to_period("M").astype(str))
            .groupby("month", as_index=False)
            .size()
            .rename(columns={"size": "items"})
        )
        left.subheader("Nieuwsritme per maand")
        left.bar_chart(monthly, x="month", y="items", use_container_width=True)

    if "category" in news.columns:
        categories = (
            news.groupby("category", as_index=False)
            .size()
            .rename(columns={"size": "items"})
            .sort_values("items", ascending=False)
        )
        categories["theme"] = categories["category"].map(display_category)
        right.subheader("Thema's")
        right.bar_chart(categories, x="theme", y="items", use_container_width=True)

    left, right = st.columns(2)
    if "member_name" in news.columns:
        members = (
            news.groupby("member_name", as_index=False)
            .size()
            .rename(columns={"size": "items"})
            .sort_values("items", ascending=False)
            .head(15)
        )
        left.subheader("Meest zichtbare leden")
        left.bar_chart(members, x="member_name", y="items", use_container_width=True)

    if "classification" in news.columns:
        classes = (
            news.groupby("classification", as_index=False)
            .size()
            .rename(columns={"size": "items"})
            .sort_values("items", ascending=False)
        )
        classes["status"] = classes["classification"].map(display_class)
        right.subheader("Redactiestatus")
        right.bar_chart(classes, x="status", y="items", use_container_width=True)


def render_coverage(members: pd.DataFrame) -> None:
    if members.empty:
        st.info("Upload life_members.csv om coverage te zien.")
        return

    members = members.copy()
    members["has_website"] = members.get("website_url", "").fillna("").astype(str).str.strip().ne("")
    total = len(members)
    followed = int(members["has_website"].sum())
    missing = total - followed
    col1, col2, col3 = st.columns(3)
    col1.metric("Leden totaal", total)
    col2.metric("Met website", followed)
    col3.metric("Nog zonder website", missing)

    st.markdown("#### Nog aan te vullen websites")
    missing_df = members[~members["has_website"]].copy()
    if missing_df.empty:
        st.success("Alle leden hebben een website in de monitor.")
    else:
        columns = [col for col in ["name", "detail_url", "description"] if col in missing_df.columns]
        render_light_table(
            missing_df,
            columns,
            labels={"name": "Lid", "detail_url": "LIFE profiel", "description": "Omschrijving"},
            link_columns={"detail_url"},
        )


def render_trends() -> None:
    st.markdown('<div class="section-title">Trendradar Noord-Nederland</div>', unsafe_allow_html=True)
    st.caption("Redactionele haakjes op basis van externe bronnen. Gebruik ze als context bij ledennieuws.")
    rows = [TREND_SIGNALS[i : i + 2] for i in range(0, len(TREND_SIGNALS), 2)]
    for row in rows:
        cols = st.columns(2)
        for col, trend in zip(cols, row):
            with col:
                st.markdown(
                    f"""
                    <div class="trend-card">
                        <h4>{trend["theme"]}</h4>
                        <p>{trend["angle"]}</p>
                        <p><strong>Nieuwsbriefhaakje:</strong> {trend["newsletter_use"]}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.link_button(trend["source"], trend["url"])

    st.markdown("#### Dagblad van het Noorden")
    st.write(
        "DvhN kan relevant zijn voor regionale zichtbaarheid, maar automatische scraping is meestal niet ideaal "
        "door login/paywall en gebruiksvoorwaarden. Voor nu: gebruik gerichte zoeklinks en voeg interessante "
        "artikelen handmatig toe aan je nieuwsbriefselectie."
    )
    queries = [
        "LIFE Cooperative Groningen",
        "life sciences Groningen",
        "healthtech Groningen",
        "UMCG startup Groningen",
        "Healthy Ageing Campus",
    ]
    for query in queries:
        url = f"https://www.google.com/search?q={quote_plus('site:dvhn.nl ' + query)}"
        st.markdown(f"- [{query}]({url})")


def render_external_news(external_news: pd.DataFrame) -> None:
    st.markdown('<div class="section-title">Externe signalen via RSS</div>', unsafe_allow_html=True)
    st.caption("Context uit geselecteerde regionale kennis- en nieuwsbronnen. Gebruik dit als haakje naast ledennieuws.")
    if external_news.empty:
        st.info("Nog geen externe RSS-items gevonden. Draai de GitHub Action of upload external_news.csv.")
        return

    sort_cols = [col for col in ["item_date", "relevance_score"] if col in external_news.columns]
    if sort_cols:
        external_news = external_news.sort_values(sort_cols, ascending=False)

    top = external_news.head(10)
    for _, row in top.iterrows():
        date_value = row.get("item_date")
        date_text = date_value.date().isoformat() if pd.notna(date_value) else "Geen datum"
        source = row.get("source_name", "Externe bron")
        title = row.get("title", "Zonder titel")
        summary = row.get("summary", "")
        topics = row.get("matched_topics", "")
        url = row.get("source_url", "")
        st.markdown(
            f"""
            <div class="story-card">
                <div class="story-meta">{date_text} · {source}</div>
                <div class="story-title">{title}</div>
                <div class="story-summary">{summary}</div>
                <span class="pill">{topics or "context"}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if url:
            st.link_button("Open externe bron", url)

    columns = [
        col
        for col in ["item_date", "source_name", "relevance_score", "matched_topics", "title", "source_url", "summary"]
        if col in external_news.columns
    ]
    with st.expander("Alle externe RSS-items"):
        render_light_table(
            external_news,
            columns,
            labels={
                "item_date": "Datum",
                "source_name": "Bron",
                "relevance_score": "Score",
                "matched_topics": "Thema's",
                "title": "Titel",
                "source_url": "Link",
                "summary": "Samenvatting",
            },
            link_columns={"source_url"},
        )


def render_jobs(jobs: pd.DataFrame) -> None:
    st.markdown('<div class="section-title">Vacatures & groei</div>', unsafe_allow_html=True)
    st.caption("Vacatures zijn geen nieuwsitems, maar wel sterke signalen voor groei, talentbehoefte en nieuwe projecten.")

    if jobs.empty:
        st.info("Nog geen vacatures gevonden. Draai de GitHub Action of upload member_jobs.csv.")
        return

    member_count = jobs["member_name"].nunique() if "member_name" in jobs.columns else 0
    col1, col2, col3 = st.columns(3)
    col1.metric("Vacatures gevonden", len(jobs))
    col2.metric("Leden met vacatures", member_count)
    col3.metric("Talent-signaal", "Hoog" if len(jobs) >= 10 else "Opbouwend")

    left, right = st.columns([1.2, 1])
    with left:
        st.markdown("#### Openstaande signalen")
        for _, row in jobs.head(12).iterrows():
            member = row.get("member_name", "Onbekend lid")
            title = row.get("job_title", "Vacature")
            location = row.get("location", "")
            hours = row.get("hours", "")
            deadline = row.get("deadline", "")
            source = row.get("source_url", "")
            summary = row.get("signal_summary", "")
            st.markdown(
                f"""
                <div class="story-card">
                    <div class="story-meta">{member}</div>
                    <div class="story-title">{title}</div>
                    <div class="story-summary">{summary}</div>
                    <span class="pill">{location or "locatie onbekend"}</span>
                    <span class="pill">{hours or "uren onbekend"}</span>
                    <span class="pill">{deadline or "deadline onbekend"}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if source:
                st.link_button("Open vacaturepagina", source)

    with right:
        st.markdown("#### Nieuwsbriefhaakjes")
        top_members = (
            jobs.groupby("member_name", as_index=False)
            .size()
            .rename(columns={"size": "vacatures"})
            .sort_values("vacatures", ascending=False)
            .head(10)
        )
        if not top_members.empty:
            st.bar_chart(top_members, x="member_name", y="vacatures", use_container_width=True)
        st.markdown(
            """
            <div class="copy-box">Mogelijke invalshoeken:

- Leden zoeken technisch en wetenschappelijk talent.
- Vacatures wijzen op groei rond diagnostiek, imaging, productontwikkeling of operations.
- Vraag leden met meerdere vacatures om een korte update: waarom groeien ze, welke expertise zoeken ze?</div>
            """,
            unsafe_allow_html=True,
        )

    columns = [
        col
        for col in ["member_name", "job_title", "location", "hours", "deadline", "source_url", "detected_at", "signal_summary"]
        if col in jobs.columns
    ]
    st.markdown("#### Alle vacatures")
    render_light_table(
        jobs,
        columns,
        labels={
            "member_name": "Lid",
            "job_title": "Vacature",
            "location": "Locatie",
            "hours": "Uren",
            "deadline": "Deadline",
            "source_url": "Bron",
            "detected_at": "Gevonden op",
            "signal_summary": "Signaal",
        },
        link_columns={"source_url"},
    )


def render_news_table(news: pd.DataFrame) -> None:
    if news.empty:
        st.info("Geen nieuwsitems gevonden. Upload de CSV uit het GitHub Actions artifact of draai de pipeline.")
        return

    columns = [
        col
        for col in [
            "item_date",
            "member_name",
            "classification",
            "category",
            "confidence",
            "title",
            "summary_nl",
            "source_url",
            "review_reason",
        ]
        if col in news.columns
    ]
    table = news[columns].copy()
    if "classification" in table.columns:
        table["classification"] = table["classification"].map(display_class)
    if "category" in table.columns:
        table["category"] = table["category"].map(display_category)
    sort_cols = [col for col in ["item_date", "confidence"] if col in table.columns]
    if sort_cols:
        table = table.sort_values(sort_cols, ascending=False)

    render_light_table(
        table,
        columns,
        labels={
            "item_date": "Datum",
            "member_name": "Lid",
            "classification": "Status",
            "category": "Thema",
            "source_url": "Bron",
            "confidence": "Score",
            "summary_nl": "Samenvatting",
            "review_reason": "Waarom geselecteerd",
        },
        link_columns={"source_url"},
    )


with st.sidebar:
    st.markdown("## Data")
    st.write(
        "Standaard leest dit dashboard uit `dashboard_data/`. "
        "Upload CSV's alleen handmatig als je een losse artifact wilt bekijken."
    )

classified_news = clean_news(load_default_or_upload("classified_recent_news.csv", CLASSIFIED_NEWS_PATHS))
recent_news = clean_news(load_default_or_upload("recent_news.csv", RECENT_NEWS_PATHS))
members = load_default_or_upload("life_members.csv", MEMBERS_PATHS)
external_news = clean_external_news(load_default_or_upload("external_news.csv", EXTERNAL_NEWS_PATHS))
jobs = clean_jobs(load_default_or_upload("member_jobs.csv", MEMBER_JOBS_PATHS))

news = classified_news if not classified_news.empty else recent_news
filtered_news = apply_filters(news)

render_lc_nav()
render_hero(news, members)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "Nieuwsbrief",
        "Analyse",
        "Alle items",
        "Vacatures & groei",
        "Leden coverage",
        "Trendradar",
    ]
)

with tab1:
    render_editorial_view(filtered_news)

with tab2:
    render_analytics(filtered_news)

with tab3:
    render_news_table(filtered_news)

with tab4:
    render_jobs(jobs)

with tab5:
    render_coverage(members)

with tab6:
    render_trends()
    render_external_news(external_news)
