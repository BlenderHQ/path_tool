# Path Tool addon.
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

# ____________________________________________________________________________ #
# NOTE: Read README.md (markdown file) for details about installation and usage
# of the addon from UI/UX user-side. Other files contains only technical
# documentation and code comments.
# ____________________________________________________________________________ #

bl_info = {
    "name": "Path Tool",
    "author": "Vlad Kuzmin (ssh4), Ivan Perevala (ivpe)",
    # Maximal tested Blender version. Newer versions would not be stop any
    # registration process, because (as a rule), newer versions hold older Python
    # API for backward compatibility.
    "version": (3, 1, 0),
    # Minimal tested (and supported as well) Blender version. Blender Python API
    # before this value do not guaranteed that some functions works as expected,
    # because of found during development process bugs from Blender side, which was
    # fixed in later versions.
    "blender": (2, 83, 0),
    "location": "Toolbar",
    "description": "Tool for selecting and marking up mesh object elements",
    "category": "3D View",
    # NOTE: For compatibility reasons both keys should be kept.
    "wiki_url": "https://github.com/BlenderHQ/path-tool",
    "doc_url": "https://github.com/BlenderHQ/path-tool",
}

if "bpy" in locals():
    _unregister_cls()

    from importlib import reload

    reload(km)
    reload(tool)
    reload(shaders)
    reload(operators)
    reload(preferences)

    del reload

    _register_cls()
else:
    __is_partially_registered__ = False
    __is_completelly_registered__ = False

import bpy

from . import km
from . import tool
from . import shaders
from . import operators
from . import preferences


_classes = [
    preferences.PathToolPreferences,
    operators.MESH_OT_select_path,
]

_register_cls, _unregister_cls = bpy.utils.register_classes_factory(classes=_classes)


def register():
    global __is_partially_registered__
    global __is_completelly_registered__

    bver_older = preferences.tested_bver_older()
    bver_latest = preferences.tested_bver_latest()

    if bpy.app.version < bver_older:
        bpy.utils.register_class(preferences.PathToolPreferences)  # Register just for warning message.
        print(
            f"WARNING: Current Blender version ({bpy.app.version_string}) "
            f"is less than older tested ("
            f"{bver_older[0]}.{bver_older[1]}.{bver_older[2]}"
            f"). Registered only addon user "
            f"preferences, which warn user about that."
        )
        __is_partially_registered__ = True
        __is_completelly_registered__ = False
        return

    elif bpy.app.version > bver_latest:
        print(
            f"WARNING: Current Blender version ({bpy.app.version_string}) "
            f"is greater than latest tested ("
            f"{bver_latest[0]}.{bver_latest[1]}.{bver_latest[2]}"
            f")."
        )

    _register_cls()

    tool.register()
    km.register()

    __is_partially_registered__ = False
    __is_completelly_registered__ = True


def unregister():
    global __is_partially_registered__
    global __is_completelly_registered__

    if __is_completelly_registered__:
        km.unregister()
        tool.unregister()

        _unregister_cls()
    elif __is_partially_registered__:
        bpy.utils.unregister_class(preferences.PathToolPreferences)
