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
from typing import Any, Dict, List, Optional

from nextgis_toolbox.nextgis_toolbox.tasks.api import TasksApi
from nextgis_toolbox.nextgis_toolbox.tasks.models import (
    ToolboxResult,
    ToolboxTask,
)


class TasksRepository:
    """Repository for Toolbox task models and result files."""

    def __init__(self, api: TasksApi) -> None:
        """Initialize repository.

        :param api: Tasks API gateway.
        """
        self._api = api

    def set_api(self, api: TasksApi) -> None:
        """Set the API gateway for managing tasks.

        :param api: Tasks API gateway.
        """
        self._api = api

    def submit_task(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        emailing: bool = False,
    ) -> str:
        """Submit task and return created task identifier.

        :param tool_name: Toolbox tool identifier.
        :param inputs: Tool input values.
        :param emailing: Enable result emailing.

        :returns: Created task identifier.
        """
        response_data = self._api.submit_task(
            tool_name=tool_name,
            inputs=inputs,
            emailing=emailing,
        )

        return response_data["task_id"]

    def retrieve_task(self, task_id: str) -> ToolboxTask:
        """Retrieve and map task information.

        :param task_id: Toolbox task identifier.

        :returns: Toolbox task model.
        """
        return self._task_from_dict(self._api.retrieve_task(task_id))

    def get_results(self, task_id: str) -> List[ToolboxResult]:
        """Retrieve task result descriptors.

        :param task_id: Toolbox task identifier.

        :returns: Toolbox result models.
        """
        return self.retrieve_task(task_id).results

    def _download_result(
        self,
        result: ToolboxResult,
        directory: Path,
        filename: Optional[str] = None,
    ) -> Path:
        """Download one Toolbox result file.

        :param result: Toolbox result descriptor.
        :param directory: Target directory.
        :param filename: Optional output filename.

        :returns: Saved file path.
        """
        return self._download_result_content(result.value, directory, filename)

    def download_results(
        self,
        results: List[ToolboxResult],
        directory: Path,
    ) -> List[Path]:
        """Download multiple Toolbox result files.

        :param results: Toolbox result descriptors.
        :param directory: Target directory.

        :returns: Saved file paths.
        """
        return [self._download_result(result, directory) for result in results]

    def _download_result_content(
        self,
        url: str,
        directory: Path,
        filename: Optional[str] = None,
    ) -> Path:
        """Download file from NextGIS Toolbox API.

        :param url: File URL.
        :param directory: Target directory.
        :param filename: Optional output filename.

        :returns: Saved file path.
        """
        content = self._api.download_result_content(url)

        if filename is None:
            filename = Path(url).name

        file_path = directory / filename
        file_path.write_bytes(content)

        return file_path

    def to_dict(self, task: ToolboxTask) -> Dict[str, Any]:
        """Convert task model to raw API-compatible dictionary.

        :param task: Toolbox task model.

        :returns: Raw task dictionary.
        """
        return {
            "tool": task.tool,
            "status": task.status,
            "progress": task.progress,
            "error": task.error,
            "output": [self.result_to_dict(result) for result in task.results],
            "operation": task.operation,
            "state": task.state,
        }

    def result_to_dict(self, result: ToolboxResult) -> Dict[str, Any]:
        """Convert result model to raw API-compatible dictionary.

        :param result: Toolbox result model.

        :returns: Raw result dictionary.
        """
        return {
            "name": result.name,
            "type": result.result_type,
            "value": result.value,
        }

    def _task_from_dict(self, data: Dict[str, Any]) -> ToolboxTask:
        """Build task model from raw API payload.

        :param data: Raw API payload.

        :returns: Parsed Toolbox task model.
        """
        return ToolboxTask(
            tool=data["tool"],
            status=data["status"],
            progress=data["progress"],
            error=data.get("error"),
            results=[
                self._result_from_dict(result_data)
                for result_data in data.get("output", [])
            ],
            operation=data["operation"],
            state=data["state"],
        )

    def _result_from_dict(self, data: Dict[str, Any]) -> ToolboxResult:
        """Build result model from raw API payload.

        :param data: Raw API payload.

        :returns: Parsed Toolbox result model.
        """
        return ToolboxResult(
            name=data["name"],
            result_type=data["type"],
            value=data["value"],
        )
