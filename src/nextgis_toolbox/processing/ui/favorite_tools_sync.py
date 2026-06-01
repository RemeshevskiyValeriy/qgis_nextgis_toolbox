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

from typing import Optional, Set

from qgis.gui import QgsGui, QgsProcessingFavoriteAlgorithmManager
from qgis.PyQt.QtCore import QObject, pyqtSlot

from nextgis_toolbox.core.logging import logger
from nextgis_toolbox.nextgis_toolbox.sdk.client import ToolboxApiClient
from nextgis_toolbox.nextgis_toolbox.tools.tools_interface import (
    ToolsInterface,
)
from nextgis_toolbox.processing.utils import toolbox_algorithm_id
from nextgis_toolbox.settings.nextgis_toolbox_settings import (
    AuthenticationType,
)


class FavoriteToolsSync(QObject):
    def __init__(
        self,
        api_client: ToolboxApiClient,
        tools_manager: ToolsInterface,
        provider_id: str,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._api_client = api_client
        self._tools_manager = tools_manager
        self._provider_id = provider_id
        self._is_connected = False
        self._is_updating_processing_favorites = False

    def start(self) -> None:
        favorite_manager = self._favorite_manager()
        if not self._is_connected:
            favorite_manager.changed.connect(self._on_favorites_changed)
            self._is_connected = True

        self._apply_remote_favorites()

    def stop(self) -> None:
        if not self._is_connected:
            return

        favorite_manager = self._favorite_manager()
        favorite_manager.changed.disconnect(self._on_favorites_changed)
        self._is_connected = False

    @pyqtSlot()
    def _on_favorites_changed(self) -> None:
        if self._is_updating_processing_favorites:
            return

        self._sync_tools_from_processing(
            sync_remote=self._api_client.authentication_type
            != AuthenticationType.NONE
        )

    def _apply_remote_favorites(self) -> None:
        favorite_manager = self._favorite_manager()
        self._is_updating_processing_favorites = True

        try:
            for algorithm_id in self._processing_favorite_ids():
                if not algorithm_id.startswith(f"{self._provider_id}:"):
                    continue

                favorite_manager.remove(algorithm_id)

            for tool in self._tools_manager.tools():
                algorithm_id = toolbox_algorithm_id(
                    self._provider_id,
                    tool.name,
                )
                if tool.is_favorite:
                    favorite_manager.add(algorithm_id)
        finally:
            self._is_updating_processing_favorites = False

    def _sync_tools_from_processing(self, *, sync_remote: bool) -> None:
        processing_favorite_ids = self._processing_favorite_ids()

        for tool in self._tools_manager.tools():
            is_processing_favorite = (
                toolbox_algorithm_id(self._provider_id, tool.name)
                in processing_favorite_ids
            )
            if tool.is_favorite is is_processing_favorite:
                continue

            try:
                self._tools_manager.set_tool_favorite(
                    tool.name,
                    is_processing_favorite,
                    sync_remote=sync_remote,
                )
            except Exception:
                logger.exception(
                    f"Failed to sync favorite state for '{tool.name}'"
                )

    def _processing_favorite_ids(self) -> Set[str]:
        return set(self._favorite_manager().favoriteAlgorithmIds())

    def _favorite_manager(self) -> QgsProcessingFavoriteAlgorithmManager:
        return QgsGui.instance().processingFavoriteAlgorithmManager()
