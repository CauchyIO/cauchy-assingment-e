"""NL→SQL query engine.

Translates natural-language questions into safe SELECT queries against the
SQLite store, executes them, and synthesises grounded answers with citations.
"""

from __future__ import annotations

import logging
import os
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

log = logging.getLogger(__name__)

DEFAULT_DB_PATH = "data/github.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"
MAX_ROWS = 50

UNSAFE_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|ATTACH|DETACH|PRAGMA|REPLACE)\b",
    re.IGNORECASE,
)

_client = AsyncOpenAI(
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY"),
)
MODEL = "azure.gpt-5.1" #TODO: make this configurable via env var


@dataclass
class Answer:
    question: str
    sql: str = ""
    raw_rows: list[dict] = field(default_factory=list)
    text: str = ""
    error: str | None = None


def _get_schema() -> str:
    return SCHEMA_PATH.read_text()


SQL_SYSTEM_PROMPT = """You are a SQL expert. Given the SQLite schema below, generate a single SELECT query to answer the user's question.

SCHEMA:
{schema}

RULES:
- Return ONLY the SQL query, no explanation, no markdown fences.
- Use is_pr = 1 for pull requests, is_pr = 0 for issues.
- Labels are stored as a JSON array string. Use json_each(labels) or LIKE for filtering.
- Always include the `url` column when referencing specific issues or PRs.
- Join with repos table when you need repo names.
- If the question cannot be answered from this schema, return exactly: SELECT 'NOT_ANSWERABLE' AS error
"""

SYNTHESIS_SYSTEM_PROMPT = """You answer questions about GitHub repositories using ONLY the data provided.

RULES:
- Be concise: 2-4 sentences max.
- Reference specific issues/PRs by number with their URL as markdown links.
- If no data rows are provided or results are empty, say you don't have enough data to answer.
- Never invent information not present in the data.
"""


def _validate_sql(sql: str) -> str | None:
    normalized = sql.strip()
    if normalized.endswith(";"):
        normalized = normalized[:-1].strip()

    if ";" in normalized:
        return "Generated query contains multiple statements."

    stripped = normalized.lstrip("-").strip().upper()
    if not (stripped.startswith("SELECT") or stripped.startswith("WITH")):
        return "Generated query must start with SELECT or WITH."
    if UNSAFE_KEYWORDS.search(normalized):
        return "Generated query contains unsafe keywords."
    return None


def _execute_sql(sql: str, db_path: str) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute(sql)
        rows = [dict(row) for row in cursor.fetchmany(MAX_ROWS)]
        return rows
    finally:
        conn.close()


async def ask(question: str, db_path: str = DEFAULT_DB_PATH, repo_filter: list[str] | None = None) -> Answer:
    """Ask a natural-language question about the ingested GitHub data."""
    answer = Answer(question=question)

    try:
        schema = _get_schema()
        system_content = SQL_SYSTEM_PROMPT.format(schema=schema)
        if repo_filter:
            system_content += f"\nOnly consider these repos: {', '.join(repo_filter)}"
        sql_resp = await _client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": question},
            ],
            temperature=0,
        )
        sql = sql_resp.choices[0].message.content.strip()
        sql = sql.removeprefix("```sql").removeprefix("```").removesuffix("```").strip()
        answer.sql = sql
    except Exception as e:
        answer.error = f"LLM API error during SQL generation: {e}"
        return answer

    validation_error = _validate_sql(sql)
    if validation_error:
        answer.error = validation_error
        return answer

    if "NOT_ANSWERABLE" in sql:
        answer.text = "This question cannot be answered from the available data."
        return answer

    try:
        rows = _execute_sql(sql, db_path)
        answer.raw_rows = rows
    except Exception as e:
        answer.error = f"SQL execution error: {e}"
        return answer

    try:
        rows_text = "\n".join(str(r) for r in rows) if rows else "(no results)"
        synth_resp = await _client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
                {"role": "user", "content": f"Question: {question}\n\nSQL used:\n{sql}\n\nResults:\n{rows_text}"},
            ],
            temperature=0,
        )
        answer.text = synth_resp.choices[0].message.content.strip()
    except Exception as e:
        answer.error = f"LLM API error during synthesis: {e}"

    return answer
