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

import importlib.util
import platform
from functools import lru_cache, wraps
from pathlib import Path
from types import TracebackType
from typing import Any, Callable, List, Optional, Type, TypeVar, Union

from qgis.core import (
    QgsApplication,
    QgsScopedRuntimeProfile,
    QgsSettings,
)
from qgis.PyQt.QtCore import QByteArray, QLocale, QMimeData
from qgis.PyQt.QtGui import QClipboard

from nextgis_toolbox.core.constants import (
    DEFAULT_TRANSLATION,
    PACKAGE_NAME,
    PLUGIN_NAME,
    UTM_TERM,
)
from nextgis_toolbox.core.exceptions import ToolboxError
from nextgis_toolbox.core.logging import logger


@lru_cache(maxsize=1)
def qgis_locale(*, adapt: bool = True) -> str:
    """Return the current locale code as a two-letter lowercase string.

    :returns: Two-letter lowercase locale code (e.g., "en", "fr").
    """
    override_locale = QgsSettings().value(
        "locale/overrideFlag", defaultValue=False, type=bool
    )
    if not override_locale:
        locale_full_name = QLocale.system().name()
    else:
        locale_full_name = QgsSettings().value("locale/userLocale", "")
    locale = locale_full_name[0:2].lower()

    if locale == "c":
        locale = "en"

    if adapt and locale not in supported_translations():
        if is_russian_speaking(locale):
            return "ru"

    return locale


@lru_cache(maxsize=1)
def plugin_path() -> Path:
    module_spec = importlib.util.find_spec(PACKAGE_NAME)
    if module_spec and module_spec.origin:
        return Path(module_spec.origin).parent
    return Path(__file__).parents[1]


@lru_cache(maxsize=1)
def real_plugin_path() -> Path:
    path = plugin_path() / "__init__.py"
    if path.is_symlink():
        path = path.resolve()
    return path.parent


@lru_cache(maxsize=1)
def nextgis_domain(subdomain: Optional[str] = None) -> str:
    """Construct the NextGIS domain URL based on the current locale.

    :param subdomain: Optional subdomain to prepend (e.g., "help").
    :returns: The full NextGIS domain URL (e.g., "https://nextgis.com").
    """
    speaks_russian = is_russian_speaking(qgis_locale())
    if subdomain is None:
        subdomain = ""
    elif not subdomain.endswith("."):
        subdomain += "."
    return f"https://{subdomain}nextgis.{'ru' if speaks_russian else 'com'}"


@lru_cache(maxsize=1)
def supported_translations() -> List[str]:
    """Return a list of supported locale codes.

    :returns: A list of supported locale codes (e.g., ["fr", "es"]).
    """
    i18n_path = plugin_path() / "i18n"
    supported = set([DEFAULT_TRANSLATION])
    for qm_file in i18n_path.glob("*.qm"):
        supported.add(qm_file.stem[-2:])

    return list(supported)


@lru_cache(maxsize=1)
def is_russian_speaking(locale: str) -> bool:
    """Determine if the current locale is Russian-speaking."""
    return locale in ("be", "kk", "ky", "ru", "uk")


def utm_tags(utm_medium: str, *, utm_campaign: str = "constant") -> str:
    """Generate a UTM tag string with customizable medium and campaign.

    :param utm_medium: UTM medium value.
    :param utm_campaign: UTM campaign value.

    :returns: UTM tag string.
    """
    return (
        f"utm_source=qgis_plugin&utm_medium={utm_medium}"
        f"&utm_campaign={utm_campaign}&utm_term={UTM_TERM}"
        f"&utm_content={qgis_locale()}"
    )


def set_clipboard_data(
    mime_type: str, data: Union[QByteArray, bytes, bytearray], text: str
) -> None:
    """Set data to the system clipboard.

    :param mime_type: The MIME type of the data being set to the clipboard.
    :param data: The data to set to the clipboard, as a QByteArray or bytes-like object.
    :param text: Optional text to set to the clipboard alongside the data.
    """
    mime_data = QMimeData()
    mime_data.setData(mime_type, data)
    if len(text) > 0:
        mime_data.setText(text)

    clipboard = QgsApplication.clipboard()
    clipboard = assert_not_none(clipboard)
    if platform.system() == "Linux":
        selection_mode = QClipboard.Mode.Selection
        clipboard.setMimeData(mime_data, selection_mode)
    clipboard.setMimeData(mime_data, QClipboard.Mode.Clipboard)


ValueType = TypeVar("ValueType")


def plugin_assert(condition: bool, message: Optional[str] = None) -> None:
    """Assert a condition and raise an AssertionError with the provided message if the condition is False.

    :param condition: The condition to assert.
    :param message: The error message to include in the exception if the assertion fails.

    :raises NextgisToolboxError: If the condition is False.
    """
    if condition:
        return

    if message is None:
        raise ToolboxError()

    raise ToolboxError(message)


def assert_not_none(
    value: Optional[ValueType],
    message: Optional[str] = None,
) -> ValueType:
    """Return a non-optional value or raise ToolboxError."""
    if value is not None:
        return value

    if message is None:
        raise ToolboxError()

    raise ToolboxError(message)


ReturnType = TypeVar("ReturnType")


class PluginRuntimeProfiler:
    """Context manager used to profile blocks"""

    _operations_count: int = 0

    def __init__(self, operation_name: str, icon: str = "⏲") -> None:
        self._operation_name = operation_name
        self._operation_name_with_number = None
        self._icon = icon
        self._profiler: Optional[QgsScopedRuntimeProfile] = None

    def __del__(self) -> None:
        self.stop()

    def start(self) -> str:
        """Run the context manager and return the operation name."""
        type(self)._operations_count += 1
        self._operation_name_with_number = (
            f"{type(self)._operations_count:03d}. {self._operation_name}"
        )

        logger.debug(f"{self._icon} Start {self._operation_name}")
        self._profiler = QgsScopedRuntimeProfile(
            self._operation_name_with_number, PLUGIN_NAME
        )
        return self._operation_name_with_number

    def stop(self) -> None:
        """Stop the profiler."""
        if not self._profiler:
            return

        del self._profiler
        self._profiler = None

        logger.debug(
            f"→ Completed {self._operation_name} (elapsed time: "
            f"{self.profile_time()} seconds)"
        )

    def profile_time(self) -> float:
        """Return the elapsed time of the profiled operation."""
        profiler = QgsApplication.instance().profiler()
        return profiler.profileTime(
            self._operation_name_with_number, PLUGIN_NAME
        )

    @classmethod
    def download(cls, operation_name: str) -> "PluginRuntimeProfiler":
        """Create a profiler instance for download operations with a specific icon."""
        return cls(operation_name, icon="↓")

    @classmethod
    def wrap(
        cls,
        operation_name: Optional[str] = None,
        *,
        icon: str = "⏲",
        format_args: Optional[Callable[..., str]] = None,
    ) -> Callable[
        [Callable[..., ReturnType]],
        Callable[..., ReturnType],
    ]:
        """Decorate a callable with runtime profiling."""

        def decorator(
            function: Callable[..., ReturnType],
        ) -> Callable[..., ReturnType]:

            @wraps(function)
            def wrapper(*args: Any, **kwargs: Any) -> ReturnType:
                profiler_name = operation_name or function.__qualname__
                if format_args:
                    profiler_name = profiler_name.format(
                        format_args(*args[1:], **kwargs)
                    )

                with cls(profiler_name, icon):
                    return function(*args, **kwargs)

            return wrapper

        return decorator

    @staticmethod
    def reset() -> None:
        """Reset profiling messages for the plugin."""
        profiler = QgsApplication.instance().profiler()
        if PLUGIN_NAME not in profiler.groups():
            return

        logger.debug("Reset profiling messages")
        profiler.clear(PLUGIN_NAME)

    def __enter__(self) -> str:
        return self.start()

    def __exit__(
        self,
        error_type: Optional[Type[BaseException]],
        error: Optional[BaseException],
        error_traceback: Optional[TracebackType],
    ) -> bool:
        """Exit the context manager, stopping the profiler and handling any exceptions.

        :param error_type: Exception type if raised, otherwise None.
        :param error: Exception instance if raised, otherwise None.
        :param error_traceback: Traceback object if exception raised, otherwise None.
        :return: Always return False to propagate exceptions.
        """
        self.stop()
        return False
