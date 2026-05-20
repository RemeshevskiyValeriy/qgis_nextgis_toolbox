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

from typing import Any, Dict, List

from nextgis_toolbox.nextgis_toolbox.sdk.client import ToolboxApiClient


class ToolsApi:
    """API gateway for NextGIS Toolbox tools endpoints."""

    def __init__(self, client: ToolboxApiClient) -> None:
        """Initialize API gateway.

        :param client: Low-level Toolbox API client.
        """
        self._client = client

    @property
    def client(self) -> ToolboxApiClient:
        """Low-level API client."""
        return self._client

    def fetch_tools(self) -> List[Dict[str, Any]]:
        """Fetch raw tool summary payloads.

        :returns: List of raw tool dictionaries.
        """
        response_data = self._client.get("tools/")
        return response_data["data"]

    def fetch_tags(self) -> List[Dict[str, Any]]:
        """Fetch raw tags payloads.

        :returns: List of raw tag dictionaries.
        """
        response_data = self._client.get("tags/")
        return response_data["data"]

    def fetch_tool(
        self,
        tool_name: str,
    ) -> Dict[str, Any]:
        """Fetch raw tool details.

        :param tool_name: Toolbox tool identifier.

        :returns: Raw tool dictionary.
        """
        return self._client.get(f"tools/{tool_name}")
