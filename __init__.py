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
    "version": (3, 3, 0),
    "blender": (3, 3, 0),
    "location": "Toolbar",
    "description": "Tool for selecting and marking up mesh object elements",
    "category": "Mesh",
    "support": 'COMMUNITY',
    "doc_url": "https://github.com/BlenderHQ/path-tool",
}

import os

import bpy
from bpy.types import (
    Context,
    UILayout,
    WindowManager,
    WorkSpaceTool,
)
from bpy.props import (
    PointerProperty,
)
from bpy.app.handlers import persistent


from . import pref
from . import main
from . import props

from .lib import bhqab


class PathToolMesh(WorkSpaceTool):
    bl_idname = "mesh.path_tool"
    bl_label = "Select Path"
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'
    bl_options = {}
    bl_description = "Select items using editable paths"
    bl_icon = os.path.join(os.path.dirname(__file__), "data", "ops.mesh.path_tool")
    bl_keymap = ((main.MESH_OT_select_path.bl_idname, dict(type='LEFTMOUSE', value='PRESS',), None),)

    @staticmethod
    def draw_settings(context: Context, layout: UILayout, tool: WorkSpaceTool):
        props: props.WindowManagerProperties = context.window_manager.select_path
        props.ui_draw_func_runtime(layout)


@persistent
def load_post(_unused):
    bhqab.utils_ui.copy_default_presets_from(
        src_root=os.path.join(os.path.dirname(__file__), "data", "presets")
    )


_classes = (
    pref.Preferences,
    pref.PREFERENCES_MT_path_tool_appearance_preset,
    pref.PREFERENCES_OT_path_tool_add_appearance,

    props.WindowManagerProperties,
    props.MESH_MT_select_path_presets,
    props.MESH_OT_select_path_preset_add,

    main.MESH_OT_select_path,
    main.MESH_PT_select_path_context,
)

_cls_register, _cls_unregister = bpy.utils.register_classes_factory(classes=_classes)

_handlers = (
    (bpy.app.handlers.load_post, load_post),
)


def register():
    _cls_register()
    WindowManager.select_path = PointerProperty(type=props.WindowManagerProperties)
    bpy.utils.register_tool(PathToolMesh, after={"builtin.select_lasso"}, separator=False, group=False)

    for handler, func in _handlers:
        if func not in handler:
            handler.append(func)


def unregister():
    for handler, func in _handlers:
        if func not in handler:
            handler.remove(func)

    bpy.utils.unregister_tool(PathToolMesh)
    del WindowManager.select_path
    _cls_unregister()
