from __future__ import annotations

import asyncio
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from cyberdeck.integrations.base import Integration

_GOOGLE_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
_NOTION_DATABASE_QUERY_URL = "https://api.notion.com/v1/databases/{database_id}/query"
_GOOGLE_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
_NOTION_VERSION = "2022-06-28"
_HTTP_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
_NEXT_IN_SECONDS = 300


def _load_google_token(token_path: Path, creds_path: Path) -> Credentials:
    if not creds_path.exists():
        raise FileNotFoundError(creds_path)
    if not token_path.exists():
        raise FileNotFoundError(token_path)

    creds = Credentials.from_authorized_user_file(str(token_path), _GOOGLE_SCOPES)
    if creds.expired:
        if not creds.refresh_token:
            raise RuntimeError("expired Google Calendar token has no refresh token")
        creds.refresh(Request())
        token_path.write_text(creds.to_json())
    return creds


async def _fetch_google_events(
    token: Credentials,
    calendar_ids: list[str],
    date_str: str,
    timezone: str,
) -> list[dict[str, Any]]:
    start_date = date.fromisoformat(date_str)
    tz = ZoneInfo(timezone)
    start = datetime.combine(start_date, time.min, tzinfo=tz)
    end = start + timedelta(days=1)
    headers = {"Authorization": f"Bearer {token.token}"}
    params = {
        "timeMin": start.isoformat(),
        "timeMax": end.isoformat(),
        "singleEvents": "true",
        "orderBy": "startTime",
    }

    events: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        for calendar_id in calendar_ids:
            url = _GOOGLE_EVENTS_URL.format(calendar_id=quote(calendar_id, safe=""))
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            payload = resp.json()
            items = payload.get("items", [])
            if isinstance(items, list):
                events.extend(item for item in items if isinstance(item, dict))
    return events


async def _fetch_notion_todos(token: str, database_ids: list[str]) -> list[dict[str, Any]]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": _NOTION_VERSION,
        "Content-Type": "application/json",
    }

    todos: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        for database_id in database_ids:
            url = _NOTION_DATABASE_QUERY_URL.format(database_id=quote(database_id, safe=""))
            cursor: str | None = None
            while True:
                body = {"start_cursor": cursor} if cursor else {}
                resp = await client.post(url, headers=headers, json=body)
                resp.raise_for_status()
                payload = resp.json()
                results = payload.get("results", [])
                if isinstance(results, list):
                    todos.extend(item for item in results if isinstance(item, dict))
                if not payload.get("has_more"):
                    break
                next_cursor = payload.get("next_cursor")
                cursor = next_cursor if isinstance(next_cursor, str) and next_cursor else None
                if cursor is None:
                    break
    return todos


def _parse_google_event(raw: dict[str, Any]) -> dict[str, Any]:
    start = _google_event_time(raw.get("start", {}))
    end = _google_event_time(raw.get("end", {}))

    return {
        "id": raw.get("id"),
        "title": raw.get("summary") or "(untitled)",
        "time": start,
        "duration": _duration_minutes(start, end),
        "location": raw.get("location"),
        "description": raw.get("description") or "",
        "color": raw.get("colorId"),
        "notion": None,
    }


def _join_events(events: list[dict[str, Any]], todos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    joined: list[dict[str, Any]] = []
    for event in events:
        match = _find_notion_match(event, todos)
        item = {**event}
        item["notion"] = _notion_summary(match) if match else None
        joined.append(item)
    return joined


class CalendarIntegration(Integration):
    name = "calendar"

    def event_name(self) -> str:
        return "calendar.update"

    async def fetch(self) -> dict[str, Any]:
        token_path = _as_path(self.config.google_calendar_token_path)
        creds_path = _as_path(self.config.google_calendar_credentials_path)
        if token_path is None or creds_path is None or not token_path.exists() or not creds_path.exists():
            return {"events": [], "next_in": None}

        loop = asyncio.get_running_loop()
        token = await loop.run_in_executor(None, _load_google_token, token_path, creds_path)
        timezone = self.config.app.device.timezone
        today = datetime.now(ZoneInfo(timezone)).date().isoformat()

        raw_events = await _fetch_google_events(
            token,
            list(self.config.app.calendar.google.calendar_ids),
            today,
            timezone,
        )
        events = [_parse_google_event(raw) for raw in raw_events]

        notion_token = self.config.notion_token
        database_ids = list(self.config.app.calendar.notion.todo_database_ids)
        todos = []
        if notion_token and database_ids:
            todos = await _fetch_notion_todos(notion_token, database_ids)

        return {"events": _join_events(events, todos), "next_in": _NEXT_IN_SECONDS}


def _as_path(value: Any) -> Path | None:
    if value is None:
        return None
    return value if isinstance(value, Path) else Path(value)


def _google_event_time(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    return value.get("dateTime") or value.get("date")


def _duration_minutes(start: str | None, end: str | None) -> int | None:
    if not start or not end:
        return None
    try:
        return int((_parse_dt(end) - _parse_dt(start)).total_seconds() // 60)
    except ValueError:
        return None


def _parse_dt(value: str) -> datetime:
    if value.endswith("Z"):
        value = f"{value[:-1]}+00:00"
    if "T" not in value:
        return datetime.fromisoformat(f"{value}T00:00:00")
    return datetime.fromisoformat(value)


def _find_notion_match(
    event: dict[str, Any],
    todos: list[dict[str, Any]],
) -> dict[str, Any] | None:
    description = str(event.get("description") or "")
    title = str(event.get("title") or "").strip().casefold()

    for todo in todos:
        url = str(todo.get("url") or "")
        if url and (_url_in_text(url, description) or _url_in_text(_plain_url(url), description)):
            return todo

    for todo in todos:
        if title and _notion_title(todo).casefold() == title:
            return todo
    return None


def _url_in_text(url: str, text: str) -> bool:
    return bool(url and text and url in text)


def _plain_url(url: str) -> str:
    return url.removeprefix("https://").removeprefix("http://")


def _notion_summary(todo: dict[str, Any]) -> dict[str, str | None]:
    props = todo.get("properties", {})
    if not isinstance(props, dict):
        props = {}
    return {
        "status": _first_property_value(props.get("Status")),
        "project": _first_property_value(props.get("Project")),
        "page_id": todo.get("id"),
    }


def _notion_title(todo: dict[str, Any]) -> str:
    props = todo.get("properties", {})
    if not isinstance(props, dict):
        return ""
    return _first_property_value(props.get("Name")) or _first_property_value(props.get("Title")) or ""


def _first_property_value(prop: Any) -> str | None:
    if not isinstance(prop, dict):
        return None
    for key in ("status", "select"):
        value = prop.get(key)
        if isinstance(value, dict) and isinstance(value.get("name"), str):
            return value["name"]
    for key in ("title", "rich_text"):
        value = prop.get(key)
        if isinstance(value, list) and value:
            first = value[0]
            if isinstance(first, dict):
                if isinstance(first.get("plain_text"), str):
                    return first["plain_text"]
                text = first.get("text")
                if isinstance(text, dict) and isinstance(text.get("content"), str):
                    return text["content"]
    if isinstance(prop.get("url"), str):
        return prop["url"]
    if isinstance(prop.get("name"), str):
        return prop["name"]
    return None
