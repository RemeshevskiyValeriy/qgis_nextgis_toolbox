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

from nextgis_toolbox.core.logging import logger
from nextgis_toolbox.nextgis_toolbox.tasks.api import TasksApi
from nextgis_toolbox.nextgis_toolbox.tasks.models import (
    ToolboxTaskInformation,
)


class TasksRepository:
    """Repository for Toolbox task models and result files."""

    def __init__(self, api: TasksApi) -> None:
        """Initialize repository.

        :param api: Tasks API gateway.
        """
        self._api = api

    def api(self) -> "TasksApi":
        """Return the API gateway for managing tasks.

        :returns: Tasks API gateway.
        """
        return self._api

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
        logger.debug(f"Submitting task for tool '{tool_name}'")
        return self._api.submit_task(
            tool_name=tool_name,
            inputs=inputs,
            emailing=emailing,
        )

    def task_information(
        self,
        task_id: str,
        feedback: Optional[QgsFeedback] = None,
    ) -> ToolboxTaskInformation:
        """Retrieve a task model from the API.

        :param task_id: Toolbox task identifier.
        :param feedback: Optional feedback object for progress reporting.

        :returns: Toolbox task model.
        """
        logger.debug(f"Fetching task information for '{task_id}'")
        return ToolboxTaskInformation.from_json(
            self._api.task_information(task_id, feedback=feedback)
        )
