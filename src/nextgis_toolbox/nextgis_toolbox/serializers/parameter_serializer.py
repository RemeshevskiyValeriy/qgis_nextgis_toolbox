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

from nextgis_toolbox.nextgis_toolbox.models.parameter import (
    ToolboxParameter,
)


class ToolboxParameterSerializer:
    """
    Serialize and deserialize NextGIS Toolbox parameter models.
    """

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> ToolboxParameter:
        """
        Build parameter model from API response payload.

        :param data: Raw API payload.

        :returns: Parsed NextGIS Toolbox parameter model.
        """

        return ToolboxParameter(
            name=data["name"],
            parameter_type=data["type"],
            alias=data.get("alias"),
            description=data.get("description"),
            required=data.get("required", False),
            choices=data.get("choices"),
        )

    @staticmethod
    def to_dict(parameter: ToolboxParameter) -> Dict[str, Any]:
        """
        Convert parameter model to dictionary.

        :param parameter: NextGIS Toolbox parameter model.

        :returns: Serialized parameter payload.
        """

        return {
            "name": parameter.name,
            "type": parameter.parameter_type,
            "alias": parameter.alias,
            "description": parameter.description,
            "required": parameter.required,
            "choices": parameter.choices,
        }
