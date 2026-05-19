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

import configparser
from abc import abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Optional, cast

from qgis import utils
from qgis.core import QgsApplication
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QObject, QTranslator, pyqtSignal, pyqtSlot

from nextgis_toolbox.core.constants import PACKAGE_NAME
from nextgis_toolbox.core.logging import logger, unload_logger
from nextgis_toolbox.core.utils import qgis_locale
from nextgis_toolbox.shared.qobject_metaclass import QObjectMetaClass

if TYPE_CHECKING:
    from nextgis_toolbox.nextgis_toolbox.tasks.tasks_interface import (
        TasksInterface,
    )
    from nextgis_toolbox.nextgis_toolbox.tools.tools_interface import (
        ToolsInterface,
    )
    from nextgis_toolbox.notifier.notifier_interface import (
        NotifierInterface,
    )


class NextgisToolboxInterface(QObject, metaclass=QObjectMetaClass):
    """Interface for the NextGIS Toolbox.

    This abstract base class provides singleton access to the plugin
    instance, exposes plugin metadata, version, and path, and defines
    abstract properties and methods that must be implemented by concrete
    subclasses.
    """

    settings_changed = pyqtSignal()
    _instance: Optional["NextgisToolboxInterface"] = None

    def __init__(self, iface: QgisInterface) -> None:
        super().__init__(iface)

        NextgisToolboxInterface._instance = self

        self._is_gui_loaded = False
        self._is_processing_loaded = False

    @classmethod
    def instance(cls) -> "NextgisToolboxInterface":
        """Return the singleton instance of the NextGIS Toolbox.

        :returns: The NextgisToolboxInterface plugin instance.

        :raises AssertionError: If the plugin has not been created yet.
        """
        plugin = cls._instance
        assert plugin is not None, "Using a plugin before it was created"
        return plugin

    @property
    def qgis_iface(self) -> QgisInterface:
        """Return the QGIS interface instance.

        :returns: QGIS interface instance.
        """
        return cast(QgisInterface, self.parent())

    @property
    def metadata(self) -> configparser.ConfigParser:
        """Return the parsed metadata for the plugin.

        :returns: Parsed metadata as a ConfigParser object.
        """
        metadata = utils.plugins_metadata_parser.get(PACKAGE_NAME)
        assert metadata is not None, "Using a plugin before it was created"
        return metadata

    @property
    def version(self) -> str:
        """Return the plugin version.

        :returns: Plugin version string.
        """
        return self.metadata.get("general", "version")

    @property
    def path(self) -> "Path":
        """Return the plugin path.

        :returns: Path to the plugin directory.
        """
        return Path(__file__).parent

    @property
    @abstractmethod
    def notifier(self) -> "NotifierInterface":
        """Return the notifier for displaying messages to the user.

        :returns: Notifier interface instance.
        """
        ...

    @property
    def tools_manager(self) -> "ToolsInterface":
        """Return the tools feature manager.

        :returns: Tools feature interface instance.

        :raises NotImplementedError: If a plugin implementation does not
            provide the tools feature.
        """
        raise NotImplementedError

    @property
    def tasks_manager(self) -> "TasksInterface":
        """Return the tasks feature manager.

        :returns: Tasks feature interface instance.

        :raises NotImplementedError: If a plugin implementation does not
            provide the tasks feature.
        """
        raise NotImplementedError

    @pyqtSlot()
    @abstractmethod
    def open_about_dialog(self) -> None:
        """Open the plugin about dialog."""
        ...

    def initGui(self) -> None:
        """Initialize the GUI components and load necessary resources."""
        self._translators = list()

        if self.metadata.get("general", "hasProcessingProvider"):
            self.initProcessing()

        try:
            self._load_translations()
            self._is_gui_loaded = self._load_ui()
        except Exception:
            logger.exception("An error occurred while plugin loading")

    def initProcessing(self) -> None:
        """Initialize the processing provider and algorithms."""
        try:
            self._is_processing_loaded = self._load_processing()
        except Exception:
            logger.exception("An error occurred while initializing processing")

    def unload(self) -> None:
        """Unload the plugin and perform cleanup operations."""
        try:
            if self._is_gui_loaded:
                self._unload_ui()
                self._unload_translations()
            if self._is_processing_loaded:
                self._unload_processing()
        except Exception:
            logger.exception("An error occurred while plugin unloading")
        finally:
            if NextgisToolboxInterface._instance is self:
                NextgisToolboxInterface._instance = None

        unload_logger()

    @abstractmethod
    def _load_ui(self) -> bool:
        """Load the plugin resources and initialize components.

        This method must be implemented by subclasses.
        """
        ...

    @abstractmethod
    def _unload_ui(self) -> None:
        """Unload the plugin resources and clean up components.

        This method must be implemented by subclasses.
        """
        ...

    def _load_processing(self) -> bool:
        """Load the processing provider and algorithms.

        This method must be implemented by subclasses.
        """
        return False

    def _unload_processing(self) -> None:
        """Unload the processing provider and algorithms.

        This method must be implemented by subclasses.
        """
        pass

    def _add_translator(self, translator_path: Path) -> None:
        """Add a translator for the plugin.

        :param translator_path: Path to the translation file.
        """
        translator = QTranslator()
        is_loaded = translator.load(str(translator_path))
        if not is_loaded:
            logger.debug(f"Translator {translator_path} wasn't loaded")
            return

        is_installed = QgsApplication.installTranslator(translator)
        if not is_installed:
            logger.error(f"Translator {translator_path} wasn't installed")
            return

        # Should be kept in memory
        self._translators.append(translator)

    def _load_translations(self) -> None:
        """Load translation files for the plugin."""
        self._translators = list()
        locale = qgis_locale()
        if locale == "en":
            return

        translator_path = self.path / "i18n" / f"{PACKAGE_NAME}_{locale}.qm"
        self._add_translator(translator_path)

    def _unload_translations(self) -> None:
        """Remove all translators added by the plugin."""
        for translator in self._translators:
            QgsApplication.removeTranslator(translator)
        self._translators.clear()
