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

from base64 import b64decode

import nextgis_toolbox.api.cache_manager as cache_manager_module
from nextgis_toolbox.api.client import ToolboxApiClient
from nextgis_toolbox.processing.tool_content_formatter import (
    ToolContentFormatter,
)
from nextgis_toolbox.tools.models import (
    ToolboxTag,
    ToolboxTool,
)


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

    help_string = ToolContentFormatter().format_help(tool)

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

    help_string = ToolContentFormatter().format_help(tool)

    assert 'class="admonition seealso extra"' not in help_string
    assert "Hidden block" not in help_string
    assert "<p>Summary</p><p>Details</p>" in help_string


def test_format_tool_help_rewrites_relative_urls() -> None:
    tool = ToolboxTool(
        alias="tool",
        can_run=True,
        description="Description",
        help=(
            '<img src="/tooldocs/en/panotag/input.bd5b9452.png">'
            '<a href="guide.html">Guide</a>'
            '<a href="#section">Anchor</a>'
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

    help_string = ToolContentFormatter(
        "https://docs.nextgis.com/docs_toolbox/source/tool.html"
    ).format_help(tool)

    assert (
        'src="https://docs.nextgis.com/tooldocs/en/panotag/input.bd5b9452.png"'
        in help_string
    )
    assert (
        'href="https://docs.nextgis.com/docs_toolbox/source/guide.html"'
        in help_string
    )
    assert 'href="#section"' in help_string


def test_tool_content_formatter_normalizes_html5_and_sphinx_markup() -> None:
    tool = ToolboxTool(
        alias="tool",
        can_run=True,
        description="Description",
        help=(
            "<section>"
            "<p><strong>Try the tool in action</strong></p>"
            '<figure class="align-center" id="panotag-input-pic">'
            '<a class="reference internal image-reference" href="images/input.png">'
            '<img alt="_images/panotag_input.png" src="images/input.png" '
            'style="width: 20cm;">'
            "</a>"
            "<figcaption>"
            "<p>"
            '<span class="caption-text">Untagged image</span>'
            '<a class="headerlink" href="#panotag-input-pic" '
            'title="Link to this image">¶</a>'
            "</p>"
            "</figcaption>"
            "</figure>"
            "</section>"
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

    help_string = ToolContentFormatter(
        "https://docs.nextgis.com/docs_toolbox/source/tool.html"
    ).format_help(tool)

    assert "<section>" not in help_string
    assert "<figure" not in help_string
    assert "<figcaption>" not in help_string
    assert "<strong>" not in help_string
    assert 'class="headerlink"' not in help_string
    assert "¶" not in help_string
    assert "<b>Try the tool in action</b>" in help_string
    assert "Untagged image" in help_string
    assert "<center><div><i><p>" in help_string
    assert (
        'href="https://docs.nextgis.com/docs_toolbox/source/images/input.png"'
        in help_string
    )
    assert (
        'src="https://docs.nextgis.com/docs_toolbox/source/images/input.png"'
        in help_string
    )


def test_tool_content_formatter_preserves_align_center_when_tag_removed() -> (
    None
):
    tool = ToolboxTool(
        alias="tool",
        can_run=True,
        description="Description",
        help=(
            '<aside class="align-center"><span>Centered content</span></aside>'
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

    help_string = ToolContentFormatter().format_help(tool)

    assert "<aside" not in help_string
    assert "<center>" in help_string
    assert "</center>" in help_string
    assert "Centered content" in help_string


def test_tool_content_formatter_reduces_list_indent() -> None:
    tool = ToolboxTool(
        alias="tool",
        can_run=True,
        description="Description",
        help="<ul><li>Item</li></ul>",
        id=1,
        is_dev=False,
        is_featured=False,
        is_free=True,
        is_new=False,
        name="Tool",
        tag_ids=[1],
        tags=[ToolboxTag(id=1, alias="Demo", icon="", tool_ids=[])],
    )

    help_string = ToolContentFormatter().format_help(tool)

    assert '<ul style="margin-left:4px; padding-left:0px;">' in help_string
    assert (
        '<li style="margin-left:0px; padding-left:8px;">&nbsp;Item</li>'
        in help_string
    )


def test_tool_content_formatter_normalizes_description_markup() -> None:
    tool = ToolboxTool(
        alias="tool",
        can_run=True,
        description="<section><strong>Description</strong></section>",
        help=None,
        id=1,
        is_dev=False,
        is_featured=False,
        is_free=True,
        is_new=False,
        name="Tool",
        tag_ids=[1],
        tags=[ToolboxTag(id=1, alias="Demo", icon="", tool_ids=[])],
    )

    description = ToolContentFormatter().format_description(tool)

    assert "<section>" not in description
    assert "<strong>" not in description
    assert "<b>Description</b>" in description
    assert description.endswith("<i>Tags: Demo</i>")


def test_tool_content_formatter_reuses_persistent_image_cache(
    api_server,
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(
        cache_manager_module.QStandardPaths,
        "writableLocation",
        lambda *_args, **_kwargs: str(tmp_path),
    )
    image_url = api_server.url("/images/demo.png")
    image_content = b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jxPsAAAAASUVORK5CYII="
    )
    api_server.add_response(
        "GET",
        "/images/demo.png",
        image_content,
        headers={"Content-Type": "image/png"},
    )

    client = ToolboxApiClient(endpoint=api_server.base_url)
    first_formatter = ToolContentFormatter(
        api_client=client,
    )
    second_formatter = ToolContentFormatter(
        api_client=client,
    )

    first_data_url = first_formatter.embed_image(image_url)
    second_data_url = second_formatter.embed_image(image_url)

    assert first_data_url.startswith("data:image/png;base64,")
    assert second_data_url == first_data_url
    assert [request.path for request in api_server.requests] == [
        "/images/demo.png"
    ]


def test_prepare_tool_help_defers_image_loading(api_server) -> None:
    tool = ToolboxTool(
        alias="tool",
        can_run=True,
        description="Description",
        help='<img src="/images/demo.png">',
        id=1,
        is_dev=False,
        is_featured=False,
        is_free=True,
        is_new=False,
        name="Tool",
        tag_ids=[],
    )
    client = ToolboxApiClient(endpoint=api_server.base_url)

    help_content = ToolContentFormatter(
        api_server.url("/docs/tool.html"),
        api_client=client,
    ).prepare_help(
        tool,
        defer_images=True,
        embed_images=False,
    )

    assert len(help_content.images) == 1
    assert help_content.images[0].source_url == api_server.url(
        "/images/demo.png"
    )
    assert (
        ":images/themes/default/downloading_svg.svg" in help_content.render()
    )
    assert api_server.requests == []
