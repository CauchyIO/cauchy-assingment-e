# GitHub data ingester.

# Fetches issues, PRs, and metadata for configured repos via the GitHub REST API,
# handles rate limits and retries, and writes to a local SQLite database.