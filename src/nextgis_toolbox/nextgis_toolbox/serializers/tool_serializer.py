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

from typing import Any, Dict

from nextgis_toolbox.nextgis_toolbox.models.tool import (
    ToolboxTag,
    ToolboxTool,
)


class ToolboxTagSerializer:
    """
    Serialize and deserialize NextGIS Toolbox tag models.
    """

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> ToolboxTag:
        """
        Build tag model from API response payload.

        :param data: Raw API payload.

        :returns: Parsed toolbox tag model.
        """

        return ToolboxTag(
            id=data["id"],
            alias=data["alias"],
            icon=data["icon"],
            tool_ids=data.get("tool_ids", []),
        )

    @staticmethod
    def to_dict(tag: ToolboxTag) -> Dict[str, Any]:
        """
        Convert tag model to dictionary.

        :param tag: NextGIS Toolbox tag model.

        :returns: Serialized tag payload.
        """

        return {
            "id": tag.id,
            "alias": tag.alias,
            "icon": tag.icon,
            "tool_ids": tag.tool_ids,
        }


class ToolboxToolSerializer:
    """
    Serialize and deserialize NextGIS Toolbox tool models.
    """

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> ToolboxTool:
        """
        Build tool model from API response payload.

        :param data: Raw API payload.

        :returns: Parsed toolbox tool model.
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

    @staticmethod
    def to_dict(tool: ToolboxTool) -> Dict[str, Any]:
        """
        Convert tool model to dictionary.

        :param tool: NextGIS Toolbox tool model.

        :returns: Serialized tool payload.
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
