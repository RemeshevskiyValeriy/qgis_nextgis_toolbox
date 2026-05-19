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

from typing import List, Tuple

from nextgis_toolbox.nextgis_toolbox.tools.api import ToolsApi
from nextgis_toolbox.nextgis_toolbox.tools.models import (
    ToolboxParameter,
    ToolboxTag,
    ToolboxTool,
)


class ToolsRepository:
    """Repository for Toolbox tool models."""

    def __init__(self, api: ToolsApi) -> None:
        """Initialize repository.

        :param api: Tools API gateway.
        """
        self._api = api

    def set_api(self, api: ToolsApi) -> None:
        """Set API gateway instance.

        :param api: Tools API gateway.
        """
        self._api = api

    def fetch_tools(self) -> List[ToolboxTool]:
        """Fetch tool models from the API.

        :returns: List of Toolbox tool models.
        """
        return [
            ToolboxTool.from_json(tool_data)
            for tool_data in self._api.fetch_tools()
        ]

    def fetch_tool_io_parameters(
        self,
        tool_name: str,
    ) -> Tuple[List[ToolboxParameter], List[ToolboxParameter]]:
        """Fetch tool input and output parameter models.

        :param tool_name: Toolbox tool identifier.

        :returns: Tuple with input and output parameter lists.
        """
        response_data = self._api.fetch_tool_io_parameters(tool_name)
        inputs = [
            ToolboxParameter.from_json(parameter_data)
            for parameter_data in response_data["inputs"]
        ]
        outputs = [
            ToolboxParameter.from_json(parameter_data)
            for parameter_data in response_data["outputs"]
        ]

        return inputs, outputs


class TagsRepository:
    """Repository for Toolbox tag models."""

    def __init__(self, api: ToolsApi) -> None:
        """Initialize repository.

        :param api: Tools API gateway.
        """
        self._api = api

    def set_api(self, api: ToolsApi) -> None:
        """Set API gateway instance.

        :param api: Tools API gateway.
        """
        self._api = api

    def fetch_tags(self) -> List[ToolboxTag]:
        """Fetch tag models from the API.

        :returns: List of Toolbox tag models.
        """
        return [
            ToolboxTag.from_json(tag_data)
            for tag_data in self._api.fetch_tags()
        ]
