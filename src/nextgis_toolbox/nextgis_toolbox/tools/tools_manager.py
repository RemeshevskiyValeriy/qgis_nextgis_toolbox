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

from typing import Any, Dict, List, Optional, Set, Union

from qgis.PyQt.QtCore import QObject, pyqtSlot

from nextgis_toolbox.nextgis_toolbox.tools.api import ToolsApi
from nextgis_toolbox.nextgis_toolbox.tools.models import (
    SortBy,
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
        self._tools_by_alias_sorted: Optional[List[ToolboxTool]] = None
        self._tools_by_id: Optional[Dict[int, ToolboxTool]] = None
        self._tools_by_id_sorted: Optional[List[ToolboxTool]] = None
        self._tools_by_name: Optional[Dict[str, ToolboxTool]] = None
        self._tools_by_tag_id: Optional[Dict[int, List[ToolboxTool]]] = None
        self._tags: List[ToolboxTag] = []
        self._tags_by_id: Optional[Dict[int, ToolboxTag]] = None
        self._tags_by_id_sorted: Optional[List[ToolboxTag]] = None

    def set_api(self, tools_api: ToolsApi) -> None:
        """Set the API for managing tools and tags.

        :param tools_api: API for managing tools and tags.
        """
        self._tools_repository.set_api(tools_api)
        self._tags_repository.set_api(tools_api)

    @pyqtSlot()
    def load(self) -> None:
        """Load the tools feature and populate caches."""
        self._tags = self._sort_tags(
            self._tags_repository.fetch_tags(),
            sort_by=SortBy.ALIAS,
        )
        self._tools = self._sort_tools(
            self._tools_repository.fetch_tools(),
            sort_by=SortBy.NAME,
        )

        self._assign_tags_to_tools()
        self._invalidate_indexes()

    @pyqtSlot()
    def unload(self) -> None:
        """Unload the tools feature and clear cached models."""
        self._tools = []
        self._tools_by_alias_sorted = None
        self._tools_by_id = None
        self._tools_by_id_sorted = None
        self._tools_by_name = None
        self._tools_by_tag_id = None
        self._tags = []
        self._tags_by_id = None
        self._tags_by_id_sorted = None

    def tools(
        self,
        *,
        sort_by: SortBy = SortBy.NAME,
    ) -> List[ToolboxTool]:
        """Return cached Toolbox tools with resolved tags.

        :returns: List of cached tool models.
        """
        if sort_by == SortBy.NAME:
            return self._tools

        if sort_by == SortBy.ID:
            return self._tools_by_id_sorted_cache()

        if sort_by == SortBy.ALIAS:
            return self._tools_by_alias_sorted_cache()

        raise ValueError(f"Unsupported tool sorting: {sort_by}")

    def tool(
        self,
        *,
        tool_id: Optional[int] = None,
        name: Optional[str] = None,
    ) -> Optional[ToolboxTool]:
        """Return one cached Toolbox tool by identifier."""
        if (tool_id is None) == (name is None):
            raise ValueError(
                "Exactly one of 'tool_id' or 'name' must be provided."
            )

        if tool_id is not None:
            return self._tools_by_id_cache().get(tool_id)

        assert name is not None
        return self._tools_by_name_cache().get(name)

    def find_tools(
        self,
        *,
        tool_id: Optional[Union[int, List[int]]] = None,
        name: Optional[Union[str, List[str]]] = None,
        tag: Optional[
            Union[int, ToolboxTag, List[Union[int, ToolboxTag]]]
        ] = None,
    ) -> List[ToolboxTool]:
        """Return cached tools matching a single search criterion."""
        criteria_count = sum(
            value is not None for value in (tool_id, name, tag)
        )
        if criteria_count != 1:
            raise ValueError(
                "Exactly one of 'tool_id', 'name', or 'tag' must be provided."
            )

        if tool_id is not None:
            tool_ids = set(self._normalize_to_list(tool_id))
            return [tool for tool in self._tools if tool.id in tool_ids]

        if name is not None:
            tool_names = set(self._normalize_to_list(name))
            return [tool for tool in self._tools if tool.name in tool_names]

        tag_ids = self._resolve_tag_ids(tag)
        matching_tool_ids: Set[int] = set()

        for tag_id in tag_ids:
            matching_tool_ids.update(
                tool.id
                for tool in self._tools_by_tag_id_cache().get(tag_id, [])
            )

        return [tool for tool in self._tools if tool.id in matching_tool_ids]

    def tags(
        self,
        *,
        sort_by: SortBy = SortBy.ALIAS,
    ) -> List[ToolboxTag]:
        """Return cached Toolbox tags.

        :returns: List of cached tag models.
        """
        if sort_by == SortBy.ALIAS:
            return self._tags

        if sort_by == SortBy.ID:
            return self._tags_by_id_sorted_cache()

        raise ValueError(f"Unsupported tag sorting: {sort_by}")

    def tag(self, tag_id: int) -> Optional[ToolboxTag]:
        """Return one cached Toolbox tag by identifier."""
        return self._tags_by_id_cache().get(tag_id)

    def _assign_tags_to_tools(self) -> None:
        """Resolve cached tag identifiers to cached tag models."""
        tag_by_id: Dict[int, ToolboxTag] = {tag.id: tag for tag in self._tags}
        tool_ids_by_tag_id: Dict[int, List[int]] = {
            tag.id: [] for tag in self._tags
        }

        for tool in self._tools:
            tool.tags = [
                tag_by_id[tag_id]
                for tag_id in tool.tag_ids
                if tag_id in tag_by_id
            ]

            for tag in tool.tags:
                tool_ids_by_tag_id.setdefault(tag.id, []).append(tool.id)

        for tag in self._tags:
            tag.tool_ids = tool_ids_by_tag_id.get(tag.id, [])

    def _invalidate_indexes(self) -> None:
        """Reset lazily built lookup structures."""
        self._tags_by_id = None
        self._tags_by_id_sorted = None
        self._tools_by_alias_sorted = None
        self._tools_by_id = None
        self._tools_by_id_sorted = None
        self._tools_by_name = None
        self._tools_by_tag_id = None

    def _tags_by_id_cache(self) -> Dict[int, ToolboxTag]:
        """Return tag lookup by identifier."""
        if self._tags_by_id is None:
            self._tags_by_id = {tag.id: tag for tag in self._tags}

        return self._tags_by_id

    def _tags_by_id_sorted_cache(self) -> List[ToolboxTag]:
        """Return tags sorted by identifier."""
        if self._tags_by_id_sorted is None:
            self._tags_by_id_sorted = self._sort_tags(
                self._tags,
                sort_by=SortBy.ID,
            )

        return self._tags_by_id_sorted

    def _tools_by_alias_sorted_cache(self) -> List[ToolboxTool]:
        """Return tools sorted by alias."""
        if self._tools_by_alias_sorted is None:
            self._tools_by_alias_sorted = self._sort_tools(
                self._tools,
                sort_by=SortBy.ALIAS,
            )

        return self._tools_by_alias_sorted

    def _tools_by_id_cache(self) -> Dict[int, ToolboxTool]:
        """Return tool lookup by identifier."""
        if self._tools_by_id is None:
            self._tools_by_id = {tool.id: tool for tool in self._tools}

        return self._tools_by_id

    def _tools_by_id_sorted_cache(self) -> List[ToolboxTool]:
        """Return tools sorted by identifier."""
        if self._tools_by_id_sorted is None:
            self._tools_by_id_sorted = self._sort_tools(
                self._tools,
                sort_by=SortBy.ID,
            )

        return self._tools_by_id_sorted

    def _tools_by_name_cache(self) -> Dict[str, ToolboxTool]:
        """Return tool lookup by name."""
        if self._tools_by_name is None:
            self._tools_by_name = {tool.name: tool for tool in self._tools}

        return self._tools_by_name

    def _tools_by_tag_id_cache(self) -> Dict[int, List[ToolboxTool]]:
        """Return tool lookup by tag identifier."""
        if self._tools_by_tag_id is None:
            tools_by_tag_id: Dict[int, List[ToolboxTool]] = {
                tag.id: [] for tag in self._tags
            }

            for tool in self._tools:
                for tag in tool.tags:
                    tools_by_tag_id.setdefault(tag.id, []).append(tool)

            self._tools_by_tag_id = tools_by_tag_id

        return self._tools_by_tag_id

    def _resolve_tag_ids(
        self,
        value: Optional[Union[int, ToolboxTag, List[Union[int, ToolboxTag]]]],
    ) -> List[int]:
        """Normalize tag search criteria to tag identifiers."""
        if value is None:
            return []

        tag_values = self._normalize_to_list(value)
        tag_ids: List[int] = []

        for tag_value in tag_values:
            if isinstance(tag_value, ToolboxTag):
                tag_ids.append(tag_value.id)
                continue

            tag_ids.append(int(tag_value))

        return tag_ids

    def _normalize_to_list(
        self, value: Any
    ) -> List[Union[int, str, ToolboxTag]]:
        """Normalize scalar or list search values to a list."""
        if isinstance(value, list):
            return value

        return [value]

    def _sort_tags(
        self,
        tags: List[ToolboxTag],
        *,
        sort_by: SortBy,
    ) -> List[ToolboxTag]:
        """Return tags sorted using the requested key."""
        if sort_by == SortBy.ID:
            return sorted(tags, key=lambda tag: tag.id)

        if sort_by == SortBy.ALIAS:
            return sorted(tags, key=lambda tag: tag.alias)

        raise ValueError(f"Unsupported tag sorting: {sort_by}")

    def _sort_tools(
        self,
        tools: List[ToolboxTool],
        *,
        sort_by: SortBy,
    ) -> List[ToolboxTool]:
        """Return tools sorted using the requested key."""
        if sort_by == SortBy.ID:
            return sorted(tools, key=lambda tool: tool.id)

        if sort_by == SortBy.NAME:
            return sorted(tools, key=lambda tool: tool.name)

        if sort_by == SortBy.ALIAS:
            return sorted(tools, key=lambda tool: tool.alias)

        raise ValueError(f"Unsupported tool sorting: {sort_by}")
