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
from typing import Any, Dict, List

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

    def task_information(self, task_id: str) -> ToolboxTask:
        """Retrieve a task model from the API.

        :param task_id: Toolbox task identifier.

        :returns: Toolbox task model.
        """
        return ToolboxTask.from_json(self._api.task_information(task_id))

    def get_results(self, task_id: str) -> List[ToolboxResult]:
        """Retrieve result models for a task.

        :param task_id: Toolbox task identifier.

        :returns: Toolbox result models.
        """
        return self.task_information(task_id).results

    def download_results(
        self,
        results: List[ToolboxResult],
        directory: Path,
    ) -> List[Path]:
        """Download task result files to the target directory.

        :param results: Toolbox result descriptors.
        :param directory: Target directory.

        :returns: Saved file paths.
        """
        downloaded_paths: List[Path] = []

        for result in results:
            destination_path = directory / Path(result.value).name
            downloaded_paths.append(
                self._api.client.download(result.value, destination_path)
            )

        return downloaded_paths
