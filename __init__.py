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
    "blender": (3, 1, 0),
    "location": "Toolbar",
    "description": "Tool for selecting and marking up mesh object elements",
    "category": "Mesh",
    "support": 'COMMUNITY',
    "doc_url": "https://github.com/BlenderHQ/path-tool",
}

if "bpy" in locals():
    from importlib import reload

    reload(preferences)
    reload(_path_tool)

    del reload

import os

import bpy
from bpy.types import (
    WorkSpaceTool,
    Context,
    UILayout,
)

from . import preferences
from . import bhqab

from . import _path_tool


class PathToolMesh(WorkSpaceTool):
    bl_idname = "mesh.path_tool"
    bl_label = "Select Path"
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'
    bl_description = "Select items using editable pathes"
    bl_icon = os.path.join(os.path.dirname(__file__), "icons", "ops.mesh.path_tool")
    bl_keymap = ((_path_tool.MESH_OT_select_path.bl_idname, dict(type='LEFTMOUSE', value='PRESS',), None),)

    @staticmethod
    def draw_settings(_context: Context, layout: UILayout, tool: WorkSpaceTool):
        _path_tool.MESH_OT_select_path._ui_draw_func(
            tool.operator_properties(_path_tool.MESH_OT_select_path.bl_idname),
            layout,
        )


_classes = (
    preferences.Preferences,
    _path_tool.MESH_OT_select_path,
)

_cls_register, _cls_unregister = bpy.utils.register_classes_factory(classes=_classes)


def register():
    _cls_register()
    bpy.utils.register_tool(PathToolMesh, after={"builtin.select_lasso"}, separator=False, group=False)
    bhqab.gpu_extras.shader.generate_shaders(os.path.join(os.path.dirname(__file__), "shaders"))


def unregister():
    bpy.utils.unregister_tool(PathToolMesh)
    _cls_unregister()
