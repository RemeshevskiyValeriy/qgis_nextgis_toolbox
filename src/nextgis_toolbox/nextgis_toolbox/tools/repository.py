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

from typing import Any, Dict, List, Tuple

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
        """Fetch and map available Toolbox tools.

        :returns: List of Toolbox tool models.
        """
        return [
            self._tool_from_dict(tool_data)
            for tool_data in self._api.fetch_tools()
        ]

    def fetch_tool_io_parameters(
        self,
        tool_name: str,
    ) -> Tuple[List[ToolboxParameter], List[ToolboxParameter]]:
        """Fetch and map tool input and output parameter definitions.

        :param tool_name: Toolbox tool identifier.

        :returns: Tuple with input and output parameter lists.
        """
        response_data = self._api.fetch_tool_io_parameters(tool_name)
        inputs = [
            self._parameter_from_dict(parameter_data)
            for parameter_data in response_data["inputs"]
        ]
        outputs = [
            self._parameter_from_dict(parameter_data)
            for parameter_data in response_data["outputs"]
        ]

        return inputs, outputs

    def to_dict(self, tool: ToolboxTool) -> Dict[str, Any]:
        """Convert tool model to raw API-compatible dictionary.

        :param tool: Toolbox tool model.

        :returns: Raw tool dictionary.
        """
        return {
            "id": tool.id,
            "name": tool.name,
            "alias": tool.alias,
            "description": tool.description,
            "is_dev": tool.is_dev,
            "is_free": tool.is_free,
            "is_new": tool.is_new,
            "is_featured": tool.is_featured,
            "can_run": tool.can_run,
            "tags": tool.tag_ids,
        }

    def parameter_to_dict(
        self,
        parameter: ToolboxParameter,
    ) -> Dict[str, Any]:
        """Convert parameter model to raw API-compatible dictionary.

        :param parameter: Toolbox parameter model.

        :returns: Raw parameter dictionary.
        """
        return {
            "name": parameter.name,
            "type": parameter.parameter_type,
            "alias": parameter.alias,
            "description": parameter.description,
            "required": parameter.required,
            "choices": parameter.choices,
        }

    def _tool_from_dict(self, data: Dict[str, Any]) -> ToolboxTool:
        """Build tool model from raw API payload.

        :param data: Raw API payload.

        :returns: Parsed Toolbox tool model.
        """
        return ToolboxTool(
            id=data["id"],
            name=data["name"],
            alias=data["alias"],
            description=data["description"],
            is_dev=data["is_dev"],
            is_free=data["is_free"],
            is_new=data["is_new"],
            is_featured=data["is_featured"],
            can_run=data["can_run"],
            tag_ids=data.get("tags", []),
        )

    def _parameter_from_dict(
        self,
        data: Dict[str, Any],
    ) -> ToolboxParameter:
        """Build parameter model from raw API payload.

        :param data: Raw API payload.

        :returns: Parsed Toolbox parameter model.
        """
        return ToolboxParameter(
            name=data["name"],
            parameter_type=data["type"],
            alias=data.get("alias"),
            description=data.get("description"),
            required=data.get("required", False),
            choices=data.get("choices"),
        )


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
        """Fetch and map available Toolbox tags.

        :returns: List of Toolbox tag models.
        """
        return [
            self._tag_from_dict(tag_data)
            for tag_data in self._api.fetch_tags()
        ]

    def to_dict(self, tag: ToolboxTag) -> Dict[str, Any]:
        """Convert tag model to raw API-compatible dictionary.

        :param tag: Toolbox tag model.

        :returns: Raw tag dictionary.
        """
        return {
            "id": tag.id,
            "alias": tag.alias,
            "icon": tag.icon,
            "tools": tag.tools,
        }

    def _tag_from_dict(self, data: Dict[str, Any]) -> ToolboxTag:
        """Build tag model from raw API payload.

        :param data: Raw API payload.

        :returns: Parsed Toolbox tag model.
        """
        return ToolboxTag(
            id=data["id"],
            alias=data["alias"],
            icon=data["icon"],
            tools=data["tools"],
        )
