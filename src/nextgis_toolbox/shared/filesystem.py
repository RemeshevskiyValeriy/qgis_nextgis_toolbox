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

import subprocess
import sys
from pathlib import Path


def reveal_in_file_manager(file_path: Path) -> None:
    """Reveal the given file or directory in the system's file manager.

    :param file_path: The path to the file or directory to reveal.
    """
    path = file_path.resolve()

    if sys.platform.startswith("win"):
        _reveal_in_windows(path)
        return

    if sys.platform == "darwin":
        _reveal_in_macos(path)
        return

    _reveal_in_linux(path)


def _reveal_in_windows(path: Path) -> None:
    # Use Windows Explorer. '/select,' highlights the file in its folder.
    if path.is_dir():
        subprocess.Popen(["explorer", str(path)], close_fds=True)
        return

    subprocess.Popen(["explorer", "/select,", str(path)], close_fds=True)


def _reveal_in_macos(path: Path) -> None:
    # Use Finder. '-R' reveals the file.
    if path.is_dir():
        subprocess.Popen(["/usr/bin/open", str(path)], close_fds=True)
        return

    subprocess.Popen(["/usr/bin/open", "-R", str(path)], close_fds=True)


def _reveal_in_linux(path: Path) -> None:
    # TODO: dbus
    _open_base_directory_with_xdg(path)


def _open_base_directory_with_xdg(path: Path) -> None:
    directory = path if path.is_dir() else path.parent
    subprocess.Popen(["xdg-open", str(directory)], close_fds=True)
