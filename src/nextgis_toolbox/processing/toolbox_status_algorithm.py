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

from typing import Any, Dict, Optional

from qgis.core import (
    Qgis,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingFeedback,
)
from qgis.PyQt.QtCore import QCoreApplication

from nextgis_toolbox.core.exceptions import ToolboxError
from nextgis_toolbox.nextgis_toolbox_interface import NextgisToolboxInterface
from nextgis_toolbox.tools.models import ToolsManagerState


class ToolboxStatusAlgorithm(QgsProcessingAlgorithm):
    def __init__(
        self,
        state: ToolsManagerState,
        error: Optional[ToolboxError],
    ) -> None:
        super().__init__()
        self._state = state
        self._error = error

    def createInstance(self) -> "ToolboxStatusAlgorithm":
        return type(self)(self._state, self._error)

    def initAlgorithm(
        self,
        configuration: Optional[Dict[Optional[str], Any]] = None,
    ) -> None:
        del configuration

    def processAlgorithm(
        self,
        parameters: Dict[Optional[str], Any],
        context: QgsProcessingContext,
        feedback: Optional[QgsProcessingFeedback],
    ) -> Dict[str, Any]:
        del parameters, context, feedback

        if self._state == ToolsManagerState.LOADING:
            return {}

        NextgisToolboxInterface.instance().notifier.display_message(
            self.tr("The tools catalog could not be loaded."),
            level=Qgis.MessageLevel.Critical,
        )
        return {}

    def name(self) -> str:
        if self._state == ToolsManagerState.LOADING:
            return "catalog_loading"

        return "catalog_error"

    def displayName(self) -> str:
        if self._state == ToolsManagerState.LOADING:
            return self.tr("Loading tools…")

        return self.tr("Tools are unavailable")

    def shortDescription(self) -> str:
        return self.canExecute()[1]

    def shortHelpString(self) -> str:
        return self.canExecute()[1]

    def flags(self) -> QgsProcessingAlgorithm.Flag:  # pyright: ignore[reportAttributeAccessIssue]
        return (
            super().flags()
            | QgsProcessingAlgorithm.Flag.FlagDisplayNameIsLiteral  # pyright: ignore[reportAttributeAccessIssue]
        )

    def tr(self, text: str) -> str:
        return QCoreApplication.translate(self.__class__.__name__, text)
