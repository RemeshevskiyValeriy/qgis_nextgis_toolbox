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

from abc import ABC, abstractmethod

from nextgis_toolbox.processing.toolbox_algorithm import (
    ToolboxAlgorithm,
)
from nextgis_toolbox.processing.ui.compat import AlgorithmDialog


class AlgorithmDialogPatch(ABC):
    @abstractmethod
    def apply(
        self,
        dialog: AlgorithmDialog,
        algorithm: ToolboxAlgorithm,
    ) -> None: ...
