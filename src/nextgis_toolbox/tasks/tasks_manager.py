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

from typing import Any, Dict, Optional

from qgis.core import QgsFeedback
from qgis.PyQt.QtCore import QObject

from nextgis_toolbox.tasks.api import TasksApi
from nextgis_toolbox.tasks.models import (
    ToolboxTaskInformation,
)
from nextgis_toolbox.tasks.repository import TasksRepository
from nextgis_toolbox.tasks.tasks_interface import (
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

    def api(self) -> "TasksApi":
        """Return the API for managing tasks.

        :returns: Tasks API instance.
        """
        return self._repository.api()

    def set_api(self, tasks_api: TasksApi) -> None:
        """Set the API for managing tasks.

        :param tasks_api: API for managing tasks.
        """
        self._repository.set_api(tasks_api)

    def load(self) -> None:
        """Load the tasks feature."""

    def unload(self) -> None:
        """Unload the tasks feature."""

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

        self.task_created.emit(task_id)

        return task_id

    def task_information(
        self,
        task_id: str,
        feedback: Optional[QgsFeedback] = None,
    ) -> ToolboxTaskInformation:
        """Retrieve Toolbox task information.

        :param task_id: Toolbox task identifier.
        :param feedback: Optional feedback object for progress reporting.

        :returns: Toolbox task model.
        """
        return self._repository.task_information(
            task_id,
            feedback=feedback,
        )
