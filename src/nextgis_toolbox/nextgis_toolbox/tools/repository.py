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

from typing import Any, Dict, List

from nextgis_toolbox.core.logging import logger
from nextgis_toolbox.nextgis_toolbox.tools.api import ToolsApi
from nextgis_toolbox.nextgis_toolbox.tools.models import (
    ToolboxTag,
    ToolboxTool,
)
from nextgis_toolbox.settings.nextgis_toolbox_settings import (
    NextgisToolboxSettings,
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
        logger.debug("Fetching Toolbox tools catalog")
        settings = NextgisToolboxSettings()
        is_developer_mode = settings.is_developer_mode

        unfiltered_tools = self._api.fetch_tools()
        logger.debug(f"Fetched {len(unfiltered_tools)} tools")

        tools: List[ToolboxTool] = []

        for tool_data in unfiltered_tools:
            if not self._is_tool_available(tool_data, is_developer_mode):
                continue

            logger.debug(
                f"Fetching Toolbox tool details for '{tool_data['name']}'"
            )
            tool_details = self._api.fetch_tool(tool_data["name"])
            tools.append(ToolboxTool.from_json({**tool_data, **tool_details}))

        return tools

    def _is_tool_available(
        self,
        tool_data: Dict[str, Any],
        is_developer_mode: bool,
    ) -> bool:
        """Check whether a tool should be exposed to the plugin."""
        if tool_data.get("is_dev", False) and not is_developer_mode:
            return False

        return True


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
        logger.debug("Fetching Toolbox tags catalog")
        tags = [
            ToolboxTag.from_json(tag_data)
            for tag_data in self._api.fetch_tags()
        ]
        logger.debug(f"Fetched {len(tags)} tags")
        return tags
