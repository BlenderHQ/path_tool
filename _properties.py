from typing import Union

from bpy.types import (
    Context,
    PropertyGroup,
    UILayout,
    Menu,
    Operator,
)

from bpy.props import (
    BoolProperty,
    IntProperty,
    EnumProperty,
)
from bl_operators.presets import AddPresetBase

from . import __package__ as addon_pkg


class WindowManagerProperties(PropertyGroup):
    mark_select: EnumProperty(
        items=(
            ('EXTEND', "Extend", "Extend existing selection", 'SELECT_EXTEND', 1),
            ('NONE', "Do nothing", "Do nothing", 'X', 2),
            ('SUBTRACT', "Subtract", "Subtract existing selection", 'SELECT_SUBTRACT', 3),
            ('INVERT', "Invert", "Inverts existing selection", 'SELECT_DIFFERENCE', 4),
        ),
        default='EXTEND',
        options={'HIDDEN', 'SKIP_SAVE'},
        name="Select",
        description="Selection options",
    )

    mark_seam: EnumProperty(
        items=(
            ('MARK', "Mark", "Mark seam path elements", 'RESTRICT_SELECT_OFF', 1),
            ('NONE', "Do nothing", "Do nothing", 'X', 2),
            ('CLEAR', "Clear", "Clear seam path elements", 'RESTRICT_SELECT_ON', 3),
            ('TOGGLE', "Toggle", "Toggle seams on path elements", 'ACTION_TWEAK', 4),
        ),
        default='NONE',
        options={'HIDDEN', 'SKIP_SAVE'},
        name="Seams",
        description="Mark seam options",
    )

    mark_sharp: EnumProperty(
        items=(
            ('MARK', "Mark", "Mark sharp path elements", 'RESTRICT_SELECT_OFF', 1),
            ('NONE', "Do nothing", "Do nothing", 'X', 2),
            ('CLEAR', "Clear", "Clear sharp path elements", 'RESTRICT_SELECT_ON', 3),
            ('TOGGLE', "Toggle", "Toggle sharpness on path", 'ACTION_TWEAK', 4),
        ),
        default="NONE",
        options={'HIDDEN', 'SKIP_SAVE'},
        name="Sharp",
        description="Mark sharp options",
    )

    skip: IntProperty(
        min=0,
        soft_max=100,
        options={'HIDDEN', 'SKIP_SAVE'},
        name="Deselected",
        description="Number of deselected elements in the repetitive sequence",
    )

    nth: IntProperty(
        min=1,
        soft_max=100,
        default=1,
        options={'HIDDEN', 'SKIP_SAVE'},
        name="Selected",
        description="Number of selected elements in the repetitive sequence",
    )

    offset: IntProperty(
        soft_min=-100,
        soft_max=100,
        options={'HIDDEN', 'SKIP_SAVE'},
        name="Offset",
        description="Offset from the starting point",
    )

    use_topology_distance: BoolProperty(
        default=False,
        options={'HIDDEN', 'SKIP_SAVE'},
        name="Use Topology Distance",
        description=("Algorithm for calculating the shortest path for all subsequent created paths"
                     "(Select means find the minimum number of steps, ignoring spatial distance)"),
    )

    def ui_draw_func(self, layout: UILayout) -> None:
        row = layout.row(align=True)
        row.menu(MESH_MT_select_path_presets.__name__)
        row.operator(operator=MESH_OT_select_path_preset_add.bl_idname, text="", icon='ADD')
        row.operator(operator=MESH_OT_select_path_preset_add.bl_idname, text="", icon='REMOVE').remove_active = True

        layout.row().prop(self, "mark_select", text="Select", icon_only=True, expand=True)
        layout.row().prop(self, "mark_seam", text="Seam", icon_only=True, expand=True)
        layout.row().prop(self, "mark_sharp", text="Sharp", icon_only=True, expand=True)
        layout.prop(self, "skip")
        layout.prop(self, "nth")
        layout.prop(self, "offset")

    def ui_draw_func_runtime(self, layout: UILayout) -> None:
        row = layout.row(align=True)
        row.label(text="Tool Settings")

        row.operator("preferences.addon_show", icon='TOOL_SETTINGS', emboss=False).module = addon_pkg
        self.ui_draw_func(layout)
        layout.prop(self, "use_topology_distance")


class WM_OT_select_path_presets(Operator):
    bl_label = "Set Preset"
    bl_description = "Set operator properties to preset values"
    bl_idname = "wm.select_path_defaults"
    bl_options = {'INTERNAL'}

    preset: EnumProperty(
        items=(
            ('DEFAULTS', "", ""),
            ('TOPOLOGY_UV', "", ""),
            ('TOPOLOGY_SHARP', "", ""),
        ),
        default='DEFAULTS',
        options={'HIDDEN', 'SKIP_SAVE'},
    )

    def execute(self, context: Context):
        props = context.window_manager.select_path

        # if self.preset == 'DEFAULTS':
        props.mark_select = 'EXTEND'
        props.mark_seam = 'NONE'
        props.mark_sharp = 'NONE'
        props.use_topology_distance = False
        props.skip = 0
        props.nth = 0
        props.offset = 0

        if self.preset == 'TOPOLOGY_UV':
            props.mark_select = 'NONE'
            props.mark_seam = 'MARK'
            props.mark_sharp = 'NONE'
            props.use_topology_distance = True

        elif self.preset == 'TOPOLOGY_SHARP':
            props.mark_select = 'NONE'
            props.mark_seam = 'NONE'
            props.mark_sharp = 'MARK'
            props.skip = 0
            props.nth = 0
            props.offset = 0
            props.use_topology_distance = True

        return {'FINISHED'}


class MESH_MT_select_path_presets(Menu):
    bl_label = "Operator Presets"
    preset_subdir = "select_path"
    preset_operator = "script.execute_preset"

    def draw(self, context):
        addon_pref = context.preferences.addons[addon_pkg].preferences
        layout = self.layout
        layout.operator(WM_OT_select_path_presets.bl_idname, text="Restore Operator Defaults").preset = 'DEFAULTS'
        layout.separator()
        Menu.draw_preset(self, context)

        if addon_pref.default_presets:
            layout.separator()
            layout.operator(WM_OT_select_path_presets.bl_idname, text="Topology UV").preset = 'TOPOLOGY_UV'
            layout.operator(WM_OT_select_path_presets.bl_idname, text="Topology Sharp").preset = 'TOPOLOGY_SHARP'


class MESH_OT_select_path_preset_add(AddPresetBase, Operator):
    """Add \"Select Path\" preset"""
    bl_idname = "mesh.select_path_preset_add"
    bl_label = "Add Preset"
    preset_menu = MESH_MT_select_path_presets.__name__
    preset_defines = [
        "props = bpy.context.window_manager.select_path"
    ]

    preset_values = [
        "props.mark_select",
        "props.mark_seam",
        "props.mark_seam",
        "props.use_topology_distance",
    ]
    preset_subdir = "select_path"
