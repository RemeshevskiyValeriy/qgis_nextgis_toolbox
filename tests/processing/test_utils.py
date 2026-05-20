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

from nextgis_toolbox.nextgis_toolbox.tools.models import (
    ToolboxTag,
    ToolboxTool,
)
from nextgis_toolbox.processing.utils import format_tool_help


def test_format_tool_help_removes_seealso_div() -> None:
    tool = ToolboxTool(
        alias="tool",
        can_run=True,
        description="Description",
        help=(
            "<p>Summary</p>"
            '<div class="seealso">'
            "<p>Hidden block</p>"
            "</div>"
            "<p>Details</p>"
        ),
        id=1,
        is_dev=False,
        is_featured=False,
        is_free=True,
        is_new=False,
        name="Tool",
        tag_ids=[1],
        tags=[ToolboxTag(id=1, alias="Demo", icon="", tool_ids=[])],
    )

    help_string = format_tool_help(tool)

    assert '<div class="seealso">' not in help_string
    assert "Hidden block" not in help_string
    assert "<p>Summary</p><p>Details</p>" in help_string
    assert "<i><b>Tags:</b> Demo</i>" in help_string


def test_format_tool_help_removes_seealso_div_when_class_is_not_first() -> (
    None
):
    tool = ToolboxTool(
        alias="tool",
        can_run=True,
        description="Description",
        help=(
            "<p>Summary</p>"
            '<div class="admonition seealso extra">'
            "<p>Hidden block</p>"
            "</div>"
            "<p>Details</p>"
        ),
        id=1,
        is_dev=False,
        is_featured=False,
        is_free=True,
        is_new=False,
        name="Tool",
        tag_ids=[1],
        tags=[ToolboxTag(id=1, alias="Demo", icon="", tool_ids=[])],
    )

    help_string = format_tool_help(tool)

    assert 'class="admonition seealso extra"' not in help_string
    assert "Hidden block" not in help_string
    assert "<p>Summary</p><p>Details</p>" in help_string
