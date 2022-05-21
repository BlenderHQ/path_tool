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

    reload(_path_tool)

    del reload

import os

import bpy
from bpy.types import (
    WorkSpaceTool,
    Context,
    UILayout,
    AddonPreferences,
    WindowManager,
)
from bpy.props import (
    EnumProperty,
    FloatVectorProperty,
    IntProperty,
    PointerProperty,
)

from . import bhqab
from . import _path_tool
from . import _properties


class Preferences(AddonPreferences):
    bl_idname = __package__

    __slots__ = (
        "tab",
        "color_control_element",
        "color_active_path_control_element",
        "color_active_control_element",
        "color_path",
        "color_active_path",
        "point_size",
        "line_width",
    )

    tab: EnumProperty(
        items=(
            ('APPEARANCE', "Appearance", "Appearance settings"),
            ('KEYMAP', "Keymap", "Keymap settings"),
        ),
        default='APPEARANCE',
        options={'HIDDEN', 'SKIP_SAVE'},
        name="Tab",
        description="User preferences tab to be displayed",
    )

    color_control_element: FloatVectorProperty(
        default=(0.622574, 0.685957, 0.666101),
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        name="Control Element",
        description="Control element color",
    )

    color_active_path_control_element: FloatVectorProperty(
        default=(0.969922, 0.969922, 0.969922),
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        name="Active Path Control Element",
        description="Control element color",
    )

    color_active_control_element: FloatVectorProperty(
        default=(0.039087, 0.331906, 0.940392),
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        name="Active Control Element",
        description="Control element color",
    )

    color_path: FloatVectorProperty(
        default=(0.0, 0.7, 1.0),
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        name="Path",
        description="Path color",
    )

    color_path_topology: FloatVectorProperty(
        default=(0.0, 0.9, 0.5),
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        name="Topology Path",
        description="Color of path",
    )

    color_active_path: FloatVectorProperty(
        default=(1.0, 0.1, 0.1),
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        name="Active Path",
        description="Path color",
    )

    color_active_path_topology: FloatVectorProperty(
        default=(1.0, 0.8, 0.1),
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        name="Active Topology Path",
        description="Path color",
    )

    point_size: IntProperty(
        default=4,
        min=1,
        max=9,
        soft_min=3,
        soft_max=6,
        subtype='PIXEL',
        name="Vertex Size",
        description="",
    )

    line_width: IntProperty(
        default=3,
        min=1,
        max=9,
        soft_min=3,
        soft_max=6,
        subtype='PIXEL',
        name="Edge Width",
        description="",
    )

    def draw(self, context: Context) -> None:
        layout: UILayout = self.layout

        layout.use_property_split = True

        row = layout.row()
        row.prop_tabs_enum(self, "tab")

        if self.tab == 'APPEARANCE':
            col = layout.column(align=True)

            col.prop(self, "color_control_element")
            col.prop(self, "color_active_path_control_element")
            col.prop(self, "color_active_control_element")
            col.prop(self, "color_path")
            col.prop(self, "color_active_path")
            col.prop(self, "color_path_topology")
            col.prop(self, "color_active_path_topology")
            col.separator()
            col.prop(self, "point_size")
            col.prop(self, "line_width")

        elif self.tab == 'KEYMAP':
            bhqab.utils_ui.template_tool_keymap(context, layout, "3D View Tool: Edit Mesh, Select Path")


class PathToolMesh(WorkSpaceTool):
    bl_idname = "mesh.path_tool"
    bl_label = "Select Path"
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'
    bl_options = {}
    bl_description = "Select items using editable pathes"
    bl_icon = os.path.join(os.path.dirname(__file__), "icons", "ops.mesh.path_tool")
    bl_keymap = ((_path_tool.MESH_OT_select_path.bl_idname, dict(type='LEFTMOUSE', value='PRESS',), None),)

    @staticmethod
    def draw_settings(context: Context, layout: UILayout, tool: WorkSpaceTool):
        props: _properties.WindowManagerProperties = context.window_manager.select_path
        props.ui_draw_presets(layout)
        props.ui_draw_func(layout)
        layout.prop(props, "use_topology_distance")


_classes = (
    Preferences,

    _properties.WindowManagerProperties,
    _properties.WM_OT_select_path_presets,
    _properties.MESH_MT_select_path_presets,
    _properties.MESH_OT_select_path_preset_add,

    _path_tool.MESH_OT_select_path,
    _path_tool.MESH_PT_select_path_context,
)

_cls_register, _cls_unregister = bpy.utils.register_classes_factory(classes=_classes)


def register():
    _cls_register()
    WindowManager.select_path = PointerProperty(type=_properties.WindowManagerProperties)
    bpy.utils.register_tool(PathToolMesh, after={"builtin.select_lasso"}, separator=False, group=False)
    bhqab.gpu_extras.shader.generate_shaders(os.path.join(os.path.dirname(__file__), "shaders"))


def unregister():
    bpy.utils.unregister_tool(PathToolMesh)
    del WindowManager.select_path
    _cls_unregister()
