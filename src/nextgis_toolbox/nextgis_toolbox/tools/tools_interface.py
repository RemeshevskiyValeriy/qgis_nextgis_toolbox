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

from abc import abstractmethod
from typing import TYPE_CHECKING, List, Optional, Union

from qgis.PyQt.QtCore import QObject, pyqtSignal, pyqtSlot

from nextgis_toolbox.nextgis_toolbox.tools.models import (
    SortBy,
    ToolboxTag,
    ToolboxTool,
    ToolsManagerState,
)
from nextgis_toolbox.shared.qobject_metaclass import QObjectMetaClass

if TYPE_CHECKING:
    from nextgis_toolbox.core.exceptions import ToolboxError
    from nextgis_toolbox.nextgis_toolbox.tools.api import ToolsApi


class ToolsInterface(QObject, metaclass=QObjectMetaClass):
    """Abstract QObject interface for the tools feature."""

    state_changed = pyqtSignal(object)
    loading_progress_changed = pyqtSignal(float)

    @property
    @abstractmethod
    def state(self) -> ToolsManagerState:
        """Return the current state of the tools manager."""
        ...

    @property
    @abstractmethod
    def error(self) -> Optional["ToolboxError"]:
        """Return the current error of the tools manager."""
        ...

    def api(self) -> "ToolsApi":
        """Return the API for managing tools and tags.

        :returns: Tools API instance.
        """
        ...

    def set_api(self, tools_api: "ToolsApi") -> None:
        """Set the API for managing tools and tags.

        :param tools_api: API for managing tools and tags.
        """

    @pyqtSlot()
    @abstractmethod
    def load(self) -> None:
        """Load all components of the tools feature."""
        ...

    @abstractmethod
    def refresh(
        self,
        *,
        clear_cache: bool = False,
    ) -> None:
        """Refresh the tools catalog using the active runtime mode.

        :param clear_cache: Clear API cache before reloading.
        """
        ...

    @pyqtSlot()
    @abstractmethod
    def unload(self) -> None:
        """Unload all components of the tools feature."""
        ...

    @abstractmethod
    def tools(self, *, sort_by: SortBy = SortBy.NAME) -> List[ToolboxTool]:
        """Return cached Toolbox tools with resolved tags.

        :returns: List of cached tool models.
        """
        ...

    @abstractmethod
    def tool(
        self,
        *,
        tool_id: Optional[int] = None,
        name: Optional[str] = None,
    ) -> ToolboxTool:
        """Return one cached Toolbox tool by identifier."""
        ...

    @abstractmethod
    def find_tools(
        self,
        *,
        tool_id: Optional[Union[int, List[int]]] = None,
        name: Optional[Union[str, List[str]]] = None,
        tag: Optional[
            Union[int, ToolboxTag, List[Union[int, ToolboxTag]]]
        ] = None,
        is_featured: Optional[bool] = None,
        is_favorite: Optional[bool] = None,
    ) -> List[ToolboxTool]:
        """Return cached tools matching a single search criterion."""
        ...

    @abstractmethod
    def set_tool_favorite(
        self,
        tool_name: str,
        is_favorite: bool,
        *,
        sync_remote: bool = True,
    ) -> None:
        """Update a cached tool favorite state and optionally sync it."""
        ...

    @abstractmethod
    def tags(self, *, sort_by: SortBy = SortBy.ALIAS) -> List[ToolboxTag]:
        """Return cached Toolbox tags.

        :returns: List of cached tag models.
        """
        ...

    @abstractmethod
    def tag(self, tag_id: int) -> ToolboxTag:
        """Return one cached Toolbox tag by identifier."""
        ...
