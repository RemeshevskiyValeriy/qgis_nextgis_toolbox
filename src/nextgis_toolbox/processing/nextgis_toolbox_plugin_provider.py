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

from typing import TYPE_CHECKING, Dict

from qgis.core import Qgis, QgsProcessingProvider, QgsRuntimeProfiler
from qgis.PyQt.QtGui import QIcon

from nextgis_toolbox.core.constants import PLUGIN_NAME
from nextgis_toolbox.core.logging import logger
from nextgis_toolbox.notifier.message_bar_notifier import MessageBarNotifier
from nextgis_toolbox.processing.nextgis_toolbox_algorithm import (
    NextgisToolboxAlgorithm,
)
from nextgis_toolbox.ui.icon import plugin_icon

if TYPE_CHECKING:
    from nextgis_toolbox.nextgis_toolbox.api.toolbox import Toolbox
    from nextgis_toolbox.nextgis_toolbox.models.tool import ToolboxTool


class NgToolboxPluginProcessingProvider(QgsProcessingProvider):
    """
    QGIS Processing provider for NextGIS Toolbox tools.
    """

    def __init__(self, toolbox: "Toolbox") -> None:
        """
        Initialize plugin processing provider.
        """
        super().__init__()
        self._toolbox = toolbox

        self._notifier = MessageBarNotifier(self)

    def unload(self) -> None:
        """
        Unloads the provider. Any tear-down steps required by the provider
        should be implemented here.
        """
        pass

    def loadAlgorithms(self) -> None:
        """
        Fetch tool I/O definitions from the API and register algorithms.
        """

        with QgsRuntimeProfiler.profile(
            f"load algs: {len(self._toolbox.tools)}"
        ):  # type: ignore PylancereportAttributeAccessIssue
            load_errors = self._load_tool_algorithms()

            if not load_errors:
                return

            self._notify_load_errors(load_errors)

    def id(self) -> str:
        """
        Return provider ID.

        :returns: Unique provider identifier.
        """
        return "ngtoolbox"

    def name(self) -> str:
        """
        Return provider short name.

        :returns: Provider name.
        """
        return PLUGIN_NAME

    def icon(self) -> QIcon:
        return plugin_icon("nextgis_toolbox_plugin_logo.svg")

    def longName(self) -> str:
        """
        Return provider full name.

        :returns: Full provider name.
        """
        return self.name()

    def _load_tool_algorithms(self) -> Dict[str, str]:
        """
        Load and register toolbox Processing algorithms.

        :returns: Mapping of tool name to error message.
        """
        load_errors: Dict[str, str] = {}

        for tool in self._toolbox.tools:
            if tool.is_dev or tool.name != "Test":
                continue

            try:
                self._add_tool_algorithm(tool)

            except Exception as error:
                load_errors[tool.name] = str(error)

        return load_errors

    def _add_tool_algorithm(
        self,
        tool: "ToolboxTool",
    ) -> None:
        """
        Create and register Processing algorithm for toolbox tool.

        :param tool: Toolbox tool descriptor.
        """
        inputs, outputs = self._toolbox.fetch_tool_io_parameters(tool.name)

        algorithm = NextgisToolboxAlgorithm(
            tool_id=tool.name,
            display_name=tool.alias,
            description=tool.description,
            inputs=inputs,
            outputs=outputs,
        )

        self.addAlgorithm(algorithm)

    def _notify_load_errors(
        self,
        load_errors: Dict[str, str],
    ) -> None:
        """
        Notify user about failed toolbox algorithm loading.

        :param load_errors: Mapping of tool name to error message.
        """
        self._notifier.display_message(
            self.tr(
                "Some tools could not be loaded. See plugin logs for details."
            ),
            level=Qgis.MessageLevel.Warning,
        )

        for tool_name, message in load_errors.items():
            logger.warning(f"Failed to load tool '{tool_name}': {message}")
