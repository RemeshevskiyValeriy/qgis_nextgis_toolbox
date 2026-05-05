# NextGIS Toolbox Plugin
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
from typing import Any, Dict, List, Tuple

from nextgis_toolbox.nextgis_toolbox.api.client import ToolboxApiClient
from nextgis_toolbox.nextgis_toolbox.api.orders_manager import (
    ToolboxOrdersManager,
)
from nextgis_toolbox.nextgis_toolbox.models.io import ToolboxParameter
from nextgis_toolbox.nextgis_toolbox.models.result import ToolboxResult


class Toolbox:
    """
    Main facade for interaction with NextGIS Toolbox API.
    """

    def __init__(self) -> None:
        """
        Initialize NextGIS Toolbox API facade.
        """
        self.client = ToolboxApiClient()
        self.orders_manager = ToolboxOrdersManager(client=self.client)

        self.tools: List[Dict[str, Any]] = self._fetch_tools()
        self.tags: List[Dict[str, Any]] = self._fetch_tags()

    def _fetch_tools(self) -> List[Dict[str, Any]]:
        """
        Fetch the list of available tools from the API.

        :returns: Raw tool descriptors from the API response.
        """
        return self.client.get("tools/")["data"]

    def _fetch_tags(self) -> List[Dict[str, Any]]:
        """
        Fetch the list of available tags from the API.

        :returns: Raw tag descriptors from the API response.
        """
        return self.client.get("tags/")["data"]

    def fetch_tool_io(
        self,
        tool_name: str,
    ) -> Tuple[List[ToolboxParameter], List[ToolboxParameter]]:
        """
        Fetch input and output parameter definitions for a single tool.

        :param tool_name: Tool identifier as returned by the API.

        :returns: Tuple of ``(inputs, outputs)`` parameter lists.
        """
        data = self.client.get(f"tools/{tool_name}", use_auth=True)
        inputs = [ToolboxParameter.from_dict(item) for item in data["inputs"]]
        outputs = [
            ToolboxParameter.from_dict(item) for item in data["outputs"]
        ]
        return inputs, outputs

    def create_order(
        self,
        tool_id: str,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Submit a tool execution order to the API.

        :param tool_id: Tool identifier.
        :param inputs: Resolved parameter values keyed by parameter name.
        :returns: API response payload containing at least ``task_id``.
        """
        payload = {
            "operation": tool_id,
            "inputs": inputs,
        }
        return self.client.post(
            "json/execute/",
            payload=payload,
            use_auth=True,
        )

    def refresh_orders(self) -> None:
        """Refresh the local orders cache."""
        self.orders_manager.update_orders()

    def save_results(
        self,
        order_id: str,
        result_directory: Path,
    ) -> None:
        """
        Download result files for a completed order.

        :param order_id: Order identifier.
        :param result_directory: Local directory to write result files into.
        """
        status_data = self.orders_manager.get_status(order_id)
        results = [
            ToolboxResult.from_dict(item) for item in status_data["output"]
        ]
        self.orders_manager.get_results(results, result_directory)

    def upload_file(self) -> str:
        """
        Upload a file to NextGIS Toolbox storage.

        :returns: Uploaded file identifier.
        """
        return self.client.get_content(
            "upload/",
            use_auth=True,
        ).decode("utf-8")
