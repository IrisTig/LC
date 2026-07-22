#!/usr/bin/env python3
"""Streamlit dashboard for LIFE Cooperative communication teams."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
import streamlit as st


OUTPUT_DIR = Path("outputs/life_members")
CLASSIFIED_NEWS_PATH = OUTPUT_DIR / "classified_recent_news.csv"
RECENT_NEWS_PATH = OUTPUT_DIR / "recent_news.csv"
MEMBERS_PATH = OUTPUT_DIR / "life_members.csv"

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
        --life-blue: #55a6d9;
        --life-teal: #44c3b3;
        --life-ink: #101620;
        --life-soft: rgba(85, 166, 217, .12);
    }
    .block-container {
        padding-top: 2.2rem;
        padding-bottom: 4rem;
        max-width: 1440px;
    }
    [data-testid="stSidebar"] {
        border-right: 1px solid rgba(148, 163, 184, .18);
    }
    .life-hero {
        padding: 1.25rem 0 1.6rem 0;
        border-bottom: 1px solid rgba(148, 163, 184, .20);
        margin-bottom: 1.2rem;
    }
    .life-kicker {
        color: var(--life-blue);
        font-weight: 700;
        letter-spacing: .08em;
        text-transform: uppercase;
        font-size: .78rem;
        margin-bottom: .35rem;
    }
    .life-hero h1 {
        font-size: clamp(2.1rem, 4.3vw, 4.8rem);
        line-height: 1;
        margin: 0;
        letter-spacing: 0;
    }
    .life-subtitle {
        max-width: 860px;
        color: rgba(229, 231, 235, .72);
        font-size: 1.05rem;
        margin-top: .9rem;
    }
    .metric-card {
        border: 1px solid rgba(148, 163, 184, .18);
        background: linear-gradient(145deg, rgba(85, 166, 217, .13), rgba(68, 195, 179, .06));
        padding: 1rem 1.05rem;
        border-radius: 8px;
        min-height: 122px;
    }
    .metric-label {
        color: rgba(229, 231, 235, .68);
        font-size: .86rem;
        margin-bottom: .35rem;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        line-height: 1;
    }
    .metric-note {
        margin-top: .45rem;
        color: rgba(229, 231, 235, .62);
        font-size: .82rem;
    }
    .section-title {
        margin: 1.4rem 0 .5rem 0;
        font-size: 1.35rem;
        font-weight: 700;
    }
    .story-card {
        border: 1px solid rgba(148, 163, 184, .18);
        border-left: 4px solid var(--life-blue);
        border-radius: 8px;
        padding: .95rem 1rem;
        margin-bottom: .8rem;
        background: rgba(15, 23, 42, .28);
    }
    .story-meta {
        color: rgba(229, 231, 235, .64);
        font-size: .82rem;
        margin-bottom: .25rem;
    }
    .story-title {
        font-weight: 700;
        font-size: 1.02rem;
        margin-bottom: .28rem;
    }
    .story-summary {
        color: rgba(229, 231, 235, .76);
        margin-bottom: .45rem;
    }
    .pill {
        display: inline-block;
        border: 1px solid rgba(148, 163, 184, .22);
        border-radius: 999px;
        padding: .16rem .48rem;
        margin-right: .25rem;
        color: rgba(229, 231, 235, .76);
        font-size: .76rem;
    }
    .copy-box {
        border: 1px dashed rgba(85, 166, 217, .45);
        background: rgba(85, 166, 217, .08);
        padding: .9rem 1rem;
        border-radius: 8px;
        white-space: pre-wrap;
        color: rgba(229, 231, 235, .86);
    }
    .trend-card {
        border: 1px solid rgba(148, 163, 184, .18);
        border-radius: 8px;
        padding: 1rem;
        height: 100%;
        background: rgba(15, 23, 42, .22);
    }
    .trend-card h4 {
        margin-top: 0;
        margin-bottom: .4rem;
    }
    .coverage-good {
        color: #6ee7b7;
        font-weight: 700;
    }
    .coverage-missing {
        color: #fca5a5;
        font-weight: 700;
    }
    div[data-testid="stMetric"] {
        background: rgba(85, 166, 217, .08);
        border: 1px solid rgba(148, 163, 184, .18);
        border-radius: 8px;
        padding: .75rem .9rem;
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


def load_default_or_upload(label: str, default_path: Path) -> pd.DataFrame:
    uploaded = st.sidebar.file_uploader(label, type=["csv"])
    if uploaded is not None:
        return read_csv(uploaded)
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


def display_class(value: str) -> str:
    return CLASS_LABELS.get(value, value.replace("_", " ").title())


def display_category(value: str) -> str:
    return CATEGORY_LABELS.get(value, value.replace("_", " ").title())


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
            <div class="life-kicker">Communicatie dashboard</div>
            <h1>LIFE Cooperative Nieuwsradar</h1>
            <div class="life-subtitle">
                Vind ledennieuws, nieuwsbriefhaakjes en regionale trends zonder door tientallen websites te klikken.
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
        st.dataframe(
            missing_df[columns],
            use_container_width=True,
            hide_index=True,
            column_config={"detail_url": st.column_config.LinkColumn("LIFE profiel")},
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

    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "item_date": st.column_config.DateColumn("Datum"),
            "member_name": "Lid",
            "classification": "Status",
            "category": "Thema",
            "source_url": st.column_config.LinkColumn("Bron"),
            "confidence": st.column_config.NumberColumn("Score", format="%.2f"),
            "summary_nl": "Samenvatting",
            "review_reason": "Waarom geselecteerd",
        },
    )


with st.sidebar:
    st.markdown("## Data")
    st.write("Upload CSV's uit het GitHub Actions artifact, of zet ze lokaal in `outputs/life_members/`.")

classified_news = clean_news(load_default_or_upload("classified_recent_news.csv", CLASSIFIED_NEWS_PATH))
recent_news = clean_news(load_default_or_upload("recent_news.csv", RECENT_NEWS_PATH))
members = load_default_or_upload("life_members.csv", MEMBERS_PATH)

news = classified_news if not classified_news.empty else recent_news
filtered_news = apply_filters(news)

render_hero(news, members)

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Nieuwsbrief",
        "Analyse",
        "Alle items",
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
    render_coverage(members)

with tab5:
    render_trends()
