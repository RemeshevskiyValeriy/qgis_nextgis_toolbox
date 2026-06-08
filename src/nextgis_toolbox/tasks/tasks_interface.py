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
from typing import TYPE_CHECKING, Any, Dict, Optional

from qgis.core import QgsFeedback
from qgis.PyQt.QtCore import QObject, pyqtSignal

from nextgis_toolbox.shared.qobject_metaclass import QObjectMetaClass
from nextgis_toolbox.tasks.models import ToolboxTaskInformation

if TYPE_CHECKING:
    from nextgis_toolbox.tasks.api import TasksApi


class TasksInterface(QObject, metaclass=QObjectMetaClass):
    """Abstract QObject interface for the tasks feature."""

    task_created = pyqtSignal(str)

    def api(self) -> "TasksApi":
        """Return the API for managing tasks.

        :returns: Tasks API instance.
        """
        ...

    def set_api(self, tasks_api: "TasksApi") -> None:
        """Set the API for managing tasks.

        :param tasks_api: API for managing tasks.
        """
        ...

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
    def task_information(
        self,
        task_id: str,
        feedback: Optional[QgsFeedback] = None,
    ) -> ToolboxTaskInformation:
        """Retrieve Toolbox task information.

        :param task_id: Toolbox task identifier.
        :param feedback: Optional feedback object for progress reporting.

        :returns: Toolbox task model.
        """
        ...
