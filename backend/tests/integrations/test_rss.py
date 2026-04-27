from __future__ import annotations

from time import gmtime
from unittest.mock import AsyncMock, MagicMock

import pytest

from cyberdeck.cache import Cache
from cyberdeck.config import AppConfig, RSSConfig, RSSFeedConfig, Settings
from cyberdeck.integrations.rss import RSSIntegration, _age_str, _dedupe
from cyberdeck.ws import WSManager


def make_config(*, feeds: list[RSSFeedConfig], headline_stack_size: int = 3) -> Settings:
    return Settings(
        app=AppConfig(
            rss=RSSConfig(
                feeds=feeds,
                headline_stack_size=headline_stack_size,
            )
        )
    )


def make_integration(config: Settings | None = None, cache=None, ws=None) -> RSSIntegration:
    return RSSIntegration(
        cache=cache or MagicMock(),
        ws_manager=ws or MagicMock(),
        config=config
        or make_config(feeds=[RSSFeedConfig(name="Tech", url="https://example.com/tech.xml")]),
    )


def parsed_feed(*entries: dict) -> MagicMock:
    return MagicMock(entries=list(entries))


def patch_feed_fetch(monkeypatch, payloads: dict[str, MagicMock], parse=None) -> None:
    class FakeResponse:
        def __init__(self, content: bytes) -> None:
            self.content = content

        def raise_for_status(self) -> None:
            pass

    class FakeClient:
        def __init__(self, *, timeout: float) -> None:
            self.timeout = timeout

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

        async def get(self, url: str) -> FakeResponse:
            return FakeResponse(url.encode())

    def parse_feed(content: bytes) -> MagicMock:
        return payloads[content.decode()]

    monkeypatch.setattr("cyberdeck.integrations.rss.httpx.AsyncClient", FakeClient)
    monkeypatch.setattr("cyberdeck.integrations.rss.feedparser.parse", parse or parse_feed)


def entry(
    *,
    title: str,
    link: str,
    id: str | None = None,
    summary: str = "",
    published_parsed=None,
) -> dict:
    data = {
        "title": title,
        "link": link,
        "summary": summary,
        "published_parsed": published_parsed,
    }
    if id is not None:
        data["id"] = id
    return data


@pytest.mark.asyncio
async def test_fetch_uses_bounded_http_client_and_parses_response_bytes(monkeypatch):
    calls: dict[str, object] = {}
    feed = RSSFeedConfig(name="Tech", url="https://example.com/tech.xml")

    class FakeResponse:
        content = b"<rss>feed bytes</rss>"

        def raise_for_status(self) -> None:
            calls["raised"] = True

    class FakeClient:
        def __init__(self, *, timeout: float) -> None:
            calls["timeout"] = timeout

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

        async def get(self, url: str) -> FakeResponse:
            calls["url"] = url
            return FakeResponse()

    def parse_feed(content: bytes) -> MagicMock:
        calls["parsed_content"] = content
        assert content == b"<rss>feed bytes</rss>"
        return parsed_feed(entry(id="1", title="One", link="https://example.com/1"))

    monkeypatch.setattr("cyberdeck.integrations.rss.httpx.AsyncClient", FakeClient)
    monkeypatch.setattr("cyberdeck.integrations.rss.feedparser.parse", parse_feed)

    result = await make_integration(config=make_config(feeds=[feed])).fetch()

    assert calls == {
        "timeout": 15.0,
        "url": "https://example.com/tech.xml",
        "raised": True,
        "parsed_content": b"<rss>feed bytes</rss>",
    }
    assert result["ticker"] == ["TECH · One"]


def test_integration_event_contract():
    integration = make_integration()

    assert integration.name == "rss"
    assert integration.event_name() == "rss.update"


def test_dedupe_removes_duplicate_ids_preserving_first():
    first = {"id": "same", "link": "https://example.com/a", "title": "first"}
    duplicate = {"id": "same", "link": "https://example.com/b", "title": "duplicate"}
    unique = {"id": "other", "link": "https://example.com/c", "title": "unique"}

    assert _dedupe([first, duplicate, unique]) == [first, unique]


def test_dedupe_removes_duplicate_links_preserving_first():
    first = {"id": "a", "link": "https://example.com/same", "title": "first"}
    duplicate = {"id": "b", "link": "https://example.com/same", "title": "duplicate"}
    unique = {"id": "c", "link": "https://example.com/unique", "title": "unique"}

    assert _dedupe([first, duplicate, unique]) == [first, unique]


def test_age_str_formats_minutes_hours_days_and_empty_values(monkeypatch):
    monkeypatch.setattr("cyberdeck.integrations.rss.time.time", lambda: 26 * 60 * 60)

    assert _age_str(None) == ""
    assert _age_str(gmtime(26 * 60 * 60 - 5 * 60)) == "5m"
    assert _age_str(gmtime(23 * 60 * 60)) == "3h"
    assert _age_str(gmtime(0)) == "1d"


@pytest.mark.asyncio
async def test_fetch_maps_entries_from_multiple_feeds(monkeypatch):
    monkeypatch.setattr("cyberdeck.integrations.rss.time.time", lambda: 26 * 60 * 60)
    feeds = [
        RSSFeedConfig(name="Tech", url="https://example.com/tech.xml"),
        RSSFeedConfig(name="News", url="https://example.com/news.xml"),
    ]
    payloads = {
        "https://example.com/tech.xml": parsed_feed(
            entry(
                id="tech-1",
                title="New laptop",
                link="https://example.com/laptop",
                summary="x" * 250,
                published_parsed=gmtime(24 * 60 * 60),
            )
        ),
        "https://example.com/news.xml": parsed_feed(
            entry(
                id="news-1",
                title="City update",
                link="https://example.com/city",
                summary="Short summary",
                published_parsed=gmtime(0),
            )
        ),
    }

    patch_feed_fetch(monkeypatch, payloads)

    result = await make_integration(config=make_config(feeds=feeds)).fetch()

    assert result["items"] == [
        {
            "id": "tech-1",
            "link": "https://example.com/laptop",
            "title": "New laptop",
            "src": "Tech",
            "summary": "x" * 200,
            "age": "2h",
        },
        {
            "id": "news-1",
            "link": "https://example.com/city",
            "title": "City update",
            "src": "News",
            "summary": "Short summary",
            "age": "1d",
        },
    ]


@pytest.mark.asyncio
async def test_fetch_dedupes_across_feeds_and_builds_ticker(monkeypatch):
    feeds = [
        RSSFeedConfig(name="Tech", url="https://example.com/tech.xml"),
        RSSFeedConfig(name="News", url="https://example.com/news.xml"),
    ]
    payloads = {
        "https://example.com/tech.xml": parsed_feed(
            entry(id="shared", title="First title", link="https://example.com/a")
        ),
        "https://example.com/news.xml": parsed_feed(
            entry(id="shared", title="Duplicate title", link="https://example.com/b"),
            entry(id="unique", title="Second title", link="https://example.com/c"),
        ),
    }
    patch_feed_fetch(monkeypatch, payloads)

    result = await make_integration(config=make_config(feeds=feeds)).fetch()

    assert [item["title"] for item in result["items"]] == ["First title", "Second title"]
    assert result["ticker"] == ["TECH · First title", "NEWS · Second title"]


@pytest.mark.asyncio
async def test_fetch_limits_headlines_to_configured_stack_size(monkeypatch):
    feed = RSSFeedConfig(name="Tech", url="https://example.com/tech.xml")
    patch_feed_fetch(
        monkeypatch,
        {
            "https://example.com/tech.xml": parsed_feed(
                entry(id="1", title="One", link="https://example.com/1"),
                entry(id="2", title="Two", link="https://example.com/2"),
                entry(id="3", title="Three", link="https://example.com/3"),
            )
        },
    )

    result = await make_integration(
        config=make_config(feeds=[feed], headline_stack_size=2)
    ).fetch()

    assert result["headlines"] == [
        {"src": "Tech", "title": "One", "age": ""},
        {"src": "Tech", "title": "Two", "age": ""},
    ]


@pytest.mark.asyncio
async def test_fetch_limits_ticker_to_twenty_items(monkeypatch):
    feed = RSSFeedConfig(name="Tech", url="https://example.com/tech.xml")
    patch_feed_fetch(
        monkeypatch,
        {
            "https://example.com/tech.xml": parsed_feed(
                *[
                    entry(id=str(i), title=f"Item {i}", link=f"https://example.com/{i}")
                    for i in range(25)
                ]
            )
        },
    )

    result = await make_integration(config=make_config(feeds=[feed])).fetch()

    assert len(result["ticker"]) == 20
    assert result["ticker"][0] == "TECH · Item 0"
    assert result["ticker"][-1] == "TECH · Item 19"


@pytest.mark.asyncio
async def test_run_swallows_feedparser_error_and_increments_error_count(monkeypatch, tmp_path):
    feed = RSSFeedConfig(name="Tech", url="https://example.com/tech.xml")

    def parse_raises(url: str) -> None:
        raise RuntimeError(f"boom {url}")

    patch_feed_fetch(monkeypatch, {"https://example.com/tech.xml": parsed_feed()}, parse=parse_raises)
    integration = make_integration(
        config=make_config(feeds=[feed]),
        cache=Cache(db_path=tmp_path / "c.db"),
        ws=WSManager(),
    )

    await integration.run()

    assert integration.status["error_count"] == 1


@pytest.mark.asyncio
async def test_run_writes_cache_and_broadcasts_rss_update(monkeypatch, tmp_path):
    feed = RSSFeedConfig(name="Tech", url="https://example.com/tech.xml")
    patch_feed_fetch(
        monkeypatch,
        {
            "https://example.com/tech.xml": parsed_feed(
                entry(id="1", title="One", link="https://example.com/1")
            )
        },
    )
    cache = Cache(db_path=tmp_path / "c.db")
    ws = MagicMock()
    ws.broadcast = AsyncMock()
    integration = make_integration(config=make_config(feeds=[feed]), cache=cache, ws=ws)

    await integration.run()

    assert cache.get("rss")["ticker"] == ["TECH · One"]
    ws.broadcast.assert_awaited_once_with(
        "rss.update",
        {
            "items": [
                {
                    "id": "1",
                    "link": "https://example.com/1",
                    "title": "One",
                    "src": "Tech",
                    "summary": "",
                    "age": "",
                }
            ],
            "headlines": [{"src": "Tech", "title": "One", "age": ""}],
            "ticker": ["TECH · One"],
        },
    )
