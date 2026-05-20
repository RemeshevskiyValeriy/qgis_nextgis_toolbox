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
from pathlib import Path
from unittest.mock import Mock
from urllib.parse import parse_qs

import pytest

import nextgis_toolbox.nextgis_toolbox.sdk.client as client_module
from nextgis_toolbox.core.exceptions import NextgisToolboxFileWriteError
from nextgis_toolbox.nextgis_toolbox.sdk.client import ToolboxApiClient


def test_get_logs_request_and_parses_json_response(
    api_server,
    monkeypatch,
) -> None:
    api_server.add_json_response(
        "GET",
        "/api/tools/",
        {"data": [{"id": 1, "name": "public-tool"}]},
    )
    logger_mock = Mock()
    monkeypatch.setattr(client_module, "logger", logger_mock)
    client = ToolboxApiClient(endpoint=api_server.base_url)

    response = client.get("tools/", query_params={"param": "value"})

    assert response == {"data": [{"id": 1, "name": "public-tool"}]}
    request = api_server.requests[-1]
    assert request.method == "GET"
    assert request.path == "/api/tools/"
    assert parse_qs(request.query) == {"param": ["value"], "lang": ["en"]}
    assert logger_mock.debug.call_args_list[0].args == (
        f"↓ GET {api_server.base_url}/api/tools/?lang=en&param=value",
    )
    assert (
        logger_mock.debug.call_args_list[1]
        .args[0]
        .startswith(
            f"✓ GET {api_server.base_url}/api/tools/?lang=en&param=value "
            "finished with status 'success' in "
        )
    )


def test_post_logs_request_and_sends_json_payload(
    api_server,
    monkeypatch,
) -> None:
    api_server.add_json_response(
        "POST",
        "/api/tasks/",
        {"task_id": "task-1"},
    )
    logger_mock = Mock()
    monkeypatch.setattr(client_module, "logger", logger_mock)
    client = ToolboxApiClient(endpoint=api_server.base_url)

    response = client.post("tasks/", {"tool": "hello"})

    assert response == {"task_id": "task-1"}
    request = api_server.requests[-1]
    assert request.method == "POST"
    assert request.path == "/api/tasks/"
    assert json.loads(request.body.decode("utf-8")) == {
        "tool": "hello",
    }
    assert logger_mock.debug.call_args_list[0].args == (
        f"↑ POST {api_server.base_url}/api/tasks/?lang=en",
    )
    assert (
        logger_mock.debug.call_args_list[1]
        .args[0]
        .startswith(
            f"✓ POST {api_server.base_url}/api/tasks/?lang=en "
            "finished with status 'success' in "
        )
    )


def test_upload_posts_binary_payload_and_parses_json_response(
    api_server,
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "example.txt"
    source_path.write_text("payload", encoding="utf-8")
    api_server.add_json_response(
        "POST",
        "/api/upload",
        {"name": "example.txt", "local": {"uuid": "uuid-1"}, "s3": None},
    )
    logger_mock = Mock()
    monkeypatch.setattr(client_module, "logger", logger_mock)
    client = ToolboxApiClient(endpoint=api_server.base_url)

    response = client.upload(source_path)

    assert response == {
        "name": "example.txt",
        "local": {"uuid": "uuid-1"},
        "s3": None,
    }
    request = api_server.requests[-1]
    assert request.method == "POST"
    assert request.path == "/api/upload"
    assert request.body == b"payload"
    assert parse_qs(request.query) == {
        "filename": ["example.txt"],
        "format": ["json"],
    }
    assert logger_mock.debug.call_args_list[0].args == (
        f"↑ UPLOAD {api_server.base_url}/api/upload?filename=example.txt&format=json",
    )
    assert (
        logger_mock.debug.call_args_list[1]
        .args[0]
        .startswith(
            f"✓ UPLOAD {api_server.base_url}/api/upload?filename=example.txt&format=json "
            "finished with status 'success' in "
        )
    )


def test_download_logs_request_and_saves_file(
    api_server,
    monkeypatch,
    tmp_path: Path,
) -> None:
    payload = b"downloaded-result"
    api_server.add_response(
        "HEAD",
        "/files/result.txt",
        b"",
        headers={
            "Content-Disposition": 'attachment; filename="server-result.txt"',
            "Content-Type": "text/plain",
        },
    )
    api_server.add_response(
        "GET",
        "/files/result.txt",
        payload,
        headers={
            "Content-Disposition": 'attachment; filename="server-result.txt"',
            "Content-Type": "text/plain",
        },
    )
    logger_mock = Mock()
    monkeypatch.setattr(client_module, "logger", logger_mock)
    client = ToolboxApiClient(endpoint=api_server.base_url)
    destination_path = tmp_path / "downloads"

    saved_path = client.download(
        api_server.url("/files/result.txt"),
        destination_path,
    )

    assert saved_path == destination_path / "server-result.txt"
    assert saved_path.read_bytes() == payload
    assert api_server.requests[0].method == "HEAD"
    assert api_server.requests[1].method == "GET"
    assert api_server.requests[1].path == "/files/result.txt"
    assert logger_mock.debug.call_args_list[0].args == (
        f"↓ DOWNLOAD {api_server.url('/files/result.txt')}",
    )
    assert logger_mock.debug.call_args_list[1].args == (
        f"↓ HEAD {api_server.url('/files/result.txt')}",
    )
    assert (
        logger_mock.debug.call_args_list[2]
        .args[0]
        .startswith(
            f"✓ HEAD {api_server.url('/files/result.txt')} finished with status 'success' in "
        )
    )
    assert (
        logger_mock.debug.call_args_list[3]
        .args[0]
        .startswith(
            f"✓ DOWNLOAD {api_server.url('/files/result.txt')} finished with status 'success' in "
        )
    )


def test_download_wraps_directory_creation_errors(
    api_server,
    monkeypatch,
    tmp_path: Path,
) -> None:
    client = ToolboxApiClient(endpoint=api_server.base_url)
    api_server.add_response(
        "HEAD",
        "/files/result.txt",
        b"",
        headers={
            "Content-Disposition": 'attachment; filename="result.txt"',
            "Content-Type": "text/plain",
        },
    )

    def raise_os_error(
        self,
        mode: int = 0o777,
        parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
        del self, mode, parents, exist_ok
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "mkdir", raise_os_error)

    with pytest.raises(NextgisToolboxFileWriteError) as error:
        client.download(
            api_server.url("/files/result.txt"),
            tmp_path / "downloads" / "result.txt",
        )

    assert error.value.detail == "permission denied"
