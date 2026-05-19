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

from abc import abstractmethod
from typing import List, Tuple

from qgis.PyQt.QtCore import QObject, pyqtSlot

from nextgis_toolbox.nextgis_toolbox.tools.models import (
    ToolboxParameter,
    ToolboxTag,
    ToolboxTool,
    ToolboxToolWithTags,
)
from nextgis_toolbox.shared.qobject_metaclass import QObjectMetaClass


class ToolsInterface(QObject, metaclass=QObjectMetaClass):
    """Abstract QObject interface for the tools feature."""

    @pyqtSlot()
    @abstractmethod
    def load(self) -> None:
        """Load the tools feature and populate caches."""
        ...

    @pyqtSlot()
    @abstractmethod
    def unload(self) -> None:
        """Unload the tools feature and clear runtime state."""
        ...

    @abstractmethod
    def tools(self) -> List[ToolboxTool]:
        """Return cached Toolbox tools.

        :returns: List of cached tool models.
        """
        ...

    @abstractmethod
    def tags(self) -> List[ToolboxTag]:
        """Return cached Toolbox tags.

        :returns: List of cached tag models.
        """
        ...

    @abstractmethod
    def tools_with_tags(self) -> List[ToolboxToolWithTags]:
        """Return cached tools enriched with cached tags.

        :returns: List of enriched tool models.
        """
        ...

    @abstractmethod
    def fetch_tool_io_parameters(
        self,
        tool_name: str,
    ) -> Tuple[List[ToolboxParameter], List[ToolboxParameter]]:
        """Fetch input and output parameters for a tool.

        :param tool_name: Toolbox tool identifier.

        :returns: Tuple with input and output parameter lists.
        """
        ...
