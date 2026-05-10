"""GitHub API helpers for repository metadata collection."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

LOGGER = logging.getLogger(__name__)
GITHUB_API_BASE_URL = "https://api.github.com"


class GitHubApiError(RuntimeError):
    """Raised when GitHub API metadata retrieval fails."""


def get_repository_info(owner: str, repo: str) -> dict[str, Any]:
    """Fetch basic metadata for a GitHub repository.

    Args:
        owner: Repository owner or organization name.
        repo: Repository name.

    Returns:
        A dictionary containing the repository full name, URL, star count,
        fork count, description, primary language, topics, and update time.

    Raises:
        ValueError: If `owner` or `repo` is empty.
        GitHubApiError: If GitHub returns an error or invalid response data.
    """
    if not owner.strip() or not repo.strip():
        raise ValueError("owner and repo must be non-empty")

    encoded_owner = urllib.parse.quote(owner.strip(), safe="")
    encoded_repo = urllib.parse.quote(repo.strip(), safe="")
    url = f"{GITHUB_API_BASE_URL}/repos/{encoded_owner}/{encoded_repo}"

    request = urllib.request.Request(url, headers=_build_headers())

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        LOGGER.warning("GitHub API returned HTTP %s for %s/%s", exc.code, owner, repo)
        raise GitHubApiError(f"GitHub API returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        LOGGER.warning("GitHub API request failed for %s/%s: %s", owner, repo, exc)
        raise GitHubApiError("GitHub API request failed") from exc
    except json.JSONDecodeError as exc:
        LOGGER.warning("GitHub API returned invalid JSON for %s/%s", owner, repo)
        raise GitHubApiError("GitHub API returned invalid JSON") from exc

    return {
        "full_name": payload.get("full_name"),
        "url": payload.get("html_url"),
        "stars": payload.get("stargazers_count"),
        "forks": payload.get("forks_count"),
        "description": payload.get("description") or "",
        "language": payload.get("language"),
        "topics": payload.get("topics") or [],
        "updated_at": payload.get("pushed_at"),
    }


def _build_headers() -> dict[str, str]:
    """Build GitHub API request headers without exposing credentials."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ai-knowledge-base-practice",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers
