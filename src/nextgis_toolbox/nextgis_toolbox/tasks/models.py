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
from typing import List, Optional


@dataclass
class ToolboxResult:
    """Descriptor of a single NextGIS Toolbox task result."""

    name: str
    result_type: str
    value: str


@dataclass
class ToolboxTask:
    """Descriptor of a NextGIS Toolbox task."""

    tool: str
    status: str
    progress: float
    error: Optional[str]
    results: List[ToolboxResult]
    operation: str
    state: str
