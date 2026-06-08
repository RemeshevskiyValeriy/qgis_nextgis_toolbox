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
from base64 import b64encode
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import urljoin, urlsplit

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QBuffer, QByteArray, QIODevice, Qt
from qgis.PyQt.QtGui import QImage

from nextgis_toolbox.api.client import ToolboxApiClient
from nextgis_toolbox.tools.models import ToolboxTool

HELP_IMAGE_LOADING_SOURCE = ":images/themes/default/downloading_svg.svg"


@dataclass(frozen=True)
class ToolHelpImage:
    placeholder: str
    source_url: str


@dataclass(frozen=True)
class FormattedToolHelp:
    html_template: str
    images: Tuple[ToolHelpImage, ...] = ()

    def render(
        self,
        image_sources: Optional[Mapping[str, str]] = None,
    ) -> str:
        rendered_html = self.html_template
        resolved_sources = image_sources or {}

        for image in self.images:
            image_source = resolved_sources.get(
                image.placeholder,
                HELP_IMAGE_LOADING_SOURCE,
            )
            rendered_html = rendered_html.replace(
                image.placeholder,
                image_source,
            )

        return rendered_html

    def render_dialog_html(
        self,
        title: str,
        image_sources: Optional[Mapping[str, str]] = None,
    ) -> str:
        rendered_help = self.render(image_sources)
        if not rendered_help:
            return ""

        paragraphs = rendered_help.split("\n")
        help_markup = "".join(
            f"<p>{paragraph}</p>" for paragraph in paragraphs
        )
        escaped_title = html.escape(title, quote=False)
        return f"<h2>{escaped_title}</h2>{help_markup}"


class ToolContentFormatter:
    _MAX_EMBEDDED_IMAGE_WIDTH = 256
    _TAG_REPLACEMENTS = {
        "article": "div",
        "em": "i",
        "figure": "div",
        "figcaption": "div",
        "main": "div",
        "section": "div",
        "strong": "b",
    }
    _SUPPORTED_TAGS = frozenset(
        {
            "a",
            "b",
            "blockquote",
            "br",
            "center",
            "code",
            "dd",
            "div",
            "dl",
            "dt",
            "font",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "hr",
            "i",
            "img",
            "li",
            "ol",
            "p",
            "pre",
            "span",
            "sub",
            "sup",
            "table",
            "tbody",
            "td",
            "th",
            "thead",
            "tr",
            "u",
            "ul",
        }
    )
    _VOID_TAGS = frozenset({"br", "hr", "img"})
    _DROP_TAGS = frozenset({"script", "style"})
    _DROP_CLASSES = frozenset({"admonition", "headerlink", "seealso"})
    _GLOBAL_ATTRIBUTES = frozenset({"style", "title"})
    _TAG_ATTRIBUTES = {
        "a": frozenset({"href", "name"}),
        "font": frozenset({"color", "face", "size"}),
        "img": frozenset({"alt", "height", "src", "width"}),
        "td": frozenset({"colspan", "rowspan", "width"}),
        "th": frozenset({"colspan", "rowspan", "width"}),
    }
    _MIME_TYPES = {
        "gif": "image/gif",
        "jpeg": "image/jpeg",
        "jpg": "image/jpeg",
        "png": "image/png",
        "svg": "image/svg+xml",
        "webp": "image/webp",
    }

    def __init__(
        self,
        toolbox_base_url: str = "",
        api_client: Optional[ToolboxApiClient] = None,
    ) -> None:
        self._toolbox_base_url = toolbox_base_url
        self._api_client = api_client or ToolboxApiClient(
            endpoint=toolbox_base_url
        )
        self._embedded_images: Dict[str, str] = {}

    def format_description(self, tool: ToolboxTool) -> str:
        description = self._sanitize_html(tool.description or "")
        tags_string = self._tags_string(tool, bold=False)

        if not description and not tags_string:
            return ""

        return description + "<br><br>" + tags_string

    def format_help(
        self,
        tool: ToolboxTool,
        *,
        embed_images: bool = True,
    ) -> str:
        return self.prepare_help(
            tool,
            embed_images=embed_images,
        ).render()

    def prepare_help(
        self,
        tool: ToolboxTool,
        *,
        defer_images: bool = False,
        embed_images: bool = False,
    ) -> FormattedToolHelp:
        help_string = self._tags_string(tool)
        deferred_images: List[ToolHelpImage] = []

        if tool.help:
            formatted_help = self._prepare_for_qgis_dialog(
                self._sanitize_html(
                    tool.help,
                    defer_images=defer_images,
                    embed_images=embed_images,
                    deferred_images=deferred_images,
                )
            )
            if help_string:
                help_string += "\n\n" + formatted_help
            else:
                help_string = formatted_help

        return FormattedToolHelp(
            html_template=help_string,
            images=tuple(deferred_images),
        )

    def _sanitize_html(
        self,
        value: str,
        *,
        defer_images: bool = False,
        embed_images: bool = False,
        deferred_images: Optional[List[ToolHelpImage]] = None,
    ) -> str:
        parser = _SupportedHtmlSanitizer(
            toolbox_base_url=self._toolbox_base_url,
            embedded_images=self._embedded_images,
            api_client=self._api_client,
            defer_images=defer_images,
            embed_images=embed_images,
            deferred_images=deferred_images,
        )
        parser.feed(value)
        parser.close()
        return parser.formatted_html().strip()

    def _prepare_for_qgis_dialog(self, value: str) -> str:
        list_block_pattern = re.compile(
            r"\s*(<(?:ul|ol)\b.*?</(?:ul|ol)>)\s*",
            re.IGNORECASE | re.DOTALL,
        )
        prepared_value = list_block_pattern.sub(
            r"\n</p>\1<p>\n",
            value,
        )
        prepared_value = re.sub(
            r"\n{3,}",
            "\n\n",
            prepared_value,
        )
        return prepared_value.strip()

    def embed_image(self, image_url: str) -> str:
        cached_image = self._embedded_images.get(image_url)
        if cached_image is not None:
            return cached_image

        mime_type = self._guess_mime_type(image_url)
        if mime_type is None:
            self._embedded_images[image_url] = image_url
            return image_url

        try:
            content = self._api_client.get_bytes(
                image_url,
                cache_key=self._image_cache_key(image_url),
            )
        except Exception:
            self._embedded_images[image_url] = image_url
            return image_url

        if not content:
            self._embedded_images[image_url] = image_url
            return image_url

        content, mime_type = self._scale_image_if_needed(content, mime_type)
        data_url = self._data_url(content, mime_type)
        self._embedded_images[image_url] = data_url
        return data_url

    def _data_url(self, content: bytes, mime_type: str) -> str:
        encoded_content = b64encode(content).decode("ascii")
        return f"data:{mime_type};base64,{encoded_content}"

    def _image_cache_key(self, image_url: str) -> str:
        return f"help-images/{image_url}"

    def _scale_image_if_needed(
        self,
        content: bytes,
        mime_type: str,
    ) -> Tuple[bytes, str]:
        image = QImage()
        if not image.loadFromData(content):
            return content, mime_type

        if image.width() <= self._MAX_EMBEDDED_IMAGE_WIDTH:
            return content, mime_type

        scaled_image = image.scaledToWidth(
            self._MAX_EMBEDDED_IMAGE_WIDTH,
            Qt.TransformationMode.SmoothTransformation,
        )

        buffer_data = QByteArray()
        buffer = QBuffer(buffer_data)
        if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
            return content, mime_type

        if not scaled_image.save(buffer, b"PNG"):
            return content, mime_type

        return bytes(buffer_data), "image/png"

    def _guess_mime_type(self, image_url: str) -> Optional[str]:
        normalized_url = image_url.split("?", 1)[0].lower()
        extension = normalized_url.rsplit(".", 1)
        if len(extension) != 2:
            return None

        return self._MIME_TYPES.get(extension[1])

    def _tags_string(self, tool: ToolboxTool, bold: bool = True) -> str:
        if not tool.tags:
            return ""

        title = QgsApplication.translate("NGToolboxProcessing", "Tags:")
        if bold:
            title = f"<b>{title}</b>"

        return (
            f"<i>{title} " + ", ".join(tag.alias for tag in tool.tags) + "</i>"
        )


class _SupportedHtmlSanitizer(HTMLParser):
    def __init__(
        self,
        toolbox_base_url: str,
        embedded_images: Dict[str, str],
        api_client: ToolboxApiClient,
        *,
        defer_images: bool = False,
        embed_images: bool = False,
        deferred_images: Optional[List[ToolHelpImage]] = None,
    ) -> None:
        super().__init__(convert_charrefs=True)
        self._toolbox_base_url = toolbox_base_url
        self._api_client = api_client
        self._embedded_images = embedded_images
        self._defer_images = defer_images
        self._embed_images = embed_images
        self._deferred_images = (
            deferred_images if deferred_images is not None else []
        )
        self._chunks: List[str] = []
        self._stack: List[Tuple[str, Optional[str], bool, Optional[str]]] = []
        self._skip_depth = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: Sequence[Tuple[str, Optional[str]]],
    ) -> None:
        self._handle_tag(tag, attrs, is_self_closing=False)

    def handle_startendtag(
        self,
        tag: str,
        attrs: Sequence[Tuple[str, Optional[str]]],
    ) -> None:
        self._handle_tag(tag, attrs, is_self_closing=True)

    def handle_endtag(self, tag: str) -> None:
        if not self._stack:
            return

        normalized_tag = tag.lower()

        while self._stack:
            opened_tag, closing_markup, skipped, _ = self._stack.pop()

            if skipped:
                self._skip_depth -= 1
            elif closing_markup is not None:
                self._chunks.append(closing_markup)

            if opened_tag == normalized_tag:
                return

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0 or not data:
            return

        self._chunks.append(html.escape(data, quote=False))

    def handle_comment(self, data: str) -> None:
        return

    def formatted_html(self) -> str:
        return "".join(self._chunks)

    def _handle_tag(
        self,
        tag: str,
        attrs: Sequence[Tuple[str, Optional[str]]],
        is_self_closing: bool,
    ) -> None:
        normalized_tag = tag.lower()

        if self._skip_depth > 0:
            if not is_self_closing:
                self._stack.append((normalized_tag, None, True, None))
                self._skip_depth += 1
            return

        attrs_dict = {
            name.lower(): value
            for name, value in attrs
            if name and value is not None
        }
        if self._should_drop_tag(normalized_tag, attrs_dict):
            if not is_self_closing:
                self._stack.append((normalized_tag, None, True, None))
                self._skip_depth += 1
            return

        rendered_tag = ToolContentFormatter._TAG_REPLACEMENTS.get(
            normalized_tag,
            normalized_tag,
        )
        should_render_tag = (
            rendered_tag in ToolContentFormatter._SUPPORTED_TAGS
        )

        if (
            should_render_tag
            and rendered_tag == "p"
            and self._is_inside_list_item()
        ):
            should_render_tag = False

        if not should_render_tag:
            if is_self_closing:
                return

            opening_markup, closing_markup = self._render_wrapped_content(
                normalized_tag,
                attrs,
            )
            if opening_markup:
                self._chunks.append(opening_markup)

            self._stack.append(
                (
                    normalized_tag,
                    closing_markup or None,
                    False,
                    None,
                )
            )
            return

        rendered_attrs = self._render_attributes(
            normalized_tag,
            rendered_tag,
            attrs,
        )
        center_opening, center_closing = self._render_center_wrappers(
            normalized_tag,
            attrs,
        )
        opening_markup = self._render_opening_tag(rendered_tag, rendered_attrs)
        closing_markup = f"</{rendered_tag}>"

        if normalized_tag == "figcaption":
            opening_markup += "<i>"
            closing_markup = "</i>" + closing_markup

        opening_markup = center_opening + opening_markup
        closing_markup += center_closing

        self._chunks.append(opening_markup)

        if rendered_tag == "li":
            self._chunks.append("&nbsp;")

        if is_self_closing or rendered_tag in ToolContentFormatter._VOID_TAGS:
            return

        self._stack.append(
            (normalized_tag, closing_markup, False, rendered_tag)
        )

    def _render_attributes(
        self,
        source_tag: str,
        tag: str,
        attrs: Sequence[Tuple[str, Optional[str]]],
    ) -> List[str]:
        allowed_attributes = set(ToolContentFormatter._GLOBAL_ATTRIBUTES)
        allowed_attributes.update(
            ToolContentFormatter._TAG_ATTRIBUTES.get(tag, ())
        )
        rendered_attrs: List[str] = []
        has_image_style = False
        class_names = self._extract_class_names(attrs)

        for attr_name, attr_value in attrs:
            if attr_name is None:
                continue

            normalized_name = attr_name.lower()
            if normalized_name not in allowed_attributes:
                continue

            if attr_value is None:
                continue

            if tag == "img" and normalized_name in {"width", "height"}:
                continue

            normalized_value = attr_value.strip()
            if not normalized_value:
                continue

            if normalized_name in {"href", "src"}:
                normalized_value = self._rewrite_relative_url(normalized_value)

            if tag == "img" and normalized_name == "src":
                normalized_value = self._resolve_image_source(normalized_value)

            if tag == "img" and normalized_name == "style":
                normalized_value = self._normalize_image_style(
                    normalized_value
                )
                has_image_style = True

            escaped_value = html.escape(normalized_value, quote=True)
            rendered_attrs.append(f'{normalized_name}="{escaped_value}"')

        if tag == "img" and not has_image_style:
            rendered_attrs.append(
                'style="display:block; width:100%; height:auto;"'
            )

        rendered_attrs = self._apply_special_styles(
            source_tag,
            tag,
            class_names,
            rendered_attrs,
        )

        return rendered_attrs

    def _render_opening_tag(self, tag: str, attrs: Iterable[str]) -> str:
        rendered_attrs = " ".join(attrs)
        if not rendered_attrs:
            return f"<{tag}>"

        return f"<{tag} {rendered_attrs}>"

    def _rewrite_relative_url(self, url: str) -> str:
        if not self._is_relative_url(url):
            return url

        return urljoin(self._toolbox_base_url, url)

    def _embed_image(self, image_url: str) -> str:
        cached_image = self._embedded_images.get(image_url)
        if cached_image is not None:
            return cached_image

        formatter = ToolContentFormatter(
            self._toolbox_base_url,
            api_client=self._api_client,
        )
        formatter._embedded_images = self._embedded_images
        return formatter.embed_image(image_url)

    def _resolve_image_source(self, image_url: str) -> str:
        if self._defer_images:
            placeholder = (
                f"__nextgis_toolbox_help_image_{len(self._deferred_images)}__"
            )
            self._deferred_images.append(
                ToolHelpImage(
                    placeholder=placeholder,
                    source_url=image_url,
                )
            )
            return placeholder

        if self._embed_images:
            return self._embed_image(image_url)

        return image_url

    def _normalize_image_style(self, style_value: str) -> str:
        declarations = []
        for declaration in style_value.split(";"):
            normalized_declaration = declaration.strip()
            if not normalized_declaration:
                continue

            property_name = normalized_declaration.split(":", 1)[0]
            if property_name.strip().lower() in {
                "display",
                "height",
                "max-width",
                "width",
            }:
                continue

            declarations.append(normalized_declaration)

        declarations.extend(
            [
                "display:block",
                "width:100%",
                "height:auto",
            ]
        )
        return "; ".join(declarations) + ";"

    def _apply_special_styles(
        self,
        source_tag: str,
        tag: str,
        class_names: List[str],
        rendered_attrs: List[str],
    ) -> List[str]:
        extra_declarations: List[str] = []

        if tag in {"ol", "ul"}:
            extra_declarations.extend(
                [
                    "margin-left:4px",
                    "padding-left:0px",
                ]
            )

        if tag == "li":
            extra_declarations.extend(
                [
                    "margin-left:0px",
                    "padding-left:8px",
                ]
            )

        if not extra_declarations:
            return rendered_attrs

        return self._merge_style_attributes(
            rendered_attrs,
            extra_declarations,
        )

    def _merge_style_attributes(
        self,
        rendered_attrs: List[str],
        extra_declarations: List[str],
    ) -> List[str]:
        merged_attrs: List[str] = []
        style_found = False

        for rendered_attr in rendered_attrs:
            if not rendered_attr.startswith("style="):
                merged_attrs.append(rendered_attr)
                continue

            style_found = True
            current_style = rendered_attr[len('style="') : -1]
            current_style = current_style.rstrip(";")
            merged_style = "; ".join(
                [
                    value
                    for value in [current_style, *extra_declarations]
                    if value
                ]
            )
            merged_attrs.append(f'style="{merged_style};"')

        if not style_found:
            merged_style = "; ".join(extra_declarations)
            merged_attrs.append(f'style="{merged_style};"')

        return merged_attrs

    def _extract_class_names(
        self,
        attrs: Sequence[Tuple[str, Optional[str]]],
    ) -> List[str]:
        for attr_name, attr_value in attrs:
            if attr_name is None or attr_value is None:
                continue

            if attr_name.lower() != "class":
                continue

            return [
                class_name.strip()
                for class_name in attr_value.split()
                if class_name.strip()
            ]

        return []

    def _render_wrapped_content(
        self,
        tag: str,
        attrs: Sequence[Tuple[str, Optional[str]]],
    ) -> Tuple[str, str]:
        opening_markup, closing_markup = self._render_center_wrappers(
            tag,
            attrs,
        )

        if tag == "figcaption":
            opening_markup += "<i>"
            closing_markup = "</i>" + closing_markup

        return opening_markup, closing_markup

    def _render_center_wrappers(
        self,
        tag: str,
        attrs: Sequence[Tuple[str, Optional[str]]],
    ) -> Tuple[str, str]:
        class_names = self._extract_class_names(attrs)
        if "align-center" not in class_names and tag != "figcaption":
            return "", ""

        return "<center>", "</center>"

    def _is_relative_url(self, url: str) -> bool:
        normalized_url = url.strip()
        if not normalized_url:
            return False

        if normalized_url.startswith(("#", "//")):
            return False

        return urlsplit(normalized_url).scheme == ""

    def _should_drop_tag(
        self,
        tag: str,
        attrs: Dict[str, str],
    ) -> bool:
        if tag in ToolContentFormatter._DROP_TAGS:
            return True

        classes = attrs.get("class", "")
        class_names = {
            class_name.strip()
            for class_name in classes.split()
            if class_name.strip()
        }
        if class_names.intersection(ToolContentFormatter._DROP_CLASSES):
            return True

        return False

    def _is_inside_list_item(self) -> bool:
        for _, _, skipped, rendered_tag in reversed(self._stack):
            if skipped:
                continue

            if rendered_tag == "li":
                return True

            if rendered_tag in {"ol", "ul"}:
                return False

        return False
