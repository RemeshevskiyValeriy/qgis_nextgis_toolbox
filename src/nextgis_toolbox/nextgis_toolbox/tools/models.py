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

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ToolboxTag:
    """Descriptor of a NextGIS Toolbox tag."""

    id: int
    alias: str
    icon: str
    tools: List[int]


@dataclass
class ToolboxTool:
    """Descriptor of a NextGIS Toolbox tool."""

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


@dataclass
class ToolboxToolWithTags:
    """Descriptor of a Toolbox tool enriched with tag models."""

    tool: ToolboxTool
    tags: List[ToolboxTag]


@dataclass(frozen=True)
class ToolboxParameter:
    """Immutable descriptor of a Toolbox input or output parameter."""

    name: str
    parameter_type: str
    alias: Optional[str]
    description: Optional[str]
    required: bool
    choices: Optional[List[Dict[str, Any]]]
