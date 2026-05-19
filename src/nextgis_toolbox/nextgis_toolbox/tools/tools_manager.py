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

from typing import Dict, List, Optional, Tuple

from qgis.PyQt.QtCore import QObject, pyqtSlot

from nextgis_toolbox.nextgis_toolbox.tools.api import ToolsApi
from nextgis_toolbox.nextgis_toolbox.tools.models import (
    ToolboxParameter,
    ToolboxTag,
    ToolboxTool,
)
from nextgis_toolbox.nextgis_toolbox.tools.repository import (
    TagsRepository,
    ToolsRepository,
)
from nextgis_toolbox.nextgis_toolbox.tools.tools_interface import (
    ToolsInterface,
)


class ToolsManager(ToolsInterface):
    """Feature-level manager for Toolbox tools."""

    def __init__(
        self,
        tools_api: ToolsApi,
        parent: Optional[QObject] = None,
    ) -> None:
        """Initialize tools manager.

        :param tools_api: API for managing tools and tags.
        :param parent: Optional Qt parent.
        """
        super().__init__(parent)
        self._tools_repository = ToolsRepository(tools_api)
        self._tags_repository = TagsRepository(tools_api)
        self._tools: List[ToolboxTool] = []
        self._tags: List[ToolboxTag] = []

    def set_api(self, tools_api: ToolsApi) -> None:
        """Set the API for managing tools and tags.

        :param tools_api: API for managing tools and tags.
        """
        self._tools_repository.set_api(tools_api)
        self._tags_repository.set_api(tools_api)

    @pyqtSlot()
    def load(self) -> None:
        """Load the tools feature and populate caches."""
        self._tags = self._tags_repository.fetch_tags()
        self._tools = self._tools_repository.fetch_tools()

        self._assign_tags_to_tools()

    @pyqtSlot()
    def unload(self) -> None:
        """Unload the tools feature and clear cached models."""
        self._tools = []
        self._tags = []

    def tools(self) -> List[ToolboxTool]:
        """Return cached Toolbox tools with resolved tags.

        :returns: List of cached tool models.
        """
        return self._tools

    def tags(self) -> List[ToolboxTag]:
        """Return cached Toolbox tags.

        :returns: List of cached tag models.
        """
        return self._tags

    def fetch_tool_io_parameters(
        self,
        tool_name: str,
    ) -> Tuple[List[ToolboxParameter], List[ToolboxParameter]]:
        """Fetch input and output parameters for a tool.

        :param tool_name: Toolbox tool identifier.

        :returns: Tuple with input and output parameter lists.
        """
        return self._tools_repository.fetch_tool_io_parameters(tool_name)

    def _assign_tags_to_tools(self) -> None:
        """Resolve cached tag identifiers to cached tag models."""
        tag_by_id: Dict[int, ToolboxTag] = {tag.id: tag for tag in self._tags}

        for tool in self._tools:
            tool.tags = [
                tag_by_id[tag_id]
                for tag_id in tool.tag_ids
                if tag_id in tag_by_id
            ]
