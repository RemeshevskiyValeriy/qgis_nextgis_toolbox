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
from pathlib import Path
from typing import Any, Dict, List

from qgis.PyQt.QtCore import QObject, pyqtSignal

from nextgis_toolbox.nextgis_toolbox.tasks.models import (
    ToolboxResult,
    ToolboxTask,
)
from nextgis_toolbox.shared.qobject_metaclass import QObjectMetaClass


class TasksInterface(QObject, metaclass=QObjectMetaClass):
    """Abstract QObject interface for the tasks feature."""

    task_created = pyqtSignal(str)

    @abstractmethod
    def load(self) -> None:
        """Load the tasks feature."""
        ...

    @abstractmethod
    def unload(self) -> None:
        """Unload the tasks feature and clear runtime state."""
        ...

    @abstractmethod
    def submit_task(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        emailing: bool = False,
    ) -> str:
        """Submit Toolbox task.

        :param tool_name: Toolbox tool identifier.
        :param inputs: Tool input values.
        :param emailing: Enable result emailing.

        :returns: Created task identifier.
        """
        ...

    @abstractmethod
    def retrieve_task(self, task_id: str) -> ToolboxTask:
        """Retrieve Toolbox task information.

        :param task_id: Toolbox task identifier.

        :returns: Toolbox task model.
        """
        ...

    @abstractmethod
    def get_results(self, task_id: str) -> List[ToolboxResult]:
        """Retrieve Toolbox task results.

        :param task_id: Toolbox task identifier.

        :returns: Toolbox result models.
        """
        ...

    @abstractmethod
    def download_results(
        self,
        results: List[ToolboxResult],
        directory: Path,
    ) -> List[Path]:
        """Download multiple Toolbox result files.

        :param results: Toolbox result descriptors.
        :param directory: Target directory.

        :returns: Saved file paths.
        """
        ...
