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

from typing import Dict
from uuid import UUID


class ToolboxAuthentication:
    """
    Represents NextGIS Toolbox authentication credentials.
    """

    def __init__(self, token: str) -> None:
        """
        Initialize authentication instance.

        :param token: NextGIS Toolbox API token.
        """

        self.token: UUID = UUID(token)

    def get_headers(self) -> Dict[str, str]:
        """
        Build authorization headers for API requests.

        :returns: HTTP headers with authorization token.
        """

        return {
            "Authorization": f"Token {self.token}",
        }
