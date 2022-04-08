import os

import bpy

from . import operators


class PathToolMesh(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'

    bl_idname = "mesh.path_tool"
    bl_label = "Path Tool"
    bl_description = (
        "Tool for selecting and marking up\n"
        "mesh object elements"
    )
    bl_icon = os.path.join(os.path.dirname(__file__), "icons", "ops.mesh.path_tool")
    bl_widget = None
    bl_keymap = (
        (
            operators.MESH_OT_select_path.bl_idname, dict(
                type='LEFTMOUSE',
                value='PRESS',
            ), None
        ),
    )

    def draw_settings(context, layout, tool):
        layout.use_property_split = True

        props = tool.operator_properties(operators.MESH_OT_select_path.bl_idname)

        row = layout.row()
        row.prop(props, "mark_select", expand=True, icon_only=True, text="Select")
        row = layout.row()
        row.prop(props, "mark_seam", expand=True, icon_only=True, text="Seam")
        row = layout.row()
        row.prop(props, "mark_sharp", expand=True, icon_only=True, text="Sharp")


def register():
    bpy.utils.register_tool(PathToolMesh, after={"builtin.select_lasso"}, separator=False, group=False)


def unregister():
    bpy.utils.unregister_tool(PathToolMesh)
