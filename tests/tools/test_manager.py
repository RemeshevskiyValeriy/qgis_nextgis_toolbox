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

from unittest.mock import Mock

import pytest

from nextgis_toolbox.nextgis_toolbox.tools.models import (
    SortBy,
    ToolboxTag,
    ToolboxTool,
)
from nextgis_toolbox.nextgis_toolbox.tools.tools_manager import ToolsManager


def build_tool(
    tool_id: int,
    name: str,
    alias: str,
    tag_ids,
) -> ToolboxTool:
    return ToolboxTool(
        alias=alias,
        can_run=False,
        description=f"Description for {name}",
        id=tool_id,
        is_dev=False,
        is_featured=False,
        is_free=True,
        is_new=False,
        name=name,
        tag_ids=tag_ids,
    )


def test_tools_manager_builds_indexes_and_supports_lookups(qgis_app) -> None:
    del qgis_app

    alpha_tag = ToolboxTag(id=2, alias="Alpha", icon="", tool_ids=[])
    beta_tag = ToolboxTag(id=1, alias="Beta", icon="", tool_ids=[])
    zebra_tool = build_tool(20, "zebra", "Zebra", [1])
    alpha_tool = build_tool(10, "alpha", "Alpha", [1, 2])
    manager = ToolsManager(Mock())
    manager._tags_repository.fetch_tags = Mock(
        return_value=[beta_tag, alpha_tag]
    )
    manager._tools_repository.fetch_tools = Mock(
        return_value=[zebra_tool, alpha_tool]
    )

    manager.load()

    assert manager._tools_by_alias_sorted is None
    assert manager._tools_by_id is None
    assert manager._tools_by_id_sorted is None
    assert manager._tools_by_name is None
    assert manager._tools_by_tag_id is None
    assert manager._tags_by_id is None
    assert manager._tags_by_id_sorted is None

    assert [tag.alias for tag in manager.tags()] == ["Alpha", "Beta"]
    assert [tag.id for tag in manager.tags(sort_by=SortBy.ID)] == [
        1,
        2,
    ]
    assert manager._tags_by_id_sorted is not None
    assert [tool.name for tool in manager.tools()] == ["alpha", "zebra"]
    assert [tool.id for tool in manager.tools(sort_by=SortBy.ID)] == [
        10,
        20,
    ]
    assert [tool.alias for tool in manager.tools(sort_by=SortBy.ALIAS)] == [
        "Alpha",
        "Zebra",
    ]
    assert manager.tool(tool_id=10) is alpha_tool
    assert manager.tool(name="zebra") is zebra_tool
    assert manager.tag(2) is alpha_tag
    assert manager.find_tools(tool_id=20) == [zebra_tool]
    assert manager.find_tools(name=["alpha", "zebra"]) == [
        alpha_tool,
        zebra_tool,
    ]
    assert manager.find_tools(tag=alpha_tag) == [alpha_tool]
    assert manager.find_tools(tag=[1, alpha_tag]) == [alpha_tool, zebra_tool]
    assert alpha_tag.tool_ids == [10]
    assert beta_tag.tool_ids == [10, 20]
    assert manager._tools_by_alias_sorted is not None
    assert manager._tools_by_id is not None
    assert manager._tools_by_id_sorted is not None
    assert manager._tools_by_name is not None
    assert manager._tools_by_tag_id is not None
    assert manager._tags_by_id is not None


def test_tools_manager_validates_lookup_arguments(qgis_app) -> None:
    del qgis_app

    manager = ToolsManager(Mock())

    with pytest.raises(ValueError):
        manager.tool()

    with pytest.raises(ValueError):
        manager.tool(tool_id=1, name="alpha")

    with pytest.raises(ValueError):
        manager.find_tools()

    with pytest.raises(ValueError):
        manager.find_tools(tool_id=1, name="alpha")
