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

from nextgis_toolbox.nextgis_toolbox.sdk.client import ToolboxApiClient
from nextgis_toolbox.nextgis_toolbox.tools.api import ToolsApi
from nextgis_toolbox.nextgis_toolbox.tools.repository import (
    TagsRepository,
    ToolsRepository,
)
from nextgis_toolbox.settings.nextgis_toolbox_settings import (
    NextgisToolboxSettings,
)


def build_tool_summary(
    tool_id: int,
    name: str,
    *,
    alias: str,
    is_dev: bool = False,
) -> dict:
    return {
        "alias": alias,
        "can_run": False,
        "description": f"Description for {name}",
        "id": tool_id,
        "is_dev": is_dev,
        "is_featured": False,
        "is_free": True,
        "is_new": False,
        "name": name,
        "tags": [10],
    }


def build_tool_detail(tool_summary: dict) -> dict:
    return {
        **tool_summary,
        "inputs": [
            {
                "alias": "Source",
                "description": "Input file",
                "name": "source",
                "required": True,
                "type": "file",
            }
        ],
        "outputs": [
            {
                "alias": "Result",
                "description": "Output file",
                "name": "result",
                "required": True,
                "type": "file",
            }
        ],
    }


def test_tools_api_fetches_lists_and_detail(api_server) -> None:
    public_tool = build_tool_summary(1, "public-tool", alias="Public")
    api_server.add_json_response(
        "GET",
        "/api/tools/",
        {"data": [public_tool]},
    )
    api_server.add_json_response(
        "GET",
        "/api/tags/",
        {
            "data": [
                {
                    "alias": "General",
                    "icon": "",
                    "id": 10,
                    "tools": [1],
                }
            ]
        },
    )
    api_server.add_json_response(
        "GET",
        "/api/tools/public-tool",
        build_tool_detail(public_tool),
    )
    client = ToolboxApiClient(endpoint=api_server.base_url)
    api = ToolsApi(client)

    assert api.fetch_tools() == [public_tool]
    assert api.fetch_tags() == [
        {"alias": "General", "icon": "", "id": 10, "tools": [1]}
    ]
    assert api.fetch_tool("public-tool") == build_tool_detail(public_tool)


def test_tools_repository_keeps_public_tools_when_can_run_is_false(
    api_server,
) -> None:
    public_tool = build_tool_summary(1, "public-tool", alias="Public")
    api_server.add_json_response(
        "GET",
        "/api/tools/",
        {"data": [public_tool]},
    )
    api_server.add_json_response(
        "GET",
        "/api/tools/public-tool",
        build_tool_detail(public_tool),
    )
    settings = NextgisToolboxSettings()
    settings.is_developer_mode = False
    repository = ToolsRepository(
        ToolsApi(ToolboxApiClient(endpoint=api_server.base_url))
    )

    tools = repository.fetch_tools()

    assert len(tools) == 1
    assert tools[0].name == "public-tool"
    assert tools[0].can_run is False
    assert [parameter.name for parameter in tools[0].inputs] == ["source"]
    assert [parameter.name for parameter in tools[0].outputs] == ["result"]


def test_tools_repository_includes_dev_tools_in_developer_mode(
    api_server,
) -> None:
    public_tool = build_tool_summary(1, "public-tool", alias="Public")
    dev_tool = build_tool_summary(
        2,
        "developer-tool",
        alias="Developer",
        is_dev=True,
    )
    api_server.add_json_response(
        "GET",
        "/api/tools/",
        {"data": [public_tool, dev_tool]},
    )
    api_server.add_json_response(
        "GET",
        "/api/tools/public-tool",
        build_tool_detail(public_tool),
    )
    api_server.add_json_response(
        "GET",
        "/api/tools/developer-tool",
        build_tool_detail(dev_tool),
    )
    settings = NextgisToolboxSettings()
    settings.is_developer_mode = True
    repository = ToolsRepository(
        ToolsApi(ToolboxApiClient(endpoint=api_server.base_url))
    )

    tools = repository.fetch_tools()

    assert [tool.name for tool in tools] == [
        "public-tool",
        "developer-tool",
    ]


def test_tags_repository_returns_tag_models(api_server) -> None:
    api_server.add_json_response(
        "GET",
        "/api/tags/",
        {
            "data": [
                {
                    "alias": "General",
                    "icon": "",
                    "id": 10,
                    "tools": [1],
                }
            ]
        },
    )
    repository = TagsRepository(
        ToolsApi(ToolboxApiClient(endpoint=api_server.base_url))
    )

    tags = repository.fetch_tags()

    assert len(tags) == 1
    assert tags[0].id == 10
    assert tags[0].alias == "General"
    assert tags[0].tool_ids == [1]
