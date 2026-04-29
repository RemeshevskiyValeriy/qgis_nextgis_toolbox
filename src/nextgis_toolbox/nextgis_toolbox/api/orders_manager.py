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

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from nextgis_toolbox.nextgis_toolbox.models.order import ToolboxOrder
from nextgis_toolbox.nextgis_toolbox.models.result import ToolboxResult

if TYPE_CHECKING:
    from nextgis_toolbox.nextgis_toolbox.api.client import ToolboxApiClient


class ToolboxOrdersManager:
    """
    Manage NextGIS Toolbox orders and result downloads.
    """

    def __init__(self, client: "ToolboxApiClient") -> None:
        """
        Initialize orders manager.

        :param client: Shared API client instance.
        """
        self.client = client
        self.orders: List[ToolboxOrder] = self.get_orders()

    def get_orders(self) -> List[ToolboxOrder]:
        """
        Fetch user orders from API.

        :returns: List of toolbox orders.
        """

        response_data = self.client.get(
            sub_url="orders",
            use_auth=True,
        )

        return [
            ToolboxOrder.from_dict(order_data)
            for order_data in response_data["data"]
        ]

    def update_orders(self) -> None:
        """
        Refresh cached orders list.
        """

        self.orders = self.get_orders()

    def get_status(self, order_id: str) -> Dict[Any, Any]:
        """
        Fetch order status.

        :param order_id: Order identifier.

        :returns: Parsed API response.
        """

        return self.client.get(
            sub_url=f"json/status/{order_id}/",
            use_auth=True,
        )

    def download_file(
        self,
        url: str,
        directory: Path,
        filename: Optional[str] = None,
    ) -> Path:
        """
        Download file from NextGIS Toolbox API.

        :param url: File URL.
        :param directory: Target directory.
        :param filename: Optional target filename.

        :returns: Saved file path.
        """

        content = self.client.get_content(
            sub_url=url,
            use_auth=True,
        )

        if filename is None:
            filename = Path(url).name

            filename = self.generate_unique_name(
                filename,
                directory,
            )

        file_path = directory / filename
        file_path.write_bytes(content)

        return file_path

    def get_result(
        self,
        result: ToolboxResult,
        directory: Path,
    ) -> Path:
        """
        Download a single result file.

        :param result: Toolbox result object.
        :param directory: Target directory.

        :returns: Saved file path.
        """

        return self.download_file(result.value, directory)

    def get_results(
        self,
        results: List[ToolboxResult],
        directory: Path,
    ) -> List[Path]:
        """
        Download multiple result files.

        :param results: List of toolbox results.
        :param directory: Target directory.

        :returns: List of saved file paths.
        """

        return [
            self.download_file(result.value, directory) for result in results
        ]

    def generate_unique_name(
        self,
        filename: str,
        directory: Path,
    ) -> str:
        """
        Generate unique filename inside directory.

        :param filename: Original filename.
        :param directory: Target directory.

        :returns: Unique filename.
        """

        stem = Path(filename).stem
        suffix = Path(filename).suffix

        existing_names = [
            path.stem
            for path in directory.iterdir()
            if path.is_file() and path.suffix == suffix
        ]

        if re.search(r"\(\d+\)$", stem):
            stem = re.sub(r"\(\d+\)$", "", stem)

        candidate = stem
        index = 1

        while candidate in existing_names:
            candidate = f"{stem}({index})"
            index += 1

        return f"{candidate}{suffix}"
