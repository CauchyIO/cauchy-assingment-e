"""Streamlit UI for GitHub Insights Assistant.

Single-page app with sidebar (ingest, quick insights, DB stats) and main panel
(question input, answer, SQL panel, evidence table with clickable URLs).
"""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

import streamlit as st

from ingester import DEFAULT_DB_PATH, DEFAULT_REPOS, ingest_repos
from query_engine import ask

st.set_page_config(page_title="GitHub Insights", layout="wide")


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def get_db_stats(db_path: str) -> dict | None:
    if not Path(db_path).exists():
        return None
    conn = sqlite3.connect(db_path)
    try:
        repos = conn.execute("SELECT count(*) FROM repos").fetchone()[0]
        issues = conn.execute("SELECT count(*) FROM issues WHERE is_pr = 0").fetchone()[0]
        prs = conn.execute("SELECT count(*) FROM issues WHERE is_pr = 1").fetchone()[0]
        return {"repos": repos, "issues": issues, "prs": prs}
    finally:
        conn.close()


def get_repo_names(db_path: str) -> list[str]:
    if not Path(db_path).exists():
        return []
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT full_name FROM repos ORDER BY full_name").fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


# --- Sidebar ---
with st.sidebar:
    st.header("Data Ingestion")

    repos_text = st.text_area(
        "Repositories (one per line)",
        value="\n".join(DEFAULT_REPOS),
        height=80,
    )
    max_items = st.slider("Max items per repo", 50, 500, 200, step=50)

    if st.button("Ingest Repos", type="primary"):
        repos_list = [r.strip() for r in repos_text.strip().splitlines() if r.strip()]
        progress_bar = st.progress(0.0)
        status_text = st.empty()

        def on_progress(msg: str, pct: float):
            progress_bar.progress(pct)
            status_text.text(msg)

        with st.spinner("Ingesting..."):
            run_async(ingest_repos(repos_list, DEFAULT_DB_PATH, max_items, on_progress))
        status_text.text("Done!")
        st.rerun()

    st.divider()
    st.header("DB Stats")
    stats = get_db_stats(DEFAULT_DB_PATH)
    if stats:
        col1, col2, col3 = st.columns(3)
        col1.metric("Repos", stats["repos"])
        col2.metric("Issues", stats["issues"])
        col3.metric("PRs", stats["prs"])
    else:
        st.info("No data yet. Ingest repos first.")

    st.divider()
    st.header("Quick Insights")

    quick_questions = [
        "Who are the most active contributors?",
        "What are the most common labels?",
        "Which issues have been open the longest?",
        "Compare open vs closed PR ratio across repos",
    ]

    for q in quick_questions:
        if st.button(q, key=f"quick_{q}"):
            st.session_state.question = q


# --- Main Panel ---
st.title("GitHub Insights Assistant")
st.caption("Ask natural-language questions about your ingested GitHub data.")

all_repos = get_repo_names(DEFAULT_DB_PATH)
repo_filter = st.multiselect(
    "Filter by repository",
    options=all_repos,
    default=all_repos,
    help="Select which repos to include in the query. Default is all.",
)

if "question" not in st.session_state:
    st.session_state.question = ""
if "last_answer" not in st.session_state:
    st.session_state.last_answer = None

question = st.text_input(
    "Your question",
    value=st.session_state.question,
    placeholder="e.g. What are the most discussed open issues in fastapi?",
)

if st.button("Ask", type="primary") or (question and question != st.session_state.get("_prev_question")):
    if question:
        st.session_state.question = question
        st.session_state._prev_question = question

        if not Path(DEFAULT_DB_PATH).exists():
            st.error("No database found. Please ingest repos first using the sidebar.")
        else:
            active_filter = repo_filter if set(repo_filter) != set(all_repos) else None
            with st.spinner("Thinking..."):
                answer = run_async(ask(question, DEFAULT_DB_PATH, repo_filter=active_filter))
            st.session_state.last_answer = answer

answer = st.session_state.last_answer
if answer:
    if answer.error:
        st.error(answer.error)

    if answer.text:
        st.markdown("### Answer")
        st.markdown(answer.text)

    if answer.sql:
        with st.expander("Generated SQL", expanded=False):
            st.code(answer.sql, language="sql")

    if answer.raw_rows:
        st.markdown("### Evidence")
        import pandas as pd

        df = pd.DataFrame(answer.raw_rows)
        if "url" in df.columns:
            df["url"] = df["url"].apply(lambda u: f"[link]({u})" if u else "")
        st.dataframe(df, use_container_width=True)
