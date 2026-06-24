-- SQLite schema for GitHub Insights Assistant.
-- Tables: repos, issues (issues + PRs unified, distinguished by is_pr).
-- Comments and reviews intentionally deferred (out of scope for v1).

CREATE TABLE IF NOT EXISTS repos (
    id INTEGER PRIMARY KEY,
    owner TEXT NOT NULL,
    name TEXT NOT NULL,
    full_name TEXT NOT NULL UNIQUE,
    description TEXT,
    stars INTEGER,
    forks INTEGER,
    open_issues_count INTEGER,
    language TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS issues (
    id INTEGER PRIMARY KEY,
    repo_id INTEGER NOT NULL REFERENCES repos(id),
    number INTEGER NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    state TEXT NOT NULL,
    is_pr INTEGER NOT NULL DEFAULT 0,
    author TEXT,
    labels TEXT,
    created_at TEXT,
    updated_at TEXT,
    closed_at TEXT,
    url TEXT NOT NULL,
    UNIQUE(repo_id, number)
);
