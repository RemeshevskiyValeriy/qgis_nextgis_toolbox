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

from dataclasses import dataclass
from typing import List


@dataclass
class ToolboxTag:
    """
    Descriptor of a NextGIS Toolbox tag (category).
    """

    id: int
    alias: str
    icon: str
    tool_ids: List[int]


@dataclass
class ToolboxTool:
    """
    Descriptor of a NextGIS Toolbox tool.
    """

    id: int
    name: str
    alias: str
    description: str
    is_dev: bool
    is_free: bool
    is_new: bool
    is_featured: bool
    can_run: bool
    tag_ids: List[int]
