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

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type


@dataclass
class ToolboxParameter:
    """
    Represents a NextGIS Toolbox operation input or output parameter.
    """

    name: str
    title: str
    description: str
    widget: str
    required: bool
    validators: List[Any]
    extension: Optional[str]
    value_type: Type
    value: Optional[Any] = field(default=None)

    _TYPE_MAPPING = {
        "float": float,
        "int": int,
        "string": str,
        "boolean": bool,
        "file": str,
    }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "ToolboxParameter":
        """
        Create parameter instance from API response.

        :param data: Parameter definition from NextGIS Toolbox API.

        :returns: NextGIS Toolbox parameter instance.
        """

        parameter_type = data["type"]

        return cls(
            name=data["name"],
            title=data["title"],
            description=data["description"],
            widget=data["widget"],
            required=data["required"],
            validators=data["validators"],
            extension=data.get("extension"),
            value_type=cls._TYPE_MAPPING[parameter_type],
        )

    def set_value(self, value: Any) -> None:
        """
        Set parameter value with type conversion.

        :param value: Input value.
        """

        self.value = self.value_type(value)
