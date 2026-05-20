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

from functools import lru_cache
from typing import Optional

from qgis.core import QgsSettings
from qgis.PyQt.QtCore import QLocale

from nextgis_toolbox.core.constants import PACKAGE_NAME


@lru_cache(maxsize=1)
def qgis_locale() -> str:
    """Return the current locale code as a two-letter lowercase string.

    :returns: Two-letter lowercase locale code (e.g., "en", "fr").
    """
    override_locale = QgsSettings().value(
        "locale/overrideFlag", defaultValue=False, type=bool
    )
    if not override_locale:
        locale_full_name = QLocale.system().name()
    else:
        locale_full_name = QgsSettings().value("locale/userLocale", "")
    locale = locale_full_name[0:2].lower()

    return locale if locale.lower() != "c" else "en"


@lru_cache(maxsize=1)
def is_russian_speaking(locale: str) -> bool:
    """Determine if the current locale is Russian-speaking."""
    return locale in ["be", "kk", "ky", "ru", "uk"]


@lru_cache(maxsize=1)
def nextgis_domain(subdomain: Optional[str] = None) -> str:
    """Construct the NextGIS domain URL based on the current locale.

    :param subdomain: Optional subdomain to prepend (e.g., "help").
    :returns: The full NextGIS domain URL (e.g., "https://nextgis.com").
    """
    speaks_russian = is_russian_speaking(qgis_locale())
    if subdomain is None:
        subdomain = ""
    elif not subdomain.endswith("."):
        subdomain += "."
    return f"https://{subdomain}nextgis.{'ru' if speaks_russian else 'com'}"


def utm_tags(utm_medium: str, *, utm_campaign: str = "constant") -> str:
    """Generate a UTM tag string with customizable medium and campaign.

    :param utm_medium: UTM medium value.
    :param utm_campaign: UTM campaign value.

    :returns: UTM tag string.
    """
    return (
        f"utm_source=qgis_plugin&utm_medium={utm_medium}"
        f"&utm_campaign={utm_campaign}&utm_term={PACKAGE_NAME}"
        f"&utm_content={qgis_locale()}"
    )
