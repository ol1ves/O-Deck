from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from cyberdeck.cache import Cache
from cyberdeck.integrations.calendar import (
    CalendarIntegration,
    _join_events,
    _parse_google_event,
)
from cyberdeck.ws import WSManager


def make_config(
    *,
    token_path: Path | None = None,
    creds_path: Path | None = None,
    notion_token: str | None = None,
    calendar_ids: list[str] | None = None,
    database_ids: list[str] | None = None,
):
    cfg = MagicMock()
    cfg.google_calendar_token_path = token_path
    cfg.google_calendar_credentials_path = creds_path
    cfg.notion_token = notion_token
    cfg.app.calendar.google.calendar_ids = calendar_ids or ["primary"]
    cfg.app.calendar.notion.todo_database_ids = database_ids or []
    return cfg


def make_integration(config=None, cache=None, ws=None):
    return CalendarIntegration(
        cache=cache or MagicMock(),
        ws_manager=ws or MagicMock(),
        config=config or make_config(),
    )


def test_parse_google_event_extracts_fields_and_duration():
    event = _parse_google_event(
        {
            "id": "evt_1",
            "summary": "Design review",
            "start": {"dateTime": "2026-04-26T09:30:00-04:00"},
            "end": {"dateTime": "2026-04-26T10:45:00-04:00"},
            "location": "Studio",
            "description": "https://notion.so/page-alpha",
            "colorId": "5",
        }
    )

    assert event == {
        "id": "evt_1",
        "title": "Design review",
        "time": "2026-04-26T09:30:00-04:00",
        "duration": 75,
        "location": "Studio",
        "description": "https://notion.so/page-alpha",
        "color": "5",
        "notion": None,
    }


def test_join_events_matches_notion_todo_by_url_in_description():
    events = [
        {
            "id": "evt_1",
            "title": "Design review",
            "description": "Prep https://notion.so/page-alpha before meeting",
            "notion": None,
        }
    ]
    todos = [
        {
            "id": "page-alpha",
            "url": "https://notion.so/page-alpha",
            "properties": {
                "Name": {"title": [{"plain_text": "Design review"}]},
                "Status": {"status": {"name": "In Progress"}},
                "Project": {"select": {"name": "Cyberdeck"}},
            },
        }
    ]

    joined = _join_events(events, todos)

    assert joined[0]["notion"] == {
        "status": "In Progress",
        "project": "Cyberdeck",
        "page_id": "page-alpha",
    }


def test_join_events_matches_notion_todo_by_plain_url_and_title_fallback():
    events = [
        {"id": "evt_url", "title": "Unrelated", "description": "notion.so/page-beta", "notion": None},
        {"id": "evt_title", "title": "Ship calendar", "description": "", "notion": None},
    ]
    todos = [
        {
            "id": "page-beta",
            "url": "https://notion.so/page-beta",
            "properties": {
                "Name": {"title": [{"plain_text": "Different title"}]},
                "Status": {"select": {"name": "Queued"}},
            },
        },
        {
            "id": "page-gamma",
            "url": "https://notion.so/page-gamma",
            "properties": {
                "Name": {"title": [{"plain_text": "Ship calendar"}]},
                "Project": {"rich_text": [{"plain_text": "Backend"}]},
            },
        },
    ]

    joined = _join_events(events, todos)

    assert joined[0]["notion"]["page_id"] == "page-beta"
    assert joined[0]["notion"]["status"] == "Queued"
    assert joined[1]["notion"] == {
        "status": None,
        "project": "Backend",
        "page_id": "page-gamma",
    }


@pytest.mark.asyncio
async def test_fetch_loads_token_in_executor_and_returns_joined_events(monkeypatch, tmp_path):
    token_path = tmp_path / "token.json"
    creds_path = tmp_path / "credentials.json"
    token_path.write_text("{}")
    creds_path.write_text("{}")
    token = SimpleNamespace(token="google-token")

    load_token = MagicMock(return_value=token)
    fetch_google = AsyncMock(
        return_value=[
            {
                "id": "evt_1",
                "summary": "Ship calendar",
                "start": {"dateTime": "2026-04-26T12:00:00-04:00"},
                "end": {"dateTime": "2026-04-26T12:30:00-04:00"},
                "description": "https://notion.so/page-1",
            }
        ]
    )
    fetch_notion = AsyncMock(
        return_value=[
            {
                "id": "page-1",
                "url": "https://notion.so/page-1",
                "properties": {
                    "Name": {"title": [{"plain_text": "Ship calendar"}]},
                    "Status": {"status": {"name": "Done"}},
                },
            }
        ]
    )
    run_in_executor = AsyncMock(return_value=token)
    loop = MagicMock()
    loop.run_in_executor = run_in_executor

    monkeypatch.setattr("cyberdeck.integrations.calendar._load_google_token", load_token)
    monkeypatch.setattr("cyberdeck.integrations.calendar._fetch_google_events", fetch_google)
    monkeypatch.setattr("cyberdeck.integrations.calendar._fetch_notion_todos", fetch_notion)
    monkeypatch.setattr("cyberdeck.integrations.calendar.asyncio.get_running_loop", lambda: loop)
    monkeypatch.setattr("cyberdeck.integrations.calendar.date", MagicMock(today=lambda: SimpleNamespace(isoformat=lambda: "2026-04-26")))

    result = await make_integration(
        make_config(
            token_path=token_path,
            creds_path=creds_path,
            notion_token="notion-secret",
            calendar_ids=["primary", "family"],
            database_ids=["todo-db"],
        )
    ).fetch()

    assert result["next_in"] == 300
    assert result["events"][0]["notion"]["status"] == "Done"
    run_in_executor.assert_awaited_once()
    assert run_in_executor.await_args.args == (None, load_token, token_path, creds_path)
    fetch_google.assert_awaited_once_with(token, ["primary", "family"], "2026-04-26")
    fetch_notion.assert_awaited_once_with("notion-secret", ["todo-db"])


@pytest.mark.asyncio
async def test_fetch_returns_empty_events_when_google_creds_or_token_missing(tmp_path):
    creds_path = tmp_path / "credentials.json"
    creds_path.write_text("{}")

    missing_token_result = await make_integration(
        make_config(token_path=tmp_path / "missing-token.json", creds_path=creds_path)
    ).fetch()
    missing_creds_result = await make_integration(
        make_config(token_path=tmp_path / "token.json", creds_path=tmp_path / "missing-creds.json")
    ).fetch()

    assert missing_token_result == {"events": [], "next_in": None}
    assert missing_creds_result == {"events": [], "next_in": None}


@pytest.mark.asyncio
async def test_run_swallows_auth_error_and_increments_error_count(monkeypatch, tmp_path):
    token_path = tmp_path / "token.json"
    creds_path = tmp_path / "credentials.json"
    token_path.write_text("{}")
    creds_path.write_text("{}")

    loop = MagicMock()
    loop.run_in_executor = AsyncMock(side_effect=ValueError("auth failed"))
    monkeypatch.setattr("cyberdeck.integrations.calendar.asyncio.get_running_loop", lambda: loop)

    integration = CalendarIntegration(
        cache=Cache(db_path=tmp_path / "c.db"),
        ws_manager=WSManager(),
        config=make_config(token_path=token_path, creds_path=creds_path),
    )

    await integration.run()

    assert integration.status["error_count"] == 1
