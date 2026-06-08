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

from typing import Any, Dict, List, Optional

from qgis.core import QgsFeedback

from nextgis_toolbox.core.logging import logger
from nextgis_toolbox.core.utils import PluginRuntimeProfiler
from nextgis_toolbox.settings.nextgis_toolbox_settings import (
    NextgisToolboxSettings,
)
from nextgis_toolbox.tools.api import ToolsApi
from nextgis_toolbox.tools.models import (
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

    def fetch_tools(
        self, feedback: Optional[QgsFeedback] = None
    ) -> List[ToolboxTool]:
        """Fetch tool models from the API.

        :returns: List of Toolbox tool models.
        """
        logger.debug("Fetching Toolbox tools catalog")

        is_developer_mode = NextgisToolboxSettings().is_developer_mode

        unfiltered_tools: List[Dict[str, Any]] = []
        with PluginRuntimeProfiler.download("fetching tools summaries"):
            unfiltered_tools = self._api.fetch_tools()

        self._set_progress(feedback, 5)

        logger.debug(f"Fetched {len(unfiltered_tools)} tools")

        tools = []
        with PluginRuntimeProfiler.download(
            "fetching tools details and presets"
        ):
            tools = self._fetch_all_tools_data(
                unfiltered_tools,
                feedback,
                is_developer_mode,
            )

        self._set_progress(feedback, 100)

        if self._is_canceled(feedback):
            return []

        logger.debug(f"Processed {len(tools)} available tools")
        return tools

    def set_tool_favorite(
        self,
        tool_name: str,
        is_favorite: bool,
    ) -> None:
        self._api.set_tool_favorite(tool_name, is_favorite)

    def _fetch_all_tools_data(
        self,
        unfiltered_tools: List[Dict[str, Any]],
        feedback: Optional[QgsFeedback],
        is_developer_mode: bool,
    ) -> List[ToolboxTool]:
        percent_progress_per_tool = (
            (95 / len(unfiltered_tools)) if unfiltered_tools else 0
        )

        tools: List[ToolboxTool] = []

        for index, tool_data in enumerate(unfiltered_tools, start=1):
            if self._is_canceled(feedback):
                logger.debug("Tools fetching canceled by user")
                return []

            if not self._is_tool_available(tool_data, is_developer_mode):
                continue

            tools.append(self._fetch_all_tool_data(tool_data))

            self._set_progress(feedback, 5 + index * percent_progress_per_tool)

        return tools

    def _fetch_all_tool_data(self, tool_data: Dict[str, Any]) -> ToolboxTool:
        tool_name = tool_data["name"]
        tool_details = self._fetch_tool_details(tool_name)
        tool_presets = self._fetch_tool_presets(tool_name)
        return ToolboxTool.from_json(
            self._merge_tool_data(
                tool_data,
                tool_details,
                tool_presets,
            )
        )

    def _fetch_tool_details(self, tool_name: str) -> Dict[str, Any]:
        logger.debug(f"Fetching tool details: {tool_name}")
        return self._api.fetch_tool(tool_name)

    def _fetch_tool_presets(self, tool_name: str) -> List[Dict[str, Any]]:
        logger.debug(f"Fetching tool presets: {tool_name}")
        return self._api.fetch_tool_presets(tool_name)

    def _merge_tool_data(
        self,
        tool_data: Dict[str, Any],
        tool_details: Dict[str, Any],
        tool_presets: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        merged_tool_data = dict(tool_details)
        merged_tool_data.update(tool_data)
        merged_tool_data["presets"] = tool_presets

        return merged_tool_data

    def _is_tool_available(
        self,
        tool_data: Dict[str, Any],
        is_developer_mode: bool,
    ) -> bool:
        """Check whether a tool should be exposed to the plugin."""
        if tool_data.get("is_dev", False) and not is_developer_mode:
            return False

        return True

    def _is_canceled(self, feedback: Optional[QgsFeedback]) -> bool:
        return feedback is not None and feedback.isCanceled()

    def _set_progress(
        self, feedback: Optional[QgsFeedback], progress: float
    ) -> None:
        if feedback is None:
            return
        feedback.setProgress(progress)


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
        tags: List[ToolboxTag] = []

        with PluginRuntimeProfiler.download("fetching tags"):
            tags = [
                ToolboxTag.from_json(tag_data)
                for tag_data in self._api.fetch_tags()
            ]

        logger.debug(f"Fetched {len(tags)} tags")
        return tags
