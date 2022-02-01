import os

if "bpy" in locals():
    from importlib import reload

    reload(operators)

    del reload

import bpy
from bpy.utils.toolsystem import ToolDef
from bl_ui.space_toolsystem_common import ToolSelectPanelHelper

from . import operators


class _PathToolBase(object):
    def get_tool_list(space_type, context_mode):
        cls = ToolSelectPanelHelper._tool_class_from_space_type(space_type)
        return cls._tools[context_mode]

    @classmethod
    def reg_km(cls):
        from bl_keymap_utils.io import keyconfig_init_from_data

        wm = bpy.context.window_manager
        kc = wm.keyconfigs
        kc_default = kc.default
        kc_addon = kc.addon

        keyconfig_init_from_data(kc_default, cls.generate_empty_keymap())
        keyconfig_init_from_data(kc_addon, cls.generate_tool_keymap())

    @classmethod
    def unreg_km(cls):
        wm = bpy.context.window_manager

        blender_keyconfig_name = "blender"
        blender_addon_keyconfig_name = "blender addon"

        if bpy.app.version >= (2, 93, 0):
            blender_keyconfig_name = "Blender"
        blender_addon_keyconfig_name = "Blender addon"

        kc_default = wm.keyconfigs.get(blender_keyconfig_name)
        if kc_default:
            km_default = kc_default.keymaps
            for keyconfig_data in cls.generate_empty_keymap():
                km_name, km_args, _km_content = keyconfig_data
                km_default.remove(km_default.find(km_name, **km_args))

        kc_addon = wm.keyconfigs.get(blender_addon_keyconfig_name)
        if kc_addon:
            km_addon = kc_addon.keymaps
            for keyconfig_data in cls.generate_tool_keymap():
                km_name, km_args, _km_content = keyconfig_data
                km_addon.remove(km_addon.find(km_name, **km_args))


def draw_settings_path_tool_mesh(_context, layout, tool):
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


class PathToolMesh(_PathToolBase):
    km_path_tool_name = "3D View Tool: Edit Mesh, Path Tool"

    def generate_empty_keymap():
        return [
            (
                PathToolMesh.km_path_tool_name,
                {"space_type": 'VIEW_3D', "region_type": 'WINDOW'},
                {"items": []},
            ),
        ]

    def generate_tool_keymap():
        return [
            (
                PathToolMesh.km_path_tool_name,
                {"space_type": 'VIEW_3D', "region_type": 'WINDOW'},
                {
                    "items": [
                        (
                            operators.MESH_OT_select_path.bl_idname, {
                                "type": 'LEFTMOUSE', "value": 'PRESS'
                            }, None
                        ),
                    ]
                },
            ),
        ]

    _tool = ToolDef.from_dict(
        dict(
            idname="mesh.path_tool",
            label="Path Tool",
            description="Tool for selecting and marking up mesh object elements",
            operator=operators.MESH_OT_select_path.bl_idname,
            icon=os.path.join(os.path.dirname(__file__), "icons", "ops.mesh.path_tool"),
            keymap=km_path_tool_name,
            draw_settings=draw_settings_path_tool_mesh,
        )
    )

    @classmethod
    def reg(cls):
        # Register tool.
        tools = cls.get_tool_list('VIEW_3D', 'EDIT_MESH')

        for index, tool in enumerate(tools, 1):
            if isinstance(tool, ToolDef) and tool.label == "Cursor":
                break

        tools[:index] += None, cls._tool

        del tools

        # Register keymap.
        cls.reg_km()

    @classmethod
    def unreg(cls):
        # Unregister keymap.
        cls.unreg_km()

        # Unregister tool.
        tools = cls.get_tool_list('VIEW_3D', 'EDIT_MESH')

        index = tools.index(cls._tool) - 1  # None
        tools.pop(index)
        tools.remove(cls._tool)

        del tools
        del index


def register():
    PathToolMesh.reg()


def unregister():
    PathToolMesh.unreg()
