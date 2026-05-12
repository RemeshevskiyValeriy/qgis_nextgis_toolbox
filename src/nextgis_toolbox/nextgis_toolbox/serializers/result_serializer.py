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

from nextgis_toolbox.nextgis_toolbox.models.result import (
    ToolboxResult,
)


class ToolboxResultSerializer:
    """
    Serializer for :class:`ToolboxResult`.
    """

    @staticmethod
    def from_dict(
        data: Dict[str, Any],
    ) -> ToolboxResult:
        """
        Deserialize toolbox result from API response.

        :param data: Raw API payload.

        :returns: Toolbox result model.
        """

        return ToolboxResult(
            name=data["name"],
            result_type=data["type"],
            value=data["value"],
        )

    @staticmethod
    def to_dict(
        result: ToolboxResult,
    ) -> Dict[str, Any]:
        """
        Serialize toolbox result to dictionary.

        :param result: Toolbox result model.

        :returns: Serialized dictionary.
        """

        return {
            "name": result.name,
            "type": result.result_type,
            "value": result.value,
        }
