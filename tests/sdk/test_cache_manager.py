# NextGIS Toolbox
# Copyright (C) 2026  NextGIS
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or any
# later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, see <https://www.gnu.org/licenses/>.

import json
from datetime import datetime, timedelta, timezone

import nextgis_toolbox.api.cache_manager as cache_manager_module
from nextgis_toolbox.api.cache_manager import CacheManager


def test_cache_manager_stores_payloads(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        cache_manager_module.QStandardPaths,
        "writableLocation",
        lambda *_args, **_kwargs: str(tmp_path),
    )
    manager = CacheManager("cache-id")
    payload = {"id": 1, "name": "tool"}

    manager.put("tools/tool", payload)

    assert manager.get("tools/tool") == payload

    cache_file = (
        tmp_path
        / "NGToolbox"
        / "cache"
        / "default"
        / "cache-id"
        / "index.json"
    )
    stored_payload = json.loads(cache_file.read_text(encoding="utf-8"))
    assert stored_payload["id"] == "cache-id"
    assert "tools/tool" in stored_payload["entries"]


def test_cache_manager_invalidates_expired_entries(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(
        cache_manager_module.QStandardPaths,
        "writableLocation",
        lambda *_args, **_kwargs: str(tmp_path),
    )
    manager = CacheManager("cache-id", cache_ttl_hours=1)
    manager.put("tools/tool", {"id": 1})

    cache_file = (
        tmp_path
        / "NGToolbox"
        / "cache"
        / "default"
        / "cache-id"
        / "index.json"
    )
    stored_payload = json.loads(cache_file.read_text(encoding="utf-8"))
    stored_payload["entries"]["tools/tool"]["created_at"] = (
        datetime.now(timezone.utc) - timedelta(hours=2)
    ).isoformat()
    cache_file.write_text(json.dumps(stored_payload), encoding="utf-8")

    assert manager.get("tools/tool") is None

    refreshed_payload = json.loads(cache_file.read_text(encoding="utf-8"))
    assert refreshed_payload["entries"] == {}


def test_cache_manager_stores_binary_payloads(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        cache_manager_module.QStandardPaths,
        "writableLocation",
        lambda *_args, **_kwargs: str(tmp_path),
    )
    manager = CacheManager("cache-id")
    binary_content = b"png-bytes"

    manager.put_bytes("help-images/demo.png", binary_content)

    cached_content = manager.get_bytes("help-images/demo.png")

    assert cached_content == binary_content

    cache_file = (
        tmp_path
        / "NGToolbox"
        / "cache"
        / "default"
        / "cache-id"
        / "index.json"
    )
    stored_payload = json.loads(cache_file.read_text(encoding="utf-8"))
    blob_path = stored_payload["entries"]["help-images/demo.png"]["blob_path"]
    assert (
        tmp_path / "NGToolbox" / "cache" / "default" / "cache-id" / blob_path
    ).exists()


def test_cache_manager_returns_blob_path(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        cache_manager_module.QStandardPaths,
        "writableLocation",
        lambda *_args, **_kwargs: str(tmp_path),
    )
    manager = CacheManager("cache-id")
    binary_content = b"png-bytes"

    manager.put_bytes("help-images/demo.png", binary_content)
    cached_path = manager.get_path("help-images/demo.png")

    assert cached_path is not None
    assert cached_path.read_bytes() == binary_content


def test_cache_manager_removes_stale_metadata_when_blob_is_missing(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(
        cache_manager_module.QStandardPaths,
        "writableLocation",
        lambda *_args, **_kwargs: str(tmp_path),
    )
    manager = CacheManager("cache-id")
    manager.put_bytes("help-images/demo.png", b"png-bytes")

    cache_file = (
        tmp_path
        / "NGToolbox"
        / "cache"
        / "default"
        / "cache-id"
        / "index.json"
    )
    stored_payload = json.loads(cache_file.read_text(encoding="utf-8"))
    blob_path = stored_payload["entries"]["help-images/demo.png"]["blob_path"]
    (tmp_path / "NGToolbox" / "cache" / "default" / "cache-id" / blob_path).unlink()

    assert manager.get_path("help-images/demo.png") is None

    refreshed_payload = json.loads(cache_file.read_text(encoding="utf-8"))
    assert refreshed_payload["entries"] == {}
