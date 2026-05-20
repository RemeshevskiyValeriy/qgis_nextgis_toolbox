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

from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest

from nextgis_toolbox.nextgis_toolbox.sdk.authentication import (
    ToolboxTokenAuthentication,
)


def test_token_authentication_applies_authorization_header() -> None:
    token = "00000000-0000-0000-0000-000000000001"
    request = QNetworkRequest(QUrl("http://example.com"))

    authentication = ToolboxTokenAuthentication(token)
    authentication.apply(request)

    assert authentication.token == token
    assert authentication.headers == {
        "Authorization": f"Token {token}",
    }
    assert (
        bytes(request.rawHeader(b"Authorization")).decode("utf-8")  # type: ignore
        == f"Token {token}"
    )
