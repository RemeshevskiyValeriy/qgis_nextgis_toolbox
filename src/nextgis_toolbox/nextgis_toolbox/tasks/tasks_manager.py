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

from qgis.PyQt.QtCore import QObject

from nextgis_toolbox.nextgis_toolbox.tasks.api import TasksApi
from nextgis_toolbox.nextgis_toolbox.tasks.models import (
    ToolboxResult,
    ToolboxTask,
)
from nextgis_toolbox.nextgis_toolbox.tasks.repository import TasksRepository
from nextgis_toolbox.nextgis_toolbox.tasks.tasks_interface import (
    TasksInterface,
)


class TasksManager(TasksInterface):
    """Feature-level manager for Toolbox tasks."""

    def __init__(
        self,
        tasks_api: TasksApi,
        parent: Optional[QObject] = None,
    ) -> None:
        """Initialize tasks manager.

        :param tasks_api: API for managing tasks.
        :param parent: Optional Qt parent.
        """
        super().__init__(parent)
        self._repository = TasksRepository(tasks_api)

    def set_api(self, tasks_api: TasksApi) -> None:
        """Set the API for managing tasks.

        :param tasks_api: API for managing tasks.
        """
        self._repository.set_api(tasks_api)

    def load(self) -> None:
        """Load the tasks feature."""
        pass

    def unload(self) -> None:
        """Unload the tasks feature and clear runtime state."""
        pass

    def submit_task(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        emailing: bool = False,
    ) -> str:
        """Submit Toolbox task and emit ``task_created``.

        :param tool_name: Toolbox tool identifier.
        :param inputs: Tool input values.
        :param emailing: Enable result emailing.

        :returns: Created task identifier.
        """
        task_id = self._repository.submit_task(
            tool_name=tool_name,
            inputs=inputs,
            emailing=emailing,
        )

        return task_id

    def retrieve_task(self, task_id: str) -> ToolboxTask:
        """Retrieve Toolbox task information.

        :param task_id: Toolbox task identifier.

        :returns: Toolbox task model.
        """
        return self._repository.retrieve_task(task_id)

    def get_results(self, task_id: str) -> List[ToolboxResult]:
        """Retrieve Toolbox task results.

        :param task_id: Toolbox task identifier.

        :returns: Toolbox result models.
        """
        return self._repository.get_results(task_id)

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
        return self._repository.download_results(results, directory)
