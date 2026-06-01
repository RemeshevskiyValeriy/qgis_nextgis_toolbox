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
import shutil
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, Optional

from qgis.PyQt.QtCore import QStandardPaths

from nextgis_toolbox.core.exceptions import (
    NextgisToolboxCacheReadError,
    ToolboxCacheFormatError,
    ToolboxCacheWriteError,
)
from nextgis_toolbox.core.logging import logger
from nextgis_toolbox.settings.nextgis_toolbox_settings import (
    NextgisToolboxSettings,
)


class CacheManager:
    def __init__(
        self,
        scope_id: str,
        qgis_profile: str = "default",
        cache_ttl_hours: Optional[int] = None,
    ) -> None:
        self._scope_id = scope_id
        self._qgis_profile = qgis_profile or "default"
        self._cache_directory = (
            Path(
                QStandardPaths.writableLocation(
                    QStandardPaths.StandardLocation.CacheLocation
                )
            )
            / "NGToolbox"
            / "cache"
            / self._qgis_profile
            / scope_id
        )
        self._metadata_path = self._cache_directory / "index.json"

        if cache_ttl_hours is not None:
            self._cache_ttl_hours = cache_ttl_hours
        else:
            self._cache_ttl_hours = NextgisToolboxSettings().cache_ttl_hours

    def get(
        self,
        path: str,
        cache_ttl_hours: Optional[int] = None,
    ) -> Optional[Any]:
        content = self.get_bytes(path, cache_ttl_hours=cache_ttl_hours)
        if content is None:
            return None

        try:
            return json.loads(content.decode("utf-8"))
        except (TypeError, ValueError, UnicodeDecodeError) as error:
            wrapped_error = ToolboxCacheFormatError(
                log_message=f"Failed to decode cached JSON '{path}'."
            )
            wrapped_error.add_note(f"Technical details: {error}")
            raise wrapped_error from error

    def put(self, path: str, data: Any) -> None:
        try:
            content = json.dumps(data, sort_keys=True).encode("utf-8")
        except (TypeError, ValueError) as error:
            wrapped_error = ToolboxCacheWriteError(
                log_message=f"Failed to serialize cached JSON '{path}'."
            )
            wrapped_error.add_note(f"Technical details: {error}")
            raise wrapped_error from error

        self.put_bytes(path, content)

    def get_bytes(
        self,
        path: str,
        cache_ttl_hours: Optional[int] = None,
    ) -> Optional[bytes]:
        blob_path = self.get_path(path, cache_ttl_hours=cache_ttl_hours)
        if blob_path is None:
            return None

        try:
            content = blob_path.read_bytes()
        except OSError as error:
            wrapped_error = NextgisToolboxCacheReadError(
                log_message=f"Failed to read cached blob '{path}'."
            )
            wrapped_error.add_note(f"Technical details: {error}")
            raise wrapped_error from error

        return content

    def get_path(
        self,
        path: str,
        cache_ttl_hours: Optional[int] = None,
    ) -> Optional[Path]:
        payload = self._read_payload()
        cache_entry = payload["entries"].get(path)
        if cache_entry is None:
            return None

        if self._is_expired(
            cache_entry.get("created_at"),
            cache_ttl_hours,
        ):
            self._expire_entry(payload, path, cache_entry)
            logger.debug(f"Cache expired: {path}")
            return None

        blob_path = self._resolve_blob_path(cache_entry.get("blob_path"))
        if blob_path is None:
            self._expire_entry(payload, path, cache_entry)
            logger.debug(f"Cache blob missing: {path}")
            return None

        # logger.debug(f"Cache hit: {path}")
        return blob_path

    def put_bytes(self, path: str, content: bytes) -> None:
        payload = self._read_payload()
        blob_relative_path = self._blob_relative_path(path)
        blob_path = self._cache_directory / blob_relative_path

        try:
            blob_path.parent.mkdir(parents=True, exist_ok=True)
            blob_path.write_bytes(content)
        except OSError as error:
            wrapped_error = ToolboxCacheWriteError(
                log_message=f"Failed to write cached blob '{path}'."
            )
            wrapped_error.add_note(f"Technical details: {error}")
            raise wrapped_error from error

        payload["entries"][path] = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "blob_path": str(blob_relative_path),
        }
        self._write_payload(payload)

    def invalidate(self) -> None:
        if not self._cache_directory.exists():
            return

        try:
            shutil.rmtree(self._cache_directory)
        except OSError as error:
            wrapped_error = ToolboxCacheWriteError(
                log_message=(
                    f"Failed to clear cache directory '{self._cache_directory}'."
                )
            )
            wrapped_error.add_note(f"Technical details: {error}")
            raise wrapped_error from error

    def invalidate_entry(self, path: str) -> None:
        payload = self._read_payload()
        cache_entry = payload["entries"].get(path)
        if cache_entry is None:
            return

        self._expire_entry(payload, path, cache_entry)

    def _default_payload(self) -> Dict[str, Any]:
        return {"id": self._scope_id, "version": 1, "entries": {}}

    def _read_payload(self) -> Dict[str, Any]:
        if not self._metadata_path.exists():
            return self._default_payload()

        try:
            payload = json.loads(
                self._metadata_path.read_text(encoding="utf-8")
            )
        except (OSError, TypeError, ValueError) as error:
            wrapped_error = NextgisToolboxCacheReadError(
                log_message=(
                    f"Failed to read cache file '{self._metadata_path}'."
                )
            )
            wrapped_error.add_note(f"Technical details: {error}")
            raise wrapped_error from error

        if not isinstance(payload, dict):
            wrapped_error = ToolboxCacheFormatError(
                log_message=(
                    f"Cache file '{self._metadata_path}' does not contain an object."
                )
            )
            wrapped_error.add_note(f"Payload type: {type(payload)}")
            raise wrapped_error

        cache_entries = payload.get("entries", {})
        if not isinstance(cache_entries, dict):
            cache_entries = {}

        return {
            "id": payload.get("id", self._scope_id),
            "version": payload.get("version", 1),
            "entries": self._normalize_cache_entries(cache_entries),
        }

    def _normalize_cache_entries(
        self,
        cache_entries: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        normalized_entries: Dict[str, Dict[str, Any]] = {}

        for path, cache_entry in cache_entries.items():
            if not isinstance(path, str):
                continue

            if not isinstance(cache_entry, dict):
                continue

            normalized_entries[path] = cache_entry

        return normalized_entries

    def _write_payload(self, payload: Dict[str, Any]) -> None:
        try:
            self._cache_directory.mkdir(parents=True, exist_ok=True)
            self._metadata_path.write_text(
                json.dumps(payload, indent=2, sort_keys=True),
                encoding="utf-8",
            )
        except (OSError, TypeError, ValueError) as error:
            wrapped_error = ToolboxCacheWriteError(
                log_message=(
                    f"Failed to write cache file '{self._metadata_path}'."
                )
            )
            wrapped_error.add_note(f"Technical details: {error}")
            raise wrapped_error from error

    def _blob_relative_path(self, path: str) -> Path:
        digest = sha256(path.encode("utf-8")).hexdigest()
        return Path("blobs") / digest[:2] / digest[2:4] / f"{digest}.bin"

    def _resolve_blob_path(self, blob_path: Any) -> Optional[Path]:
        if not isinstance(blob_path, str):
            return None

        resolved_path = self._cache_directory / Path(blob_path)
        if not resolved_path.exists():
            return

        return resolved_path

    def _expire_entry(
        self,
        payload: Dict[str, Any],
        path: str,
        cache_entry: Dict[str, Any],
    ) -> None:
        self._delete_blob(cache_entry.get("blob_path"))
        payload["entries"].pop(path, None)
        self._write_payload(payload)

    def _delete_blob(self, blob_path: Any) -> None:
        resolved_path = self._resolve_blob_path(blob_path)
        if resolved_path is None:
            return

        try:
            resolved_path.unlink()
        except OSError as error:
            wrapped_error = ToolboxCacheWriteError(
                log_message=(
                    f"Failed to delete cached blob '{resolved_path}'."
                )
            )
            wrapped_error.add_note(f"Technical details: {error}")
            raise wrapped_error from error

    def _is_expired(
        self,
        cached_at: Any,
        cache_ttl_hours: Optional[int] = None,
    ) -> bool:
        if not isinstance(cached_at, str):
            return True

        try:
            cached_datetime = datetime.fromisoformat(cached_at)
        except ValueError:
            return True

        if cached_datetime.tzinfo is None:
            cached_datetime = cached_datetime.replace(tzinfo=timezone.utc)

        ttl_hours = self._cache_ttl_hours
        if cache_ttl_hours is not None:
            ttl_hours = cache_ttl_hours

        expires_at = cached_datetime + timedelta(hours=ttl_hours)
        return datetime.now(timezone.utc) >= expires_at
