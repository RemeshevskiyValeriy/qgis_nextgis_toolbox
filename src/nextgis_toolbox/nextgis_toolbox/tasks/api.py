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
from urllib.parse import urljoin

from qgis.core import QgsFeedback
from qgis.PyQt.QtCore import QUrl, QUrlQuery

from nextgis_toolbox.core.exceptions import ToolboxTaskExecutionError
from nextgis_toolbox.nextgis_toolbox.sdk.client import ToolboxApiClient


class TasksApi:
    """API gateway for NextGIS Toolbox tasks endpoints."""

    def __init__(self, api_client: ToolboxApiClient) -> None:
        """Initialize API gateway.

        :param api_client: Low-level Toolbox API client.
        """
        self._api_client = api_client

    @property
    def api_client(self) -> ToolboxApiClient:
        """Low-level API client."""
        return self._api_client

    def tasks_history_url(self) -> QUrl:
        """Return the public URL for the task history page."""
        return self._instance_url("orders")

    def task_results_url(self, task_id: str) -> QUrl:
        """Return the public URL for a task results page."""
        url = self.tasks_history_url()
        query = QUrlQuery()
        query.addQueryItem("selected", task_id)
        url.setQuery(query)
        return url

    def submit_task(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        emailing: bool = False,
        feedback: Optional[QgsFeedback] = None,
    ) -> str:
        """Submit a task and return its identifier.

        :param tool_name: Toolbox tool identifier.
        :param inputs: Tool input values.
        :param emailing: Enable result emailing.
        :param feedback: Optional feedback object for progress reporting.

        :returns: Created task identifier.
        """
        payload = {
            "tool": tool_name,
            "inputs": inputs,
            "mode": "api",
            "emailing": emailing,
        }
        response = self._api_client.post(
            "tasks/",
            payload,
            feedback=feedback,
        )

        task_id = response.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            error = ToolboxTaskExecutionError(
                log_message=(
                    "Task submission did not return a valid task id for "
                    f"operation '{tool_name}'"
                ),
            )
            error.add_note(f"Response payload: {response}")
            raise error

        return task_id

    def task_information(
        self,
        task_id: str,
        feedback: Optional[QgsFeedback] = None,
    ) -> Dict[str, Any]:
        """Retrieve raw task information.

        :param task_id: Toolbox task identifier.
        :param feedback: Optional feedback object for progress reporting.

        :returns: Raw task dictionary.
        """
        return self._api_client.get(
            f"tasks/{task_id}",
            headers={
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            },
            feedback=feedback,
        )

    def _instance_url(self, path: str) -> QUrl:
        return QUrl(urljoin(self._api_client.endpoint.rstrip("/") + "/", path))
