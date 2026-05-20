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

import re
from typing import List, Union

from qgis.core import QgsApplication

from nextgis_toolbox.nextgis_toolbox.tools.models import ToolboxTool


def format_tool_description(tool: ToolboxTool) -> str:
    """Preprocess tool description for display in the Processing interface."""
    description = tool.description or ""
    description += "<br><br>" + _tags_string(tool, bold=False)
    return description


def format_tool_help(tool: ToolboxTool) -> str:
    """Preprocess tool help text for display in the Processing interface."""
    help_string = _tags_string(tool)
    if tool.help:
        help_string += "\n\n" + _strip_divs_by_class(
            tool.help or "", ["seealso", "admonition"]
        )

    return help_string


def _tags_string(tool: ToolboxTool, bold: bool = True) -> str:
    if not tool.tags:
        return ""

    title = QgsApplication.translate("NGToolboxProcessing", "Tags:")
    if bold:
        title = f"<b>{title}</b>"

    return f"<i>{title} " + ", ".join(tag.alias for tag in tool.tags) + "</i>"


def _strip_divs_by_class(
    help_string: str, html_classes: Union[str, List[str]]
) -> str:
    if isinstance(html_classes, str):
        html_classes = [html_classes]
    class_pattern = "|".join(re.escape(name) for name in html_classes)
    div_pattern = re.compile(
        rf"<div\b(?=[^>]*\bclass\s*=\s*(?:\"[^\"]*\b(?:{class_pattern})\b[^\"]*\"|'[^']*\b(?:{class_pattern})\b[^']*'))[^>]*>.*?</div>",
        re.IGNORECASE | re.DOTALL,
    )
    return div_pattern.sub("", help_string).strip()
