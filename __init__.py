# Path Tool addon (Blender 2.91 +)
# Copyright (C) 2020  Vlad Kuzmin (ssh4), Ivan Perevala (ivpe)

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

bl_info = {
    "name": "Path Tool",
    "author": "Vlad Kuzmin (ssh4), Ivan Perevala (ivpe)",
    "version": (1, 2, 0),
    "blender": (2, 91, 0),
    "location": "Toolbar",
    "description": "Tool for selecting and marking up mesh object elements",
    "category": "3D View",
    "doc_url": "https://github.com/BlenderHQ/path-tool"
}

if "bpy" in locals():
    import importlib

    _unregister_cls()

    if "km" in locals():
        importlib.reload(km)
    if "tool" in locals():
        importlib.reload(tool)
    if "shaders" in locals():
        importlib.reload(shaders)
    if "operators" in locals():
        importlib.reload(operators)
    if "preferences" in locals():
        importlib.reload(preferences)

    _register_cls()

import bpy

from . import km
from . import tool
from . import shaders
from . import operators
from . import preferences


def _check_blender_version() -> bool:
    for i, cv in enumerate(bpy.app.version):
        if cv < bl_info["blender"][i]:
            return False
    return True


_classes = [
    preferences.PathToolPreferences,
    operators.MESH_OT_select_path,
]

_register_cls, _unregister_cls = bpy.utils.register_classes_factory(
    classes=_classes)


def register():
    if _check_blender_version():
        _register_cls()

        tool.register()
        km.register()
    else:
        rbver = bl_info["blender"]
        raise ImportError(
            f"Required Blender version at least {rbver[0]}.{rbver[1]}.{rbver[2]}")


def unregister():
    km.unregister()
    tool.unregister()

    _unregister_cls()
