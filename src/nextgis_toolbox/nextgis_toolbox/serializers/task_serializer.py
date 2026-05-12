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

from typing import Any, Dict

from nextgis_toolbox.nextgis_toolbox.models.task import (
    ToolboxTask,
)
from nextgis_toolbox.nextgis_toolbox.serializers.result_serializer import (
    ToolboxResultSerializer,
)


class ToolboxTaskSerializer:
    """
    Serializer for :class:`ToolboxTask`.
    """

    @staticmethod
    def from_dict(
        data: Dict[str, Any],
    ) -> ToolboxTask:
        """
        Deserialize toolbox task from API response.

        :param data: Raw API payload.

        :returns: Toolbox task model.
        """

        return ToolboxTask(
            tool=data["tool"],
            status=data["status"],
            progress=data["progress"],
            error=data.get("error"),
            results=[
                ToolboxResultSerializer.from_dict(result_data)
                for result_data in data.get("output", [])
            ],
            operation=data["operation"],
            state=data["state"],
        )

    @staticmethod
    def to_dict(
        task: ToolboxTask,
    ) -> Dict[str, Any]:
        """
        Serialize toolbox task to dictionary.

        :param task: Toolbox task model.

        :returns: Serialized dictionary.
        """

        return {
            "tool": task.tool,
            "status": task.status,
            "progress": task.progress,
            "error": task.error,
            "output": [
                ToolboxResultSerializer.to_dict(result)
                for result in task.results
            ],
            "operation": task.operation,
            "state": task.state,
        }
