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

from pathlib import Path
from unittest.mock import Mock

from nextgis_toolbox.tasks.models import (
    ManagerState,
    TaskStatus,
    ToolboxResult,
    ToolboxTask,
)
from nextgis_toolbox.tasks.tasks_manager import TasksManager


def test_tasks_manager_submits_task_and_emits_signal(qgis_app) -> None:
    del qgis_app

    manager = TasksManager(Mock())
    repository = Mock()
    repository.submit_task.return_value = "task-1"
    manager._repository = repository
    captured_task_ids = []
    manager.task_created.connect(captured_task_ids.append)

    task_id = manager.submit_task(
        "hello",
        {"name": "value"},
        emailing=True,
    )

    assert task_id == "task-1"
    assert captured_task_ids == ["task-1"]
    repository.submit_task.assert_called_once_with(
        tool_name="hello",
        inputs={"name": "value"},
        emailing=True,
    )


def test_tasks_manager_delegates_read_operations(qgis_app) -> None:
    del qgis_app

    manager = TasksManager(Mock())
    repository = Mock()
    result = ToolboxResult(
        name="result",
        result_type="file",
        value="http://example.com/result.txt",
    )
    task = ToolboxTask(
        tool="hello",
        status=TaskStatus.SUCCESS,
        progress=100.0,
        error=None,
        results=[result],
        operation="hello",
        state=TaskStatus.SUCCESS,
    )
    saved_paths = [Path("/tmp/result.txt")]
    repository.task_information.return_value = task
    repository.get_results.return_value = [result]
    repository.download_results.return_value = saved_paths
    manager._repository = repository

    assert manager.retrieve_task("task-1") is task
    assert manager.get_results("task-1") == [result]
    assert manager.download_results([result], Path("/tmp")) == saved_paths

    repository.task_information.assert_called_once_with("task-1")
    repository.get_results.assert_called_once_with("task-1")
    repository.download_results.assert_called_once_with(
        [result],
        Path("/tmp"),
    )


def test_tasks_manager_tracks_catalog_runtime_state(qgis_app) -> None:
    del qgis_app

    manager = TasksManager(Mock())
    observed_states = []
    manager.state_changed.connect(observed_states.append)

    manager.on_tools_catalog_loading_finished(False, "broken")
    manager.on_tools_catalog_loading_finished(True, "")
    manager.unload()

    assert manager.state == ManagerState.LOADING
    assert manager.error_message == ""
    assert observed_states == [
        ManagerState.ERROR,
        ManagerState.LOADED,
        ManagerState.LOADING,
    ]
