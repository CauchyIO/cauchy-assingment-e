# Plan - GitHub Insights Assistant (NL→SQL + Streamlit)

> Living doc. Updated as I work.

## 1. Problem
Build a Streamlit app that ingests real GitHub data into SQLite and answers natural-language questions by generating auditable SQL, with every answer backed by clickable evidence (issue/PR numbers + URLs).

## 2. Scope (chosen explicitly)
- **2–3 related public repos** (default: `tiangolo/fastapi`, `pydantic/pydantic`).
- **Data:** repo metadata, issues, PRs, labels, authors, timestamps, body snippets.
- **Interface:** single-page Streamlit app with sidebar (ingest + quick insights + stats) and main panel (ask + answer + evidence).

## 3. Assumptions
- Python 3.11+, `pip install -r requirements.txt`.
- `GITHUB_TOKEN` and `OPENAI_API_KEY` in `.env`.
- ~200 issues/PRs per repo for demo speed.
- Public repos only.

## 4. Out of Scope
- Multi-turn chat, embeddings, deployment, webhooks, comments ingestion, PR reviews ingestion, multi-page UI, authentication.

## 5. Approach
- **Ingestion:** async `httpx` + retry + rate-limit handling → SQLite.
- **NL→SQL:** GPT-4o generates a `SELECT` query against a documented schema; validated read-only; executed; rows fed back into a synthesis call.
- **Grounding:**
  - SQL surfaced in collapsible panel (auditable).
  - Evidence table with clickable URLs.
  - Pre-built insight buttons as deterministic fallback.


## 6. Timeline
- [ ] 0:00–0:10 — Scaffold + planning docs
- [ ] 0:10–0:30 — GitHub ingester
- [ ] 0:30–0:45 — Verify ingest e2e
- [ ] 0:45–1:05 — NL→SQL engine + safety
- [ ] 1:05–1:30 — Streamlit UI core
- [ ] 1:30–1:42 — Quick insights + polish
- [ ] 1:42–1:52 — Sample outputs + errors
- [ ] 1:52–2:00 — README

## 7. Quality Check
- 5 hand-picked questions covering: factual lookup, aggregation, theme query, comparison, out-of-scope refusal.
- Manually grade each: ✅ grounded / ⚠️ partial / ❌ hallucinated.
- Screenshots in `samples/`.

## 8. Risks
- **OpenAI flaky during demo** → pre-cache 3 example answers; have screenshots ready.
- **Streamlit eats time** → cut quick-insight buttons first, then drop 3rd repo.
- **LLM writes wrong-but-valid SQL** → mitigated by surfacing SQL + explanation to user.
- **GitHub rate limit mid-demo** → ingest beforehand; demo uses cached DB.

## 9. AI Usage Log
| Tool | Used for | Verified by |
|---|---|---|
|      |          |             |

## 10. With More Time
- [ ] Embeddings hybrid retrieval for paraphrased questions
- [ ] Comments + PR reviews ingestion
- [ ] Streamlit chat memory (multi-turn)
- [ ] LLM-as-judge eval over a golden question set
- [ ] Caching LLM responses by (question, db_hash)
- [ ] Deploy to Streamlit Community Cloud