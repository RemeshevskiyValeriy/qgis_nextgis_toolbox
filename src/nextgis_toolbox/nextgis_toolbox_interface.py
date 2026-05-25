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
import sys
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Optional, cast

from osgeo import gdal
from qgis import utils
from qgis.core import Qgis, QgsApplication, QgsTaskManager
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import (
    QT_VERSION_STR,
    QObject,
    QSysInfo,
    QTranslator,
    pyqtSignal,
    pyqtSlot,
)

from nextgis_toolbox.core.constants import PACKAGE_NAME, PLUGIN_NAME
from nextgis_toolbox.core.exceptions import NextgisToolboxError
from nextgis_toolbox.core.logging import logger, unload_logger
from nextgis_toolbox.core.utils import qgis_locale
from nextgis_toolbox.notifier.cli_notifier import CliNotifier
from nextgis_toolbox.notifier.message_bar_notifier import MessageBarNotifier
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

    class Mode(Enum):
        """Enum representing the plugin mode."""

        LOADING = "loading"
        GUI = "gui"
        PROCESSING = "processing"
        ERROR = "error"
        UNLOADED = "unloaded"

    settings_changed = pyqtSignal()
    _instance: Optional["NextgisToolboxInterface"] = None

    def __init__(self, iface: QgisInterface) -> None:
        super().__init__(iface)
        self._log_versions()

        NextgisToolboxInterface._instance = self

        self._mode = self.Mode.LOADING
        self._is_gui_loaded = False
        self._is_processing_loaded = False
        self._notifier = None  # type: Optional[NotifierInterface]
        self._translators = list()

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
    def mode(self) -> Mode:
        """Return the plugin mode.

        :returns: The plugin mode (GUI or PROCESSING).
        """
        return self._mode

    @property
    def notifier(self) -> "NotifierInterface":
        """Return the notifier for displaying messages to the user.

        :returns: Notifier interface instance.
        """
        if self._notifier is None:
            raise NextgisToolboxError(
                "Using notifier before it was initialized"
            )
        return self._notifier

    @property
    def tools_manager(self) -> "ToolsInterface":
        """Return the tools feature manager.

        :returns: Tools feature interface instance.

        :raises NextgisToolboxError: If a plugin implementation does not
            provide the tools feature.
        """
        raise NextgisToolboxError(
            "Plugin does not implement tools manager access"
        )

    @property
    def tasks_manager(self) -> "TasksInterface":
        """Return the tasks feature manager.

        :returns: Tasks feature interface instance.

        :raises NextgisToolboxError: If a plugin implementation does not
            provide the tasks feature.
        """
        raise NextgisToolboxError(
            "Plugin does not implement tasks manager access"
        )

    @property
    def qgis_tasks_manager(self) -> QgsTaskManager:
        raise NextgisToolboxError(
            "Plugin does not implement QGIS tasks manager access"
        )

    @pyqtSlot()
    def open_about_dialog(self) -> None:
        """Open the plugin about dialog."""
        raise NextgisToolboxError("Plugin does not implement about dialog")

    @pyqtSlot()
    def open_settings(self) -> None:
        """Open the plugin settings dialog."""
        self.qgis_iface.showOptionsDialog(
            self.qgis_iface.mainWindow(), PLUGIN_NAME
        )

    def initGui(self) -> None:
        """Initialize the GUI components and load necessary resources."""
        self._mode = self.Mode.GUI
        self._notifier = MessageBarNotifier(self)

        try:
            self._load_translations()

            if self.metadata.getboolean("general", "hasProcessingProvider"):
                self._init_processing()

            self._is_gui_loaded = self._load_ui()
            if not self._is_gui_loaded:
                raise NextgisToolboxError("Failed to load GUI components")

        except Exception as error:
            logger.error("An error occurred while initializing the GUI")
            self._process_error(error)
            return

        logger.debug(f"✓ Plugin initialized in {self._mode.name} mode")

    def initProcessing(self) -> None:
        """Initialize the processing provider and algorithms."""
        self._mode = self.Mode.PROCESSING
        self._notifier = CliNotifier(self)

        try:
            self._init_processing()

        except Exception as error:
            logger.error("An error occurred while initializing processing")
            self._process_error(error)
            return

        logger.debug(f"✓ Plugin initialized in {self._mode.name} mode")

    def unload(self) -> None:
        """Unload the plugin and perform cleanup operations."""
        try:
            if self._is_gui_loaded:
                self._unload_ui()

            if self._is_processing_loaded:
                self._unload_processing()

            if self._translators:
                self._unload_translations()

            self._unload_notifier()

        except Exception:
            logger.warning(
                "An error occurred while unloading the plugin, some resources"
                " may not be cleaned up properly"
            )

        finally:
            if NextgisToolboxInterface._instance is self:
                NextgisToolboxInterface._instance = None

        logger.debug("✓ Plugin unloaded")

        unload_logger()

        self._mode = self.Mode.UNLOADED

    def _init_processing(self) -> None:
        """Initialize the processing provider and algorithms."""
        if self.mode == self.Mode.ERROR:
            logger.debug(
                "Plugin is in error mode, skipping processing provider initialization"
            )
            return

        self._is_processing_loaded = self._load_processing()
        if not self._is_processing_loaded:
            raise NextgisToolboxError("Failed to load processing provider")

    def _load_ui(self) -> bool:
        """Load the plugin resources and initialize components.

        This method must be implemented by subclasses.
        """
        if self._mode == self.Mode.ERROR:
            logger.debug("Plugin is in error mode, skipping UI loading")
            return False

        raise NextgisToolboxError(
            "Plugin has UI components but they are not implemented"
        )

    def _unload_ui(self) -> None:
        """Unload the plugin resources and clean up components.

        This method must be implemented by subclasses.
        """
        if self._mode == self.Mode.ERROR:
            logger.debug("Plugin is in error mode, skipping UI unloading")
            return

        raise NextgisToolboxError(
            "Plugin has UI components but they are not implemented"
        )

    def _load_processing(self) -> bool:
        """Load the processing provider and algorithms.

        This method must be implemented by subclasses.
        """
        if self.mode == self.Mode.ERROR:
            logger.debug(
                "Plugin is in error mode, skipping processing provider loading"
            )
            return True

        raise NextgisToolboxError(
            "Plugin has processing provider but it is not implemented"
        )

    def _unload_processing(self) -> None:
        """Unload the processing provider and algorithms.

        This method must be implemented by subclasses.
        """
        if self.mode == self.Mode.ERROR:
            logger.debug(
                "Plugin is in error mode, skipping processing provider unloading"
            )
            return

        raise NextgisToolboxError(
            "Plugin has processing provider but it is not implemented"
        )

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

    def _unload_notifier(self) -> None:
        """Unload the notifier component."""
        if self._notifier is None:
            return

        self._notifier.deleteLater()
        self._notifier = None

    def _log_versions(self) -> None:
        """Log versions of QGIS, Python, GDAL, and the plugin itself."""

        logger.debug(f"<b>ⓘ OS:</b> {QSysInfo().prettyProductName()}")
        logger.debug(f"<b>ⓘ Qt version:</b> {QT_VERSION_STR}")
        logger.debug(f"<b>ⓘ QGIS version:</b> {Qgis.version()}")
        logger.debug(f"<b>ⓘ Python version:</b> {sys.version}")
        logger.debug(f"<b>ⓘ GDAL version:</b> {gdal.__version__}")
        logger.debug(f"<b>ⓘ Plugin version:</b> {self.version}")
        logger.debug(
            f"<b>ⓘ Plugin path:</b> {self.path}"
            + (f" -> {self.path.resolve()}" if self.path.is_symlink() else "")
        )

    def _process_error(self, error: Exception) -> None:
        """Log an error with its traceback."""
        self._mode = self.Mode.ERROR
        if self._notifier is not None:
            self._notifier.display_exception(error)
        else:
            logger.exception(f"An error occurred: {error}")


class NextgisToolboxPluginStub(NextgisToolboxInterface):
    """Stub implementation of plugin interface used to notify the user when the plugin failed to start."""

    def __init__(self, iface: QgisInterface) -> None:
        """Initialize the plugin stub."""
        super().__init__(iface)
        self._mode = self.Mode.ERROR
        logger.debug("<b>✓ Plugin stub created</b>")
