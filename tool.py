# <pep8 compliant>

import os

from bpy.utils.toolsystem import ToolDef

from . import operators
from . import km

if "_rc" in locals():
    import importlib

    importlib.reload(operators)
    importlib.reload(km)

_rc = None


@ToolDef.from_fn
def path_tool():
    def draw_settings(context, layout, tool):
        layout.use_property_split = False

        props = tool.operator_properties(operators.MESH_OT_select_path.bl_idname)

        row = layout.row(align=True)
        row.label(text="Select")
        row.prop(props, "mark_select", expand=True, icon_only=True)
        row = layout.row(align=True)
        row.label(text="Seam")
        row.prop(props, "mark_seam", expand=True, icon_only=True)
        row = layout.row(align=True)
        row.label(text="Sharp")
        row.prop(props, "mark_sharp", expand=True, icon_only=True)

    icons_dir = os.path.join(os.path.dirname(__file__), "icons")
    icon_file = os.path.join(icons_dir, "ops.mesh.path_tool")

    if not os.path.isfile(icon_file + ".dat"):
        print("Missing tool icon file in addon directory\n(%s)" % icon_file)

    return dict(
        idname="mesh.path_tool",
        label="Path Tool",
        description="Tool for selecting and marking up mesh object elements (alpha)",
        operator=operators.MESH_OT_select_path.bl_idname,
        icon=icon_file,
        keymap=km.km_path_tool_name,
        draw_settings=draw_settings,
    )


def get_tool_list(space_type, context_mode):
    from bl_ui.space_toolsystem_common import ToolSelectPanelHelper

    cls = ToolSelectPanelHelper._tool_class_from_space_type(space_type)
    return cls._tools[context_mode]


def register():
    tools = get_tool_list('VIEW_3D', 'EDIT_MESH')

    for index, tool in enumerate(tools, 1):
        if isinstance(tool, ToolDef) and tool.label == "Cursor":
            break

    tools[:index] += None, path_tool

    del tools


def unregister():
    tools = get_tool_list('VIEW_3D', 'EDIT_MESH')

    index = tools.index(path_tool) - 1  # None
    tools.pop(index)
    tools.remove(path_tool)

    del tools
    del index
