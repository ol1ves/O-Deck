from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest
import respx

from cyberdeck.cache import Cache
from cyberdeck.config import AppConfig, GitHubConfig, Settings
from cyberdeck.integrations.github import GitHubIntegration
from cyberdeck.ws import WSManager


EVENTS_URL = "https://api.github.com/users/octocat/events"
SEARCH_URL = "https://api.github.com/search/issues"
EMPTY_STATE = {"commits": [], "prs": [], "issues": []}


def make_config(*, username: str = "octocat", token: str | None = None) -> Settings:
    return Settings(github_token=token, app=AppConfig(github=GitHubConfig(username=username)))


def make_integration(config: Settings | None = None, cache=None, ws=None) -> GitHubIntegration:
    return GitHubIntegration(
        cache=cache or MagicMock(),
        ws_manager=ws or MagicMock(),
        config=config or make_config(),
    )


def search_payload(*items: dict) -> dict:
    return {"total_count": len(items), "items": list(items)}


def test_integration_event_contract():
    integration = make_integration()

    assert integration.name == "github"
    assert integration.event_name() == "github.update"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_without_username_returns_empty_state_and_skips_http():
    events_route = respx.get(EVENTS_URL).mock(return_value=httpx.Response(200, json=[]))

    result = await make_integration(config=make_config(username="")).fetch()

    assert result == EMPTY_STATE
    assert not events_route.called


@pytest.mark.asyncio
@respx.mock
async def test_fetch_extracts_push_commits():
    respx.get(EVENTS_URL).mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "type": "PushEvent",
                    "repo": {"name": "octocat/Hello-World"},
                    "created_at": "2026-04-26T12:00:00Z",
                    "payload": {
                        "commits": [
                            {
                                "sha": "0123456789abcdef",
                                "message": "Fix dashboard tile\n\nBody ignored",
                            }
                        ]
                    },
                }
            ],
        )
    )
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=search_payload()))

    result = await make_integration().fetch()

    assert result["commits"] == [
        {
            "sha": "0123456",
            "msg": "Fix dashboard tile",
            "repo": "octocat/Hello-World",
            "time": "2026-04-26T12:00:00Z",
        }
    ]


@pytest.mark.asyncio
@respx.mock
async def test_fetch_ignores_non_push_events_and_caps_commits_at_ten():
    push_events = [
        {
            "type": "PushEvent",
            "repo": {"name": "octocat/repo"},
            "created_at": f"2026-04-26T12:{minute:02d}:00Z",
            "payload": {"commits": [{"sha": f"{minute:040d}", "message": f"Commit {minute}"}]},
        }
        for minute in range(12)
    ]
    events = [{"type": "IssuesEvent", "repo": {"name": "octocat/nope"}}] + push_events
    respx.get(EVENTS_URL).mock(return_value=httpx.Response(200, json=events))
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=search_payload()))

    result = await make_integration().fetch()

    assert len(result["commits"]) == 10
    assert all(commit["repo"] == "octocat/repo" for commit in result["commits"])


@pytest.mark.asyncio
@respx.mock
async def test_fetch_truncates_commit_message_first_line_to_eighty_chars():
    long_line = "x" * 90
    respx.get(EVENTS_URL).mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "type": "PushEvent",
                    "repo": {"name": "octocat/repo"},
                    "created_at": "2026-04-26T12:00:00Z",
                    "payload": {"commits": [{"sha": "abcdef123456", "message": f"{long_line}\nignored"}]},
                }
            ],
        )
    )
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=search_payload()))

    result = await make_integration().fetch()

    assert result["commits"][0]["msg"] == "x" * 80


@pytest.mark.asyncio
@respx.mock
async def test_fetch_maps_open_prs():
    respx.get(EVENTS_URL).mock(return_value=httpx.Response(200, json=[]))
    respx.get(SEARCH_URL).mock(
        side_effect=[
            httpx.Response(
                200,
                json=search_payload(
                    {
                        "title": "Add backend integration",
                        "html_url": "https://github.com/octocat/repo/pull/12",
                        "repository_url": "https://api.github.com/repos/octocat/repo",
                        "number": 12,
                        "state": "open",
                        "created_at": "2026-04-24T10:00:00Z",
                        "labels": [{"name": "backend"}],
                    }
                ),
            ),
            httpx.Response(200, json=search_payload()),
        ]
    )

    result = await make_integration().fetch()

    assert result["prs"] == [
        {
            "title": "Add backend integration",
            "url": "https://github.com/octocat/repo/pull/12",
            "repo": "octocat/repo",
            "number": 12,
            "status": "open",
            "age": "2026-04-24T10:00:00Z",
            "label": "backend",
        }
    ]


@pytest.mark.asyncio
@respx.mock
async def test_fetch_maps_assigned_issues_with_empty_label_fallback():
    respx.get(EVENTS_URL).mock(return_value=httpx.Response(200, json=[]))
    respx.get(SEARCH_URL).mock(
        side_effect=[
            httpx.Response(200, json=search_payload()),
            httpx.Response(
                200,
                json=search_payload(
                    {
                        "title": "Fix widget bug",
                        "html_url": "https://github.com/octocat/repo/issues/34",
                        "repository_url": "https://api.github.com/repos/octocat/repo",
                        "number": 34,
                        "created_at": "2026-04-25T10:00:00Z",
                        "labels": [],
                    }
                ),
            ),
        ]
    )

    result = await make_integration().fetch()

    assert result["issues"] == [
        {
            "title": "Fix widget bug",
            "url": "https://github.com/octocat/repo/issues/34",
            "repo": "octocat/repo",
            "number": 34,
            "age": "2026-04-25T10:00:00Z",
            "label": "",
        }
    ]


@pytest.mark.asyncio
@respx.mock
async def test_fetch_sends_required_headers_and_bearer_token():
    events_route = respx.get(EVENTS_URL).mock(return_value=httpx.Response(200, json=[]))
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=search_payload()))

    await make_integration(config=make_config(token="github-token")).fetch()

    request = events_route.calls[0].request
    assert request.headers["accept"] == "application/vnd.github+json"
    assert request.headers["x-github-api-version"] == "2022-11-28"
    assert request.headers["authorization"] == "Bearer github-token"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_requests_expected_github_queries():
    respx.get(EVENTS_URL).mock(return_value=httpx.Response(200, json=[]))
    search_route = respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=search_payload()))

    await make_integration().fetch()

    queries = [call.request.url.params["q"] for call in search_route.calls]
    per_pages = [call.request.url.params["per_page"] for call in search_route.calls]
    assert queries == [
        "author:octocat type:pr state:open",
        "assignee:octocat state:open is:issue",
    ]
    assert per_pages == ["10", "10"]


@pytest.mark.asyncio
@respx.mock
async def test_run_swallows_http_error_and_increments_error_count(tmp_path):
    respx.get(EVENTS_URL).mock(return_value=httpx.Response(503))

    integration = make_integration(cache=Cache(db_path=tmp_path / "c.db"), ws=WSManager())
    await integration.run()

    assert integration.status["error_count"] == 1
