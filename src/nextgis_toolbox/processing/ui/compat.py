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

from typing import TYPE_CHECKING

from qgis.core import QgsApplication

IS_DESKTOP_PLATFORM = QgsApplication.platform() == "desktop"

if TYPE_CHECKING or IS_DESKTOP_PLATFORM:
    try:
        from processing.gui.AlgorithmDialog import AlgorithmDialog
    except ModuleNotFoundError:
        from processing.gui.algorithm_widget import (
            AlgorithmWidget as AlgorithmDialog,
        )
    from processing.gui.ParametersPanel import ParametersPanel
    from processing.gui.ProcessingToolbox import ProcessingToolbox
    from processing.gui.ProviderActions import (
        ProviderActions,
        ProviderContextMenuActions,
    )
else:
    AlgorithmDialog = object
    ParametersPanel = object
    ProcessingToolbox = object
    ProviderActions = object
    ProviderContextMenuActions = object


__all__ = [
    "AlgorithmDialog",
    "IS_DESKTOP_PLATFORM",
    "ParametersPanel",
    "ProcessingToolbox",
]
