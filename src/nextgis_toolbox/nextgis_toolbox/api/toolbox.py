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

from typing import List, Tuple

from nextgis_toolbox.nextgis_toolbox.api.client import (
    ToolboxApiClient,
)
from nextgis_toolbox.nextgis_toolbox.models.parameter import (
    ToolboxParameter,
)
from nextgis_toolbox.nextgis_toolbox.models.tool import (
    ToolboxTag,
    ToolboxTool,
)
from nextgis_toolbox.nextgis_toolbox.serializers.parameter_serializer import (
    ToolboxParameterSerializer,
)
from nextgis_toolbox.nextgis_toolbox.serializers.tool_serializer import (
    ToolboxTagSerializer,
    ToolboxToolSerializer,
)


class Toolbox:
    """
    Main facade for interaction with NextGIS Toolbox API.
    """

    def __init__(self) -> None:
        """
        Initialize NextGIS Toolbox API facade.
        """

        self.client = ToolboxApiClient()

        self.tools: List[ToolboxTool] = []
        self.tags: List[ToolboxTag] = []

    def load_tools(self) -> None:
        """
        Load available toolbox tools.

        :returns: List of toolbox tool models.
        """

        response_data = self.client.get(
            sub_url="tools/",
        )

        self.tools = [
            ToolboxToolSerializer.from_dict(tool_data)
            for tool_data in response_data["data"]
        ]

    def load_tags(self) -> None:
        """
        Load available toolbox tags.
        """

        response_data = self.client.get(
            sub_url="tags/",
        )

        self.tags = [
            ToolboxTagSerializer.from_dict(tag_data)
            for tag_data in response_data["data"]
        ]

    def fetch_tool_io_parameters(
        self,
        tool_name: str,
    ) -> Tuple[
        List[ToolboxParameter],
        List[ToolboxParameter],
    ]:
        """
        Fetch input and output parameter definitions for a tool.

        :param tool_name: Toolbox tool identifier.

        :returns: Tuple containing input and output parameter lists.
        """

        response_data = self.client.get(
            sub_url=f"tools/{tool_name}",
            use_auth=True,
        )

        inputs = [
            ToolboxParameterSerializer.from_dict(parameter_data)
            for parameter_data in response_data["inputs"]
        ]

        outputs = [
            ToolboxParameterSerializer.from_dict(parameter_data)
            for parameter_data in response_data["outputs"]
        ]

        return inputs, outputs
