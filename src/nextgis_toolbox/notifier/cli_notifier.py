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
import sys
import uuid
from typing import Optional, TextIO, Tuple

from qgis.core import Qgis
from qgis.PyQt.QtCore import QObject

from nextgis_toolbox.core.exceptions import (
    ToolboxError,
    ToolboxWarning,
)
from nextgis_toolbox.core.logging import logger
from nextgis_toolbox.notifier.notifier_interface import NotifierInterface


class CliNotifier(NotifierInterface):
    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

    def display_message(
        self,
        message: str,
        *,
        header: Optional[str] = None,
        level: Qgis.MessageLevel = Qgis.MessageLevel.Info,
        **kwargs,  # noqa: ANN003, ARG002
    ) -> str:

        message_id = str(uuid.uuid4())
        stream, prefix = self._stream_for_level(level)
        plain_message = self._format_message(message, header=header)
        logger.log(level, plain_message)
        print(f"{prefix}{plain_message}", file=stream, flush=True)
        return message_id

    def display_exception(self, error: Exception) -> str:
        if not isinstance(error, (ToolboxError, ToolboxWarning)):
            old_error = error
            error = (
                ToolboxError()
                if not isinstance(error, Warning)
                else ToolboxWarning()
            )
            error.__cause__ = old_error
            del old_error

        level = (
            Qgis.MessageLevel.Warning
            if isinstance(error, Warning)
            else Qgis.MessageLevel.Critical
        )
        return self.display_message(error.user_message, level=level)

    def _format_message(
        self,
        message: str,
        *,
        header: Optional[str] = None,
    ) -> str:
        plain_message = self._strip_html(message)
        if header:
            return f"{self._strip_html(header)}: {plain_message}"

        return plain_message

    def _stream_for_level(
        self,
        level: Qgis.MessageLevel,
    ) -> Tuple[TextIO, str]:
        if level == Qgis.MessageLevel.Critical:
            return sys.stderr, "ERROR:\t"

        if level == Qgis.MessageLevel.Warning:
            return sys.stdout, "WARNING:\t"

        return sys.stdout, ""

    def _strip_html(self, message: str) -> str:
        normalized_message = html.unescape(message)
        normalized_message = re.sub(r"<[^>]+>", "", normalized_message)
        normalized_message = re.sub(r"\s+", " ", normalized_message)
        return normalized_message.strip()
