from __future__ import annotations

from typing import Any

import httpx

from cyberdeck.integrations.base import Integration

_GITHUB_API = "https://api.github.com"
_EMPTY_STATE: dict[str, list[dict[str, Any]]] = {"commits": [], "prs": [], "issues": []}


class GitHubIntegration(Integration):
    name = "github"

    def event_name(self) -> str:
        return "github.update"

    async def fetch(self) -> dict[str, list[dict[str, Any]]]:
        username = self.config.app.github.username
        if not username:
            return _empty_state()

        headers = _headers(self.config.github_token)
        async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
            events_response = await client.get(
                f"{_GITHUB_API}/users/{username}/events",
                params={"per_page": "100"},
            )
            events_response.raise_for_status()

            prs_response = await client.get(
                f"{_GITHUB_API}/search/issues",
                params={"q": f"author:{username} type:pr state:open", "per_page": "10"},
            )
            prs_response.raise_for_status()

            issues_response = await client.get(
                f"{_GITHUB_API}/search/issues",
                params={"q": f"assignee:{username} state:open is:issue", "per_page": "10"},
            )
            issues_response.raise_for_status()

        return {
            "commits": _push_commits(events_response.json()),
            "prs": _issue_items(prs_response.json(), include_status=True),
            "issues": _issue_items(issues_response.json()),
        }


def _empty_state() -> dict[str, list[dict[str, Any]]]:
    return {key: list(value) for key, value in _EMPTY_STATE.items()}


def _headers(token: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _push_commits(events: Any) -> list[dict[str, str]]:
    if not isinstance(events, list):
        return []

    commits: list[dict[str, str]] = []
    for event in events:
        if not isinstance(event, dict) or event.get("type") != "PushEvent":
            continue

        repo = event.get("repo")
        payload = event.get("payload")
        raw_commits = payload.get("commits") if isinstance(payload, dict) else []
        repo_name = repo.get("name") if isinstance(repo, dict) else ""
        created_at = str(event.get("created_at") or "")

        for commit in raw_commits if isinstance(raw_commits, list) else []:
            if not isinstance(commit, dict):
                continue
            commits.append(
                {
                    "sha": str(commit.get("sha") or "")[:7],
                    "msg": _first_line(str(commit.get("message") or ""))[:80],
                    "repo": str(repo_name or ""),
                    "time": created_at,
                }
            )
            if len(commits) == 10:
                return commits

    return commits


def _first_line(message: str) -> str:
    return message.splitlines()[0] if message.splitlines() else ""


def _issue_items(payload: Any, *, include_status: bool = False) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []

    items = payload.get("items")
    if not isinstance(items, list):
        return []

    return [_issue_item(item, include_status=include_status) for item in items if isinstance(item, dict)]


def _issue_item(item: dict[str, Any], *, include_status: bool) -> dict[str, Any]:
    result = {
        "title": item.get("title"),
        "url": item.get("html_url"),
        "repo": _repo_from_url(item.get("repository_url")),
        "number": item.get("number"),
        "age": item.get("created_at"),
        "label": _first_label(item.get("labels")),
    }
    if include_status:
        result["status"] = item.get("state")
    return result


def _repo_from_url(repository_url: Any) -> str:
    if not isinstance(repository_url, str):
        return ""
    marker = "/repos/"
    if marker not in repository_url:
        return ""
    return repository_url.rsplit(marker, 1)[1]


def _first_label(labels: Any) -> str:
    if not isinstance(labels, list) or not labels:
        return ""
    first = labels[0]
    if not isinstance(first, dict):
        return ""
    return str(first.get("name") or "")
