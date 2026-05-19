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

from nextgis_toolbox.nextgis_toolbox.sdk.client import ToolboxApiClient
from nextgis_toolbox.nextgis_toolbox.tools.api import ToolsApi
from nextgis_toolbox.nextgis_toolbox.tools.models import (
    ToolboxParameter,
    ToolboxTag,
    ToolboxTool,
    ToolboxToolWithTags,
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
        tools_repository: ToolsRepository,
        tags_repository: TagsRepository,
        parent: Optional[QObject] = None,
    ) -> None:
        """Initialize tools manager.

        :param tools_repository: Repository for tool models.
        :param tags_repository: Repository for tag models.
        :param parent: Optional Qt parent.
        """
        super().__init__(parent)
        self._tools_repository = tools_repository
        self._tags_repository = tags_repository
        self._tools: List[ToolboxTool] = []
        self._tags: List[ToolboxTag] = []

    @classmethod
    def create(
        cls,
        parent: Optional[QObject] = None,
    ) -> "ToolsManager":
        """Create manager with default API and repositories.

        :param parent: Optional Qt parent.

        :returns: Configured tools manager.
        """
        api = ToolsApi(ToolboxApiClient())
        return cls(
            tools_repository=ToolsRepository(api),
            tags_repository=TagsRepository(api),
            parent=parent,
        )

    @pyqtSlot()
    def load(self) -> None:
        """Load the tools feature and populate caches."""
        self._tools = self._tools_repository.fetch_tools()
        self._tags = self._tags_repository.fetch_tags()

    @pyqtSlot()
    def unload(self) -> None:
        """Unload the tools feature and clear cached models."""
        self._tools = []
        self._tags = []

    def tools(self) -> List[ToolboxTool]:
        """Return cached Toolbox tools.

        :returns: List of cached tool models.
        """
        return self._tools

    def tags(self) -> List[ToolboxTag]:
        """Return cached Toolbox tags.

        :returns: List of cached tag models.
        """
        return self._tags

    def tools_with_tags(self) -> List[ToolboxToolWithTags]:
        """Return cached tools enriched with cached tags.

        :returns: List of enriched tool models.
        """
        tag_by_id: Dict[int, ToolboxTag] = {tag.id: tag for tag in self._tags}

        return [
            ToolboxToolWithTags(
                tool=tool,
                tags=[
                    tag_by_id[tag_id]
                    for tag_id in tool.tag_ids
                    if tag_id in tag_by_id
                ],
            )
            for tool in self._tools
        ]

    def fetch_tool_io_parameters(
        self,
        tool_name: str,
    ) -> Tuple[List[ToolboxParameter], List[ToolboxParameter]]:
        """Fetch input and output parameters for a tool.

        :param tool_name: Toolbox tool identifier.

        :returns: Tuple with input and output parameter lists.
        """
        return self._tools_repository.fetch_tool_io_parameters(tool_name)
