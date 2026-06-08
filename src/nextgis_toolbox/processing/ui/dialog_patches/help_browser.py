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

import html
import re
import shutil
from base64 import b64encode
from functools import partial
from hashlib import sha256
from pathlib import Path
from tempfile import mkdtemp
from typing import TYPE_CHECKING, Callable, Dict, Optional, Sequence, Tuple

import qgis.gui
from qgis.core import QgsApplication, QgsTask, QgsTaskManager
from qgis.PyQt import sip
from qgis.PyQt.QtCore import QBuffer, QByteArray, QIODevice, Qt, QUrl
from qgis.PyQt.QtGui import QDesktopServices, QImage
from qgis.PyQt.QtWidgets import QTextBrowser, QWidget

from nextgis_toolbox.core.exceptions import ToolboxError
from nextgis_toolbox.core.logging import logger
from nextgis_toolbox.nextgis_toolbox_interface import (
    NextgisToolboxInterface,
)
from nextgis_toolbox.processing.tool_content_formatter import ToolHelpImage
from nextgis_toolbox.processing.toolbox_algorithm import (
    ToolboxAlgorithm,
)
from nextgis_toolbox.processing.ui.compat import AlgorithmDialog

if hasattr(qgis.gui, "QgsExternalResourceWidget"):
    from nextgis_toolbox.processing.ui.help_image_preview_dialog import (
        HelpImagePreviewDialog,
    )
else:
    HelpImagePreviewDialog = None

from .common import AlgorithmDialogPatch
from .dialog_runtime import DialogWidgetAccessor

if TYPE_CHECKING:
    from nextgis_toolbox.api.client import ToolboxApiClient

TOOLBOX_HELP_IMAGES_TASK_ATTRIBUTE = "_nextgis_toolbox_help_images_task"
TOOLBOX_HELP_IMAGES_DIRECTORY_ATTRIBUTE = (
    "_nextgis_toolbox_help_images_directory"
)
HELP_IMAGES_PATCHED_PROPERTY = "_nextgis_toolbox_help_images_patched"
HELP_ANCHOR_PATCHED_PROPERTY = "_nextgis_toolbox_help_anchor_patched"
HELP_IMAGE_PATHS_ATTRIBUTE = "_nextgis_toolbox_help_image_paths"


class HelpBrowserState:
    def __init__(
        self,
        widget_accessor: Optional[DialogWidgetAccessor] = None,
    ) -> None:
        self._widget_accessor = widget_accessor or DialogWidgetAccessor()

    def browser(
        self,
        dialog: AlgorithmDialog,
    ) -> Optional[QTextBrowser]:
        """Return the active help browser widget for the dialog."""
        help_browser = self._widget_accessor.help_browser(dialog)
        if help_browser is None or sip.isdeleted(help_browser):
            return None

        return help_browser

    def set_cached_image_paths(
        self,
        help_browser: QTextBrowser,
        image_paths: Dict[str, str],
    ) -> None:
        setattr(help_browser, HELP_IMAGE_PATHS_ATTRIBUTE, dict(image_paths))

    def cached_image_path(
        self,
        help_browser: QTextBrowser,
        url: QUrl,
    ) -> Optional[str]:
        if sip.isdeleted(help_browser):
            return None

        try:
            cached_paths = getattr(
                help_browser,
                HELP_IMAGE_PATHS_ATTRIBUTE,
                {},
            )
        except RuntimeError:
            return None

        if not isinstance(cached_paths, dict):
            return None

        for candidate in (url.toString(), url.toDisplayString()):
            image_path = cached_paths.get(candidate)
            if not isinstance(image_path, str):
                continue

            if Path(image_path).is_file():
                return image_path

        return None


class HelpImageTaskSupport:
    def wrap_help_image_links(
        self,
        help_html: str,
        help_images: Sequence[ToolHelpImage],
        image_sources: Dict[str, str],
    ) -> str:
        wrapped_help_html = help_html

        for help_image in help_images:
            rendered_source = image_sources.get(help_image.placeholder)
            if rendered_source is None:
                continue

            escaped_source = html.escape(rendered_source, quote=True)
            escaped_href = html.escape(help_image.source_url, quote=True)
            image_pattern = re.compile(
                rf'(<img\b[^>]*\bsrc="{re.escape(escaped_source)}"[^>]*>)',
                re.IGNORECASE,
            )
            wrapped_help_html = image_pattern.sub(
                rf'<a href="{escaped_href}">\1</a>',
                wrapped_help_html,
            )

        return wrapped_help_html

    def cache_key(self, image_url: str) -> str:
        return f"help-images/{image_url}"

    def cancel_task_if_alive(
        self,
        task: Optional[QgsTask],
        *_args: object,
    ) -> None:
        if task is None or sip.isdeleted(task):
            return

        try:
            task.cancel()
        except RuntimeError:
            return

    def cleanup_help_image_directory(
        self,
        image_directory: Path,
        *_args: object,
    ) -> None:
        try:
            shutil.rmtree(image_directory)
        except OSError:
            return


class HelpAnchorClickPatch(AlgorithmDialogPatch):
    def __init__(
        self,
        browser_state: Optional[HelpBrowserState] = None,
    ) -> None:
        self._browser_state = browser_state or HelpBrowserState()

    def apply(
        self,
        dialog: AlgorithmDialog,
        algorithm: ToolboxAlgorithm,
    ) -> None:
        del algorithm

        help_browser = self._browser_state.browser(dialog)
        if help_browser is None:
            return

        if help_browser.property(HELP_ANCHOR_PATCHED_PROPERTY):
            return

        self._browser_state.set_cached_image_paths(help_browser, {})

        try:
            help_browser.anchorClicked.disconnect()
        except (RuntimeError, TypeError):
            pass

        help_browser.anchorClicked.connect(
            lambda url, current_browser=help_browser: self._open_anchor(
                current_browser,
                url,
            )
        )
        help_browser.setProperty(HELP_ANCHOR_PATCHED_PROPERTY, True)

    def _open_anchor(
        self,
        help_browser: QTextBrowser,
        url: QUrl,
    ) -> None:
        image_path = self._browser_state.cached_image_path(
            help_browser,
            url,
        )
        if image_path is not None:
            self._show_help_image_preview_dialog(image_path)
            return

        if url.isRelative() and not url.path() and url.hasFragment():
            help_browser.scrollToAnchor(url.fragment())
            return

        if not url.isValid():
            return

        QDesktopServices.openUrl(url)

    def _show_help_image_preview_dialog(self, image_path: str) -> None:
        image_file = Path(image_path)
        if not image_file.is_file():
            return

        if HelpImagePreviewDialog is None:
            return

        dialog = HelpImagePreviewDialog(
            str(image_file),
            parent=self._dialog_parent(),
        )
        dialog.exec()

    def _dialog_parent(self) -> Optional[QWidget]:
        try:
            plugin = NextgisToolboxInterface.instance()
        except ToolboxError:
            return None

        main_window = plugin.qgis_iface.mainWindow()
        if main_window is None or sip.isdeleted(main_window):
            return None

        return main_window


class HelpImagesPatch(AlgorithmDialogPatch):
    _MIME_TYPES = {
        "gif": "image/gif",
        "jpeg": "image/jpeg",
        "jpg": "image/jpeg",
        "png": "image/png",
        "svg": "image/svg+xml",
        "webp": "image/webp",
    }

    def __init__(
        self,
        browser_state: Optional[HelpBrowserState] = None,
        task_support: Optional[HelpImageTaskSupport] = None,
    ) -> None:
        self._browser_state = browser_state or HelpBrowserState()
        self._task_support = task_support or HelpImageTaskSupport()

    def apply(
        self,
        dialog: AlgorithmDialog,
        algorithm: ToolboxAlgorithm,
    ) -> None:
        help_browser = self._browser_state.browser(dialog)
        if help_browser is None:
            return

        self._browser_state.set_cached_image_paths(help_browser, {})

        help_content = algorithm.help_content(defer_images=True)
        if not help_content.images:
            return

        if help_browser.property(HELP_IMAGES_PATCHED_PROPERTY):
            return

        help_browser.setProperty(HELP_IMAGES_PATCHED_PROPERTY, True)
        help_browser.setHtml(algorithm.rendered_help_html(defer_images=True))

        image_directory = Path(mkdtemp(prefix="nextgis_toolbox_help_images_"))
        self._set_image_directory(dialog, image_directory)
        load_task = self._create_load_task(
            dialog,
            help_browser,
            algorithm,
            help_content.images,
            image_directory,
        )
        self._connect_dialog_cleanup(dialog, load_task, image_directory)
        self._start_load_task(load_task)

    def _set_image_directory(
        self,
        dialog: AlgorithmDialog,
        image_directory: Path,
    ) -> None:
        setattr(
            dialog,
            TOOLBOX_HELP_IMAGES_DIRECTORY_ATTRIBUTE,
            image_directory,
        )

    def _create_load_task(
        self,
        dialog: AlgorithmDialog,
        help_browser: QTextBrowser,
        algorithm: ToolboxAlgorithm,
        help_images: Tuple[ToolHelpImage, ...],
        image_directory: Path,
    ) -> "_LoadHelpImagesTask":
        load_task = _LoadHelpImagesTask(
            algorithm.api_client(),
            help_images,
            image_directory,
            partial(
                self._on_task_finished,
                dialog,
                help_browser,
                algorithm,
                help_images,
            ),
            task_support=self._task_support,
        )
        setattr(dialog, TOOLBOX_HELP_IMAGES_TASK_ATTRIBUTE, load_task)
        return load_task

    def _connect_dialog_cleanup(
        self,
        dialog: AlgorithmDialog,
        load_task: "_LoadHelpImagesTask",
        image_directory: Path,
    ) -> None:
        dialog.destroyed.connect(
            partial(self._task_support.cancel_task_if_alive, load_task)
        )
        dialog.destroyed.connect(
            partial(
                self._task_support.cleanup_help_image_directory,
                image_directory,
            )
        )

    def _start_load_task(self, load_task: "_LoadHelpImagesTask") -> None:
        task_manager = self._task_manager()
        if task_manager is None:
            return

        task_manager.addTask(load_task)

    def _task_manager(self) -> Optional[QgsTaskManager]:
        try:
            plugin = NextgisToolboxInterface.instance()
        except ToolboxError:
            return QgsApplication.taskManager()

        task_manager = getattr(plugin, "task_manager", None)
        if isinstance(task_manager, QgsTaskManager):
            return task_manager

        return QgsApplication.taskManager()

    def _on_task_finished(
        self,
        dialog: AlgorithmDialog,
        help_browser: QTextBrowser,
        algorithm: ToolboxAlgorithm,
        help_images: Tuple[ToolHelpImage, ...],
        task: "_LoadHelpImagesTask",
        result: bool,
    ) -> None:
        if sip.isdeleted(dialog):
            return

        self._clear_finished_task(dialog, task)
        if not self._can_apply_finished_task(
            dialog,
            help_browser,
            task,
            result,
        ):
            return

        image_sources, cached_image_paths = self._image_sources(
            help_browser,
            help_images,
            task.image_paths,
        )
        if not image_sources:
            return

        self._apply_loaded_images(
            help_browser,
            algorithm,
            help_images,
            image_sources,
            cached_image_paths,
        )

    def _clear_finished_task(
        self,
        dialog: AlgorithmDialog,
        task: "_LoadHelpImagesTask",
    ) -> None:
        if getattr(dialog, TOOLBOX_HELP_IMAGES_TASK_ATTRIBUTE, None) is task:
            setattr(dialog, TOOLBOX_HELP_IMAGES_TASK_ATTRIBUTE, None)

    def _can_apply_finished_task(
        self,
        dialog: AlgorithmDialog,
        help_browser: QTextBrowser,
        task: "_LoadHelpImagesTask",
        result: bool,
    ) -> bool:
        if not result or task.isCanceled():
            return False

        if sip.isdeleted(dialog) or sip.isdeleted(help_browser):
            return False

        return True

    def _apply_loaded_images(
        self,
        help_browser: QTextBrowser,
        algorithm: ToolboxAlgorithm,
        help_images: Tuple[ToolHelpImage, ...],
        image_sources: Dict[str, str],
        cached_image_paths: Dict[str, str],
    ) -> None:
        self._browser_state.set_cached_image_paths(
            help_browser,
            cached_image_paths,
        )
        help_browser.setHtml(
            self._task_support.wrap_help_image_links(
                algorithm.rendered_help_html(
                    image_sources,
                    defer_images=True,
                ),
                help_images,
                image_sources,
            )
        )

    def _image_sources(
        self,
        help_browser: QTextBrowser,
        help_images: Sequence[ToolHelpImage],
        image_paths: Dict[str, str],
    ) -> Tuple[Dict[str, str], Dict[str, str]]:
        max_width = self._image_width(help_browser)
        image_urls = {
            image.placeholder: image.source_url for image in help_images
        }
        resolved_sources: Dict[str, str] = {}
        cached_image_paths: Dict[str, str] = {}

        for placeholder, image_path in image_paths.items():
            image_url = image_urls.get(placeholder)
            if image_url is None:
                continue

            content = self._read_cached_image(image_path)
            if content is None:
                continue

            image_source = self._image_data_url(
                content,
                image_url,
                max_width,
            )
            if image_source is None:
                continue

            resolved_sources[placeholder] = image_source
            cached_image_paths[image_url] = image_path

        return resolved_sources, cached_image_paths

    def _read_cached_image(
        self,
        image_path: str,
    ) -> Optional[bytes]:
        path = Path(image_path)
        if not path.is_file():
            return None

        try:
            return path.read_bytes()
        except OSError as error:
            logger.debug(
                "Failed to read cached help image '%s': %s",
                image_path,
                error,
            )
            return None

    def _image_width(self, help_browser: QTextBrowser) -> int:
        viewport = help_browser.viewport()
        viewport_width = viewport.width() if viewport is not None else 0
        if viewport_width <= 0:
            viewport_width = help_browser.width()

        return max(viewport_width - 24, 64)

    def _image_data_url(
        self,
        content: bytes,
        image_url: str,
        max_width: int,
    ) -> Optional[str]:
        mime_type = self._mime_type(image_url)
        if mime_type is None:
            return None

        scaled_content, scaled_mime_type = self._scale_image(
            content,
            mime_type,
            max_width,
        )
        encoded_content = b64encode(scaled_content).decode("ascii")
        return f"data:{scaled_mime_type};base64,{encoded_content}"

    def _scale_image(
        self,
        content: bytes,
        mime_type: str,
        max_width: int,
    ) -> Tuple[bytes, str]:
        image = QImage()
        if not image.loadFromData(content):
            return content, mime_type

        if image.width() <= max_width:
            return content, mime_type

        scaled_image = image.scaledToWidth(
            max_width,
            Qt.TransformationMode.SmoothTransformation,
        )
        buffer_data = QByteArray()
        buffer = QBuffer(buffer_data)
        if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
            return content, mime_type

        if not scaled_image.save(buffer, b"PNG"):
            return content, mime_type

        return bytes(buffer_data.data()), "image/png"

    def _mime_type(self, image_url: str) -> Optional[str]:
        normalized_url = image_url.split("?", 1)[0].lower()
        url_parts = normalized_url.rsplit(".", 1)
        if len(url_parts) != 2:
            return None

        return self._MIME_TYPES.get(url_parts[1])


class _LoadHelpImagesTask(QgsTask):
    def __init__(
        self,
        api_client: "ToolboxApiClient",
        images: Sequence[ToolHelpImage],
        image_directory: Path,
        on_finished: Callable[["_LoadHelpImagesTask", bool], None],
        task_support: Optional[HelpImageTaskSupport] = None,
    ) -> None:
        super().__init__(
            "Load NextGIS Toolbox help images",
            QgsTask.Flag.CanCancel,
        )
        self._api_client = api_client
        self._images = list(images)
        self._image_directory = Path(image_directory)
        self._on_finished = on_finished
        self._task_support = task_support or HelpImageTaskSupport()
        self._image_paths: Dict[str, str] = {}

    @property
    def image_paths(self) -> Dict[str, str]:
        return self._image_paths

    def run(self) -> bool:
        total_images = max(len(self._images), 1)
        cached_by_url: Dict[str, str] = {}

        for index, image in enumerate(self._images, start=1):
            if self.isCanceled():
                return False

            self._load_image(image, cached_by_url)
            self._update_progress(index, total_images)

        return not self.isCanceled()

    def _load_image(
        self,
        image: ToolHelpImage,
        cached_by_url: Dict[str, str],
    ) -> None:
        image_path = self._load_image_path(image.source_url, cached_by_url)
        if image_path:
            self._image_paths[image.placeholder] = image_path

    def _load_image_path(
        self,
        image_url: str,
        cached_by_url: Dict[str, str],
    ) -> str:
        cached_image_path = cached_by_url.get(image_url)
        if cached_image_path is not None:
            return cached_image_path

        content = self._fetch_image_content(image_url)
        if content is None:
            return ""

        image_path = self._store_image_file(image_url, content)
        if image_path:
            cached_by_url[image_url] = image_path

        return image_path

    def _fetch_image_content(self, image_url: str) -> Optional[bytes]:
        cache_key = self._task_support.cache_key(image_url)
        try:
            return self._api_client.get_bytes(
                image_url,
                cache_key=cache_key,
            )
        except Exception as error:
            logger.debug(
                "Failed to load help image '%s': %s",
                image_url,
                error,
            )
            return None

    def _update_progress(self, index: int, total_images: int) -> None:
        self.setProgress(index * 100.0 / total_images)

    def finished(self, result: bool) -> None:
        self._on_finished(self, result)

    def _store_image_file(self, image_url: str, content: bytes) -> str:
        image_path = self._image_file_path(image_url)

        try:
            self._image_directory.mkdir(parents=True, exist_ok=True)
            image_path.write_bytes(content)
        except OSError as error:
            logger.debug(
                "Failed to store help image '%s': %s",
                image_url,
                error,
            )
            return ""

        return str(image_path)

    def _image_file_path(self, image_url: str) -> Path:
        suffix = Path(QUrl(image_url).path()).suffix.lower()
        if not suffix:
            suffix = ".img"

        image_name = sha256(image_url.encode("utf-8")).hexdigest()
        return self._image_directory / f"{image_name}{suffix}"
