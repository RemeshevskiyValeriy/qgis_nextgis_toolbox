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

from typing import Any, Dict

from nextgis_toolbox.nextgis_toolbox.sdk.client import ToolboxApiClient


class TasksApi:
    """API gateway for NextGIS Toolbox tasks endpoints."""

    def __init__(self, client: ToolboxApiClient) -> None:
        """Initialize API gateway.

        :param client: Low-level Toolbox API client.
        """
        self._client = client

    def submit_task(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        emailing: bool = False,
    ) -> Dict[str, Any]:
        """Submit raw task payload.

        :param tool_name: Toolbox tool identifier.
        :param inputs: Tool input values.
        :param emailing: Enable result emailing.

        :returns: Raw task creation response.
        """
        payload = {
            "tool": tool_name,
            "inputs": inputs,
            "mode": "api",
            "emailing": emailing,
        }

        return self._client.post(
            sub_url="tasks/",
            payload=payload,
            use_auth=True,
        )

    def retrieve_task(self, task_id: str) -> Dict[str, Any]:
        """Retrieve raw task information.

        :param task_id: Toolbox task identifier.

        :returns: Raw task dictionary.
        """
        return self._client.get(
            sub_url=f"tasks/{task_id}",
            use_auth=True,
        )

    def download_result_content(self, url: str) -> bytes:
        """Download raw task result content.

        :param url: Result file URL.

        :returns: Downloaded file content.
        """
        return self._client.get_content(
            sub_url=url,
            use_auth=True,
        )
