# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GitHub Insights Assistant — a Streamlit app that ingests GitHub data into SQLite and answers natural-language questions by generating auditable SQL (NL→SQL via GPT-4o). Every answer is backed by clickable evidence (issue/PR numbers + URLs).

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py

# Environment setup (copy and fill in tokens)
cp .env.example .env
```

Required env vars: `GITHUB_TOKEN`, `OPENAI_API_KEY` (in `.env`).

## Architecture

```
app.py          → Streamlit UI (sidebar: ingest/insights/stats, main: ask/answer/evidence)
ingester.py     → Async GitHub REST API fetcher (httpx + retry + rate-limit) → SQLite
query_engine.py → NL→SQL: GPT-4o generates SELECT → validates read-only → executes → synthesises grounded answer
schema.sql      → SQLite schema (repos, issues table — issues+PRs unified via is_pr flag)
```

Flow: User asks question → query_engine sends schema + question to GPT-4o → gets SQL → validates it's a safe SELECT → executes against SQLite → feeds rows back to GPT-4o for synthesis → returns answer with citations.

## Key Design Decisions

- **Unified issues table**: Issues and PRs share one table, distinguished by `is_pr` boolean.
- **Read-only SQL validation**: The query engine must reject anything that isn't a SELECT.
- **Grounding**: SQL is surfaced to the user (auditable), evidence table includes clickable GitHub URLs.
- **Ingestion scope**: ~200 issues/PRs per repo, public repos only. Default targets: `tiangolo/fastapi`, `pydantic/pydantic`.
- **No embeddings**: Pure NL→SQL approach (embeddings listed as future improvement).
- **SQLite DB stored in `data/`** (gitignored).
