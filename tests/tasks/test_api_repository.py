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

from nextgis_toolbox.api.client import ToolboxApiClient
from nextgis_toolbox.tasks.api import TasksApi
from nextgis_toolbox.tasks.models import TaskStatus
from nextgis_toolbox.tasks.repository import TasksRepository


def build_task_payload(result_url: str) -> dict:
    return {
        "error": None,
        "operation": "hello",
        "output": [
            {
                "name": "result",
                "type": "file",
                "value": result_url,
            }
        ],
        "progress": 100.0,
        "state": "SUCCESS",
        "status": "SUCCESS",
        "tool": "hello",
    }


def test_tasks_api_submits_payload_and_fetches_task(api_server) -> None:
    task_payload = build_task_payload(api_server.url("/files/result.txt"))
    api_server.add_json_response(
        "POST",
        "/api/tasks/",
        {"task_id": "task-1"},
    )
    api_server.add_json_response(
        "GET",
        "/api/tasks/task-1",
        task_payload,
    )
    api = TasksApi(ToolboxApiClient(endpoint=api_server.base_url))

    response = api.submit_task("hello", {"name": "value"}, emailing=True)
    task_information = api.task_information("task-1")

    assert response == "task-1"
    assert task_information == task_payload
    assert json.loads(api_server.requests[0].body.decode("utf-8")) == {
        "emailing": True,
        "inputs": {"name": "value"},
        "mode": "api",
        "tool": "hello",
    }
    assert api_server.requests[1].headers["Cache-Control"] == "no-cache"
    assert api_server.requests[1].headers["Pragma"] == "no-cache"


def test_tasks_repository_submits_and_fetches_task(api_server) -> None:
    task_payload = build_task_payload(api_server.url("/files/result.txt"))
    api_server.add_json_response(
        "POST",
        "/api/tasks/",
        {"task_id": "task-1"},
    )
    api_server.add_json_response(
        "GET",
        "/api/tasks/task-1",
        task_payload,
    )
    api_server.add_json_response(
        "GET",
        "/api/tasks/task-1",
        task_payload,
    )
    repository = TasksRepository(
        TasksApi(ToolboxApiClient(endpoint=api_server.base_url))
    )

    task_id = repository.submit_task("hello", {"name": "value"})
    task = repository.task_information(task_id)

    assert task_id == "task-1"
    assert task.tool == "hello"
    assert task.status == TaskStatus.SUCCESS
    assert len(task.results) == 1
    assert task.results[0].name == "result"
    assert task.results[0].value == api_server.url("/files/result.txt")


def test_tasks_api_builds_public_urls_from_endpoint_path() -> None:
    api = TasksApi(
        ToolboxApiClient(
            endpoint="https://toolbox.nextgis.test/custom-instance"
        )
    )

    assert api.tasks_history_url().toString() == (
        "https://toolbox.nextgis.test/custom-instance/orders"
    )
    assert api.task_results_url("task-1").toString() == (
        "https://toolbox.nextgis.test/custom-instance/orders?selected=task-1"
    )
