"""GitHub data ingester.

Fetches issues, PRs, and metadata for configured repos via the GitHub REST API,
handles rate limits and retries, and writes to a local SQLite database.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Callable

import httpx
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

DEFAULT_REPOS = ["fastapi/fastapi", "pydantic/pydantic"]
DEFAULT_DB_PATH = "data/github.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"
GITHUB_API = "https://api.github.com"
MAX_BODY_CHARS = 500
MAX_RETRIES = 3


def _init_db(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    schema = SCHEMA_PATH.read_text()
    conn.executescript(schema)
    return conn


def _headers() -> dict[str, str]:
    token = os.getenv("GITHUB_TOKEN", "")
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


async def _wait_for_rate_limit(response: httpx.Response) -> None:
    remaining = int(response.headers.get("X-RateLimit-Remaining", "1"))
    if remaining <= 1:
        reset_at = int(response.headers.get("X-RateLimit-Reset", "0"))
        wait = max(reset_at - int(time.time()), 1)
        log.warning("Rate limit near zero, sleeping %ds", wait)
        await asyncio.sleep(wait)


async def _request_with_retry(client: httpx.AsyncClient, url: str, params: dict | None = None) -> httpx.Response:
    backoff = 1
    for attempt in range(MAX_RETRIES):
        resp = await client.get(url, params=params)
        if resp.status_code == 200:
            await _wait_for_rate_limit(resp)
            return resp
        if resp.status_code in (403, 429):
            reset_at = int(resp.headers.get("X-RateLimit-Reset", "0"))
            wait = max(reset_at - int(time.time()), backoff)
            log.warning("Rate limited (%d), attempt %d, sleeping %ds", resp.status_code, attempt + 1, wait)
            await asyncio.sleep(wait)
            backoff *= 2
            continue
        if resp.status_code >= 500:
            log.warning("Server error %d, attempt %d, sleeping %ds", resp.status_code, attempt + 1, backoff)
            await asyncio.sleep(backoff)
            backoff *= 2
            continue
        resp.raise_for_status()
    resp.raise_for_status()
    return resp  # unreachable, satisfies type checker


async def _fetch_repo_meta(client: httpx.AsyncClient, owner: str, repo: str) -> dict:
    resp = await _request_with_retry(client, f"{GITHUB_API}/repos/{owner}/{repo}")
    return resp.json()


async def _fetch_issues(
    client: httpx.AsyncClient, owner: str, repo: str, max_items: int
) -> list[dict]:
    items: list[dict] = []
    page = 1
    while len(items) < max_items:
        params = {"state": "all", "per_page": 100, "sort": "updated", "direction": "desc", "page": page}
        resp = await _request_with_retry(client, f"{GITHUB_API}/repos/{owner}/{repo}/issues", params)
        batch = resp.json()
        if not batch:
            break
        items.extend(batch)
        page += 1
    return items[:max_items]


def _save_repo(conn: sqlite3.Connection, data: dict) -> int:
    conn.execute(
        """INSERT OR REPLACE INTO repos (id, owner, name, full_name, description, stars, forks, open_issues_count, language, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data["id"],
            data["owner"]["login"],
            data["name"],
            data["full_name"],
            data.get("description"),
            data.get("stargazers_count"),
            data.get("forks_count"),
            data.get("open_issues_count"),
            data.get("language"),
            data.get("created_at"),
            data.get("updated_at"),
        ),
    )
    conn.commit()
    return data["id"]


def _save_issues(conn: sqlite3.Connection, repo_id: int, items: list[dict]) -> int:
    rows = []
    for item in items:
        body = item.get("body") or ""
        labels = json.dumps([lbl["name"] for lbl in item.get("labels", [])])
        rows.append((
            item["id"],
            repo_id,
            item["number"],
            item["title"],
            body[:MAX_BODY_CHARS],
            item["state"],
            1 if "pull_request" in item else 0,
            item["user"]["login"] if item.get("user") else None,
            labels,
            item.get("created_at"),
            item.get("updated_at"),
            item.get("closed_at"),
            item.get("html_url", ""),
        ))
    conn.executemany(
        """INSERT OR REPLACE INTO issues (id, repo_id, number, title, body, state, is_pr, author, labels, created_at, updated_at, closed_at, url)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )
    conn.commit()
    return len(rows)


ProgressCallback = Callable[[str, float], None] | None


async def ingest_repos(
    repos: list[str] | None = None,
    db_path: str = DEFAULT_DB_PATH,
    max_items: int = 200,
    on_progress: ProgressCallback = None,
) -> None:
    """Ingest GitHub repos into the local SQLite database."""
    repos = repos or DEFAULT_REPOS
    conn = _init_db(db_path)

    async with httpx.AsyncClient(headers=_headers(), timeout=30.0) as client:
        for i, repo_slug in enumerate(repos):
            owner, repo = repo_slug.split("/")
            base_pct = i / len(repos)

            if on_progress:
                on_progress(f"Fetching metadata for {repo_slug}...", base_pct)
            log.info("Fetching repo metadata: %s", repo_slug)
            meta = await _fetch_repo_meta(client, owner, repo)
            repo_id = _save_repo(conn, meta)

            if on_progress:
                on_progress(f"Fetching issues/PRs for {repo_slug}...", base_pct + 0.3 / len(repos))
            log.info("Fetching issues/PRs: %s (max %d)", repo_slug, max_items)
            items = await _fetch_issues(client, owner, repo, max_items)

            count = _save_issues(conn, repo_id, items)
            log.info("Saved %d items for %s", count, repo_slug)
            if on_progress:
                on_progress(f"Saved {count} items for {repo_slug}", (i + 1) / len(repos))

    conn.close()
    if on_progress:
        on_progress("Ingestion complete.", 1.0)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    asyncio.run(ingest_repos())
