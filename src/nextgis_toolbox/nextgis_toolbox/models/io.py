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
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ToolboxParameter:
    """
    Immutable descriptor of a single NextGIS Toolbox input or output.

    All fields are populated directly from the API response; no runtime
    mutation is intended or allowed (``frozen=True``).
    """

    name: str
    parameter_type: str
    alias: Optional[str]
    description: Optional[str]
    required: bool
    choices: Optional[List[Dict[str, Any]]]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolboxParameter":
        """
        Construct a parameter descriptor from a raw API response dict.

        :param data: Single parameter definition from NextGIS Toolbox API.
        :returns: Populated :class:`ToolboxParameter` instance.
        """
        return cls(
            name=data["name"],
            parameter_type=data["type"],
            alias=data.get("alias"),
            description=data.get("description"),
            required=data["required"],
            choices=data.get("choices"),
        )
