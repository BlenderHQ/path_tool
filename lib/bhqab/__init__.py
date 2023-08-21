# BlenderHQ addon base module.
# Copyright (C) 2022-2023 Vlad Kuzmin (ssh4), Ivan Perevala (ivpe)

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

__version__ = (3, 4)

__author__ = "Vlad Kuzmin (ssh4), Ivan Perevala (ivpe)"
__copyright__ = "Copyright (C) 2022  Vlad Kuzmin (ssh4), Ivan Perevala (ivpe)"
__maintainer__ = "Ivan Perevala (ivpe)"
__credits__ = ["Vlad Kuzmin (ssh4)", ]
__license__ = "GPLv3"

if "bpy" in locals():
    from importlib import reload

    reload(utils_gpu)
    reload(utils_ui)
    reload(utils_wm)
else:
    from . import utils_gpu
    from . import utils_ui
    from . import utils_wm

__all__ = (
    "utils_gpu",
    "utils_ui",
    "utils_wm",
)
