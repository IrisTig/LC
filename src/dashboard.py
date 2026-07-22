#!/usr/bin/env python3
"""Streamlit dashboard for LIFE Cooperative news-monitor outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st


OUTPUT_DIR = Path("outputs/life_members")
CLASSIFIED_NEWS_PATH = OUTPUT_DIR / "classified_recent_news.csv"
RECENT_NEWS_PATH = OUTPUT_DIR / "recent_news.csv"
MEMBERS_PATH = OUTPUT_DIR / "life_members.csv"


st.set_page_config(
    page_title="LIFE Cooperative News Monitor",
    page_icon="LC",
    layout="wide",
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
    if "confidence" in df.columns:
        df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce")
    if "heuristic_score" in df.columns:
        df["heuristic_score"] = pd.to_numeric(df["heuristic_score"], errors="coerce")
    return df


def metric_row(news: pd.DataFrame, members: pd.DataFrame) -> None:
    col1, col2, col3, col4 = st.columns(4)
    total_members = len(members) if not members.empty else 0
    followed_members = (
        members["website_url"].notna().sum()
        if not members.empty and "website_url" in members.columns
        else 0
    )
    useful_items = (
        news["classification"].isin(["newsworthy", "possibly_newsworthy"]).sum()
        if not news.empty and "classification" in news.columns
        else 0
    )
    col1.metric("Leden", total_members)
    col2.metric("Websites gevolgd", int(followed_members))
    col3.metric("Gevonden items", len(news))
    col4.metric("Nieuwswaardig/mogelijk", int(useful_items))


def apply_filters(news: pd.DataFrame) -> pd.DataFrame:
    if news.empty:
        return news

    filtered = news.copy()
    st.sidebar.header("Filters")

    if "classification" in filtered.columns:
        values = sorted(filtered["classification"].dropna().unique())
        selected = st.sidebar.multiselect("Classificatie", values, default=values)
        filtered = filtered[filtered["classification"].isin(selected)]

    if "category" in filtered.columns:
        values = sorted(filtered["category"].dropna().unique())
        selected = st.sidebar.multiselect("Categorie", values, default=values)
        filtered = filtered[filtered["category"].isin(selected)]

    if "member_name" in filtered.columns:
        values = sorted(filtered["member_name"].dropna().unique())
        selected = st.sidebar.multiselect("Lid", values, default=values)
        filtered = filtered[filtered["member_name"].isin(selected)]

    if "item_date" in filtered.columns and filtered["item_date"].notna().any():
        min_date = filtered["item_date"].min().date()
        max_date = filtered["item_date"].max().date()
        start_date, end_date = st.sidebar.date_input(
            "Periode",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
        filtered = filtered[
            (filtered["item_date"].dt.date >= start_date)
            & (filtered["item_date"].dt.date <= end_date)
        ]

    return filtered


def show_charts(news: pd.DataFrame) -> None:
    if news.empty:
        return

    left, right = st.columns(2)

    if "item_date" in news.columns and news["item_date"].notna().any():
        monthly = (
            news.assign(month=news["item_date"].dt.to_period("M").astype(str))
            .groupby("month", as_index=False)
            .size()
            .rename(columns={"size": "items"})
        )
        left.subheader("Items per maand")
        left.bar_chart(monthly, x="month", y="items")

    if "category" in news.columns:
        categories = (
            news.groupby("category", as_index=False)
            .size()
            .rename(columns={"size": "items"})
            .sort_values("items", ascending=False)
        )
        right.subheader("Categorieen")
        right.bar_chart(categories, x="category", y="items")

    left, right = st.columns(2)
    if "member_name" in news.columns:
        members = (
            news.groupby("member_name", as_index=False)
            .size()
            .rename(columns={"size": "items"})
            .sort_values("items", ascending=False)
            .head(15)
        )
        left.subheader("Meest actieve leden")
        left.bar_chart(members, x="member_name", y="items")

    if "classification" in news.columns:
        classes = (
            news.groupby("classification", as_index=False)
            .size()
            .rename(columns={"size": "items"})
            .sort_values("items", ascending=False)
        )
        right.subheader("Classificaties")
        right.bar_chart(classes, x="classification", y="items")


def show_table(news: pd.DataFrame) -> None:
    if news.empty:
        st.info("Geen nieuwsitems gevonden. Upload de CSV uit het GitHub Actions artifact of draai de pipeline.")
        return

    st.subheader("Nieuwsitems")
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
    table = news[columns].sort_values(
        [col for col in ["item_date", "confidence"] if col in news.columns],
        ascending=False,
    )
    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "source_url": st.column_config.LinkColumn("Bron"),
            "confidence": st.column_config.NumberColumn("Confidence", format="%.2f"),
        },
    )


def show_stakeholder_summary(news: pd.DataFrame) -> None:
    if news.empty or "classification" not in news.columns:
        return

    useful = news[news["classification"].isin(["newsworthy", "possibly_newsworthy"])].copy()
    if useful.empty:
        return

    st.subheader("Stakeholder-samenvatting")
    useful = useful.sort_values(
        [col for col in ["item_date", "confidence"] if col in useful.columns],
        ascending=False,
    )
    for _, row in useful.head(8).iterrows():
        date_value = row.get("item_date")
        date_text = date_value.date().isoformat() if pd.notna(date_value) else ""
        title = row.get("title", "Zonder titel")
        member = row.get("member_name", "Onbekend lid")
        category = row.get("category", "unknown")
        summary = row.get("summary_nl", "")
        source = row.get("source_url", "")
        st.markdown(f"**{date_text} - {member} - {category}**")
        st.markdown(f"{title}. {summary}")
        if source:
            st.markdown(f"[Bron]({source})")


st.title("LIFE Cooperative News Monitor")
st.caption("Dashboard voor monitoring, analyse en stakeholderupdates.")

with st.sidebar:
    st.header("Data")
    st.write("Upload CSV's uit het GitHub Actions artifact, of zet ze lokaal in `outputs/life_members/`.")

classified_news = clean_news(load_default_or_upload("classified_recent_news.csv", CLASSIFIED_NEWS_PATH))
recent_news = clean_news(load_default_or_upload("recent_news.csv", RECENT_NEWS_PATH))
members = load_default_or_upload("life_members.csv", MEMBERS_PATH)

news = classified_news if not classified_news.empty else recent_news
filtered_news = apply_filters(news)

metric_row(news, members)
show_charts(filtered_news)
show_stakeholder_summary(filtered_news)
show_table(filtered_news)
