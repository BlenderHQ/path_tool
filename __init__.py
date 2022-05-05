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

bl_info = {
    "name": "Path Tool",
    "author": "Vlad Kuzmin (ssh4), Ivan Perevala (ivpe)",
    "version": (3, 0, 0),
    "blender": (3, 0, 0),
    "location": "Toolbar",
    "description": "Tool for selecting and marking up mesh object elements",
    "category": "Mesh",
    "support": 'COMMUNITY',
    "doc_url": "https://github.com/BlenderHQ/path-tool",
}

if "bpy" in locals():
    from importlib import reload

    reload(tools)
    reload(preferences)

    del reload

import os

import bpy

from . import tools
from . import preferences
from . import bhqab

_classes = (
    preferences.Preferences,
    tools.MESH_OT_select_path,
)

_cls_register, _cls_unregister = bpy.utils.register_classes_factory(classes=_classes)


def register():
    _cls_register()
    bpy.utils.register_tool(tools.PathToolMesh, after={"builtin.select_lasso"}, separator=False, group=False)
    bhqab.gpu_extras.shader.generate_shaders(os.path.join(os.path.dirname(__file__), "shaders"))


def unregister():
    bpy.utils.unregister_tool(tools.PathToolMesh)
    _cls_unregister()
