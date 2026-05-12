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

from pathlib import Path
from typing import Any, Dict, List, Optional

from nextgis_toolbox.nextgis_toolbox.api.client import (
    ToolboxApiClient,
)
from nextgis_toolbox.nextgis_toolbox.models.result import (
    ToolboxResult,
)
from nextgis_toolbox.nextgis_toolbox.models.task import (
    ToolboxTask,
)
from nextgis_toolbox.nextgis_toolbox.serializers.task_serializer import (
    ToolboxTaskSerializer,
)


class ToolboxTasksManager:
    """
    Manage toolbox tasks and results.
    """

    def __init__(
        self,
    ) -> None:
        """
        Initialize tasks manager.
        """

        self.client = ToolboxApiClient()

    def submit_task(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        emailing: bool = False,
    ) -> str:
        """
        Submit toolbox task.

        :param tool_name: Toolbox tool identifier.
        :param inputs: Tool input values.
        :param emailing: Enable result emailing.

        :returns: Created task identifier.
        """

        payload = {
            "tool": tool_name,
            "inputs": inputs,
            "mode": "api",
            "emailing": emailing,
        }

        response_data = self.client.post(
            sub_url="tasks/",
            payload=payload,
            use_auth=True,
        )

        return response_data["task_id"]

    def retrieve_task(
        self,
        task_id: str,
    ) -> ToolboxTask:
        """
        Retrieve toolbox task information.

        :param task_id: Toolbox task identifier.

        :returns: Toolbox task model.
        """

        response_data = self.client.get(
            sub_url=f"tasks/{task_id}",
            use_auth=True,
        )

        return ToolboxTaskSerializer.from_dict(response_data)

    def get_results(
        self,
        task_id: str,
    ) -> List[ToolboxResult]:
        """
        Retrieve toolbox task results.

        :param task_id: Toolbox task identifier.

        :returns: Toolbox results.
        """

        task = self.retrieve_task(task_id)

        return task.results

    def _download_result(
        self,
        result: ToolboxResult,
        directory: Path,
        filename: Optional[str] = None,
    ) -> Path:
        """
        Download toolbox result file.

        :param result: Toolbox result descriptor.
        :param directory: Target directory.
        :param filename: Optional output filename.

        :returns: Saved file path.
        """

        return self._download_file(
            result.value,
            directory,
            filename,
        )

    def download_results(
        self,
        results: List[ToolboxResult],
        directory: Path,
    ) -> List[Path]:
        """
        Download multiple toolbox result files.

        :param results: Toolbox results.
        :param directory: Target directory.

        :returns: Saved file paths.
        """

        return [self._download_result(result, directory) for result in results]

    def _download_file(
        self,
        url: str,
        directory: Path,
        filename: Optional[str] = None,
    ) -> Path:
        """
        Download file from NextGIS Toolbox API.

        :param url: File URL.
        :param directory: Target directory.
        :param filename: Optional output filename.

        :returns: Saved file path.
        """

        content = self.client.get_content(
            sub_url=url,
            use_auth=True,
        )

        if filename is None:
            filename = Path(url).name

        file_path = directory / filename

        file_path.write_bytes(content)

        return file_path
