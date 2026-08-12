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

from qgis.core import Qgis

from nextgis_toolbox.notifier.cli_notifier import CliNotifier


def test_cli_notifier_writes_warning_to_stdout(qgis_app, capsys) -> None:
    del qgis_app

    notifier = CliNotifier()

    _ = notifier.display_message(
        "Missing authentication",
        level=Qgis.MessageLevel.Warning,
    )

    captured = capsys.readouterr()

    assert captured.out == "WARNING:\tMissing authentication\n"
    assert captured.err == ""


def test_cli_notifier_writes_error_to_stderr(qgis_app, capsys) -> None:
    del qgis_app

    notifier = CliNotifier()

    _ = notifier.display_exception(RuntimeError("boom"))

    captured = capsys.readouterr()

    assert captured.out == ""
    assert captured.err.startswith("ERROR:\t")
