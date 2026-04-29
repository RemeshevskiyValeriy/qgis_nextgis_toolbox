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
from typing import Any, Dict, List

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

        self.tools: List[Dict[str, Any]] = []
        self.tags: List[Dict[str, Any]] = []

        self.tools = self.get_tools()
        self.tags = self.get_tags()

        self.orders_manager = ToolboxOrdersManager(client=self.client)

    def get_tools(self) -> List[Dict[str, Any]]:
        """
        Fetch available tools.

        :returns: List of tools.
        """

        response_data = self.client.get("tools/")

        return response_data["data"]

    def get_tags(self) -> List[Dict[str, Any]]:
        """
        Fetch available tags.

        :returns: List of tags.
        """

        response_data = self.client.get("tags/")

        return response_data["data"]

    def get_tool_inputs(
        self,
        tool_id: str,
    ) -> List[ToolboxParameter]:
        """
        Fetch tool input parameters.

        :param tool_id: Tool identifier.

        :returns: List of input parameters.
        """

        response_data = self.client.get(
            f"operation/{tool_id}/inputs",
            use_auth=True,
        )

        return [ToolboxParameter.from_dict(item) for item in response_data]

    def get_tool_outputs(
        self,
        tool_id: str,
    ) -> List[ToolboxParameter]:
        """
        Fetch tool output parameters.

        :param tool_id: Tool identifier.

        :returns: List of output parameters.
        """

        response_data = self.client.get(
            f"operations/{tool_id}/outputs",
            use_auth=True,
        )

        return [ToolboxParameter.from_dict(item) for item in response_data]

    def get_toolbox_interface(
        self,
    ) -> Dict[str, Dict[str, List[ToolboxParameter]]]:
        """
        Fetch toolbox interface description.

        :returns: Parsed toolbox interface structure.
        """

        response_data = self.client.get(
            "operations/interface/",
            use_auth=True,
        )

        result: Dict[
            str,
            Dict[str, List[ToolboxParameter]],
        ] = {}

        errors: Dict[str, str] = {}

        for tool_name, tool_data in response_data.items():
            try:
                result[tool_name] = {
                    "inputs": [
                        ToolboxParameter.from_dict(item)
                        for item in tool_data["inputs"]
                    ],
                    "outputs": [
                        ToolboxParameter.from_dict(item)
                        for item in tool_data["outputs"]
                    ],
                }

            except Exception as error:
                errors[tool_name] = str(error)

                if tool_name in result:
                    del result[tool_name]

        return result, errors

    def refresh_orders(self) -> None:
        """
        Refresh orders cache.
        """

        if self.orders_manager is None:
            return

        self.orders_manager.update_orders()

    def upload_file(self) -> str:
        """
        Upload file to NextGIS Toolbox storage.

        :returns: Uploaded file identifier.
        """

        return self.client.get_content(
            "upload/",
            use_auth=True,
        ).decode("utf-8")

    def create_order(
        self,
        tool_id: str,
        inputs: List[ToolboxParameter],
    ) -> Dict[str, Any]:
        """
        Create toolbox execution order.

        :param tool_id: Tool identifier.
        :param inputs: Tool input parameters.

        :returns: API response payload.
        """
        request_payload = {
            "operation": tool_id,
            "inputs": {
                parameter.name: parameter.value for parameter in inputs
            },
        }

        return self.client.post(
            "json/execute/",
            payload=request_payload,
            use_auth=True,
        )

    def save_results(
        self,
        order_id: str,
        result_directory: Path,
    ) -> None:
        """
        Download order result files.

        :param order_id: Order identifier.
        :param result_directory: Target directory.
        """

        if self.orders_manager is None:
            return

        status_data = self.orders_manager.get_status(order_id)

        results = [
            ToolboxResult.from_dict(item) for item in status_data["output"]
        ]

        self.orders_manager.get_results(
            results,
            result_directory,
        )
