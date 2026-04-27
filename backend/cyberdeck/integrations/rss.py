from __future__ import annotations

import asyncio
import calendar
import time
from typing import Any

import feedparser
import httpx

from cyberdeck.integrations.base import Integration


class RSSIntegration(Integration):
    name = "rss"

    def event_name(self) -> str:
        return "rss.update"

    async def fetch(self) -> dict[str, Any]:
        items: list[dict[str, str]] = []

        for feed in self.config.app.rss.feeds:
            parsed = await self._parse_feed(feed.url)
            entries = getattr(parsed, "entries", [])
            if not isinstance(entries, list):
                continue

            for raw_entry in entries:
                title = _entry_value(raw_entry, "title")
                link = _entry_value(raw_entry, "link")
                item_id = _entry_value(raw_entry, "id") or link
                items.append(
                    {
                        "id": item_id,
                        "link": link,
                        "title": title,
                        "src": feed.name,
                        "summary": _entry_value(raw_entry, "summary")[:200],
                        "age": _age_str(_entry_raw_value(raw_entry, "published_parsed")),
                    }
                )

        deduped = _dedupe(items)
        return {
            "items": deduped,
            "headlines": [
                {"src": item["src"], "title": item["title"], "age": item["age"]}
                for item in deduped[: self.config.app.rss.headline_stack_size]
            ],
            "ticker": [f"{item['src'].upper()} · {item['title']}" for item in deduped[:20]],
        }

    async def _parse_feed(self, url: str) -> Any:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            content = response.content

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, feedparser.parse, content)


def _dedupe(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen_ids: set[str] = set()
    seen_links: set[str] = set()
    deduped: list[dict[str, str]] = []

    for item in items:
        item_id = item.get("id", "")
        link = item.get("link", "")
        if (item_id and item_id in seen_ids) or (link and link in seen_links):
            continue

        deduped.append(item)
        if item_id:
            seen_ids.add(item_id)
        if link:
            seen_links.add(link)

    return deduped


def _age_str(published_parsed: Any) -> str:
    if published_parsed is None:
        return ""

    try:
        published_ts = calendar.timegm(published_parsed)
    except (TypeError, ValueError):
        return ""

    age_seconds = max(0, int(time.time() - published_ts))
    if age_seconds < 60 * 60:
        return f"{age_seconds // 60}m"
    if age_seconds < 24 * 60 * 60:
        return f"{age_seconds // (60 * 60)}h"
    return f"{age_seconds // (24 * 60 * 60)}d"


def _entry_value(entry: Any, key: str) -> str:
    value = _entry_raw_value(entry, key)
    return str(value or "")


def _entry_raw_value(entry: Any, key: str) -> Any:
    if isinstance(entry, dict):
        return entry.get(key)
    return getattr(entry, key, None)
