from qgis.core import QgsSettings
from qgis.PyQt.QtCore import QLocale

from nextgis_toolbox.core.constants import PACKAGE_NAME


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
