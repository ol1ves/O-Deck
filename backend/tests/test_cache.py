import sqlite3
import time

import pytest

from cyberdeck.cache import Cache


def test_missing_key_returns_none(tmp_path):
    cache = Cache(db_path=tmp_path / "cache.db")
    assert cache.get("missing") is None
    assert cache.get_entry("missing") is None


def test_set_get_roundtrip(tmp_path):
    cache = Cache(db_path=tmp_path / "cache.db")
    payload = {"x": 1, "items": [1, 2, 3]}
    cache.set("k", payload)
    assert cache.get("k") == payload


def test_set_returns_true_on_new_key(tmp_path):
    cache = Cache(db_path=tmp_path / "cache.db")
    assert cache.set("k", {"v": 1}) is True


def test_set_false_when_unchanged(tmp_path):
    cache = Cache(db_path=tmp_path / "cache.db")
    assert cache.set("k", {"v": 1}) is True
    assert cache.set("k", {"v": 1}) is False


def test_set_true_when_changed(tmp_path):
    cache = Cache(db_path=tmp_path / "cache.db")
    assert cache.set("k", {"v": 1}) is True
    assert cache.set("k", {"v": 2}) is True


def test_entry_has_fetched_at_timestamp(tmp_path):
    cache = Cache(db_path=tmp_path / "cache.db")
    before = time.time()
    cache.set("k", {"v": 1})
    after = time.time()

    entry = cache.get_entry("k")
    assert entry is not None
    assert before <= entry.fetched_at <= after


def test_persistence_across_cache_instances(tmp_path):
    db = tmp_path / "cache.db"
    cache1 = Cache(db_path=db)
    payload = {"hello": "world"}
    cache1.set("k", payload)

    cache2 = Cache(db_path=db)
    cache2.load_from_db()
    assert cache2.get("k") == payload


def test_timestamp_preserved_across_load_from_db(tmp_path):
    db = tmp_path / "cache.db"
    cache1 = Cache(db_path=db)
    cache1.set("k", {"v": 1})
    original = cache1.get_entry("k")
    assert original is not None

    # Force fresh instance state and reload from SQLite.
    cache2 = Cache(db_path=db)
    cache2.load_from_db()
    loaded = cache2.get_entry("k")
    assert loaded is not None
    assert loaded.fetched_at == original.fetched_at

    # Cross-check DB row stores same timestamp too.
    with sqlite3.connect(db) as conn:
        row = conn.execute("SELECT fetched_at FROM cache WHERE key = ?", ("k",)).fetchone()
    assert row is not None
    assert row[0] == original.fetched_at


def test_get_returns_defensive_copy(tmp_path):
    cache = Cache(db_path=tmp_path / "cache.db")
    cache.set("k", {"nested": {"n": 1}})

    first = cache.get("k")
    assert first is not None
    first["nested"]["n"] = 999

    second = cache.get("k")
    assert second == {"nested": {"n": 1}}


def test_get_entry_payload_is_defensive_copy(tmp_path):
    cache = Cache(db_path=tmp_path / "cache.db")
    cache.set("k", {"nested": {"n": 1}})

    first = cache.get_entry("k")
    assert first is not None
    first.payload["nested"]["n"] = 999

    second = cache.get_entry("k")
    assert second is not None
    assert second.payload == {"nested": {"n": 1}}


def test_set_does_not_mutate_memory_when_persist_fails(tmp_path, monkeypatch):
    cache = Cache(db_path=tmp_path / "cache.db")
    cache.set("k", {"v": 1})
    before = cache.get_entry("k")
    assert before is not None

    def fail_persist(*_args, **_kwargs):
        raise RuntimeError("persist failed")

    monkeypatch.setattr(cache, "_persist", fail_persist)

    with pytest.raises(RuntimeError, match="persist failed"):
        cache.set("k", {"v": 2})

    after = cache.get_entry("k")
    assert after is not None
    assert after.payload == {"v": 1}
    assert after.fetched_at == before.fetched_at
