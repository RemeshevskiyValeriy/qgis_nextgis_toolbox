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

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID


@dataclass
class ToolboxOrderParameters:
    """
    Represents NextGIS Toolbox order execution parameters.
    """

    operation_name: str
    inputs: Dict[str, Any]

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "ToolboxOrderParameters":
        """
        Create order parameters instance from API response.

        :param data: Order parameters definition.

        :returns: NextGIS Toolbox order parameters instance.
        """

        return cls(
            operation_name=data["operation_name"],
            inputs=data["inputs"],
        )


@dataclass
class ToolboxOrder:
    """
    Represents a NextGIS Toolbox execution order.
    """

    id: int
    guid: UUID
    created_at: datetime
    parameters: ToolboxOrderParameters
    status: str
    priority: int
    error: Optional[str] = None

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "ToolboxOrder":
        """
        Create order instance from API response.

        :param data: Order definition from Toolbox API.

        :returns: NextGIS Toolbox order instance.
        """

        return cls(
            id=data["id"],
            guid=UUID(data["guid"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            parameters=ToolboxOrderParameters.from_dict(data["parameters"]),
            status=data["status"],
            priority=data["priority"],
            error=data.get("error"),
        )
