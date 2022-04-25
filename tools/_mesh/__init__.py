import os

import bpy

from . import _op_mesh


class PathToolMesh(bpy.types.WorkSpaceTool):
    bl_idname = "mesh.path_tool"
    bl_label = "Path Tool"
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'
    bl_description = (
        "Tool for selecting and marking up\n"
        "mesh object elements"
    )
    bl_icon = os.path.join(os.path.dirname(__file__), "ops.mesh.path_tool")
    bl_keymap = ((_op_mesh.MESH_OT_select_path.bl_idname, dict(type='LEFTMOUSE', value='PRESS',), None),)

    @staticmethod
    def draw_settings(context, layout, tool):
        _op_mesh.MESH_OT_select_path.draw_func(tool.operator_properties(_op_mesh.MESH_OT_select_path.bl_idname), layout)
