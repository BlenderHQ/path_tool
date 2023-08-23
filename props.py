from __future__ import annotations

import os

from . import ADDON_PKG
from .lib import bhqab

import bpy
from bpy.types import (
    Context,
    Menu,
    Operator,
    OperatorProperties,
    PropertyGroup,
    UILayout,
)

from bpy.props import (
    BoolProperty,
    EnumProperty,
)
from bl_operators.presets import AddPresetBase
from bpy.app.translations import pgettext


class WMProps(PropertyGroup):
    is_runtime: BoolProperty(
        options={'HIDDEN'},
    )

    mark_select: EnumProperty(
        items=(
            ('EXTEND', "Extend", "Extend existing selection", 'SELECT_EXTEND', 1),
            ('NONE', "Do nothing", "Do nothing", 'X', 2),
            ('SUBTRACT', "Subtract", "Subtract existing selection", 'SELECT_SUBTRACT', 3),
            ('INVERT', "Invert", "Inverts existing selection", 'SELECT_DIFFERENCE', 4),
        ),
        default='EXTEND',
        options={'HIDDEN', 'SKIP_SAVE'},
        translation_context='WMProps',
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
        translation_context='WMProps',
        name="Seam",
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
        translation_context='WMProps',
        name="Sharp",
        description="Mark sharp options",
    )

    use_topology_distance: BoolProperty(
        default=False,
        options={'HIDDEN', 'SKIP_SAVE'},
        translation_context='WMProps',
        name="Use Topology Distance",
        description=(
            "Use the algorithm for determining the shortest path without taking into account the spatial distance, "
            "only the number of steps. Newly created paths will use the value of the option, but this can be adjusted "
            "individually for each of them"
        ),
    )

    def ui_draw_func(self, layout: UILayout) -> None:
        bhqab.utils_ui.template_preset(
            layout,
            menu=MESH_MT_select_path_presets,
            operator=MESH_OT_select_path_preset_add.bl_idname
        )

        # Такий метод відображення необхідний оскільки стандартний, який також використовується в круговому меню,
        # розтягує опції переліку в ширину.
        lay = layout
        if bpy.context.region.type in {'WINDOW', 'UI'}:
            lay = layout.column()

        def _intern_draw_enum_prop(identifier: str, text: str):
            row = lay.row()
            row.prop(self, identifier, text=text, icon_only=True, expand=True, text_ctxt='WMProps', translate=True)

        _intern_draw_enum_prop("mark_select", "Select")
        _intern_draw_enum_prop("mark_seam", "Seam")
        _intern_draw_enum_prop("mark_sharp", "Sharp")

    def ui_draw_func_runtime(self, layout: UILayout) -> None:
        row = layout.row(align=True)
        row.label(text="Tool Settings", text_ctxt='WMProps')

        row.operator("preferences.addon_show", icon='TOOL_SETTINGS', emboss=False, text_ctxt="PT").module = ADDON_PKG
        self.ui_draw_func(layout)
        layout.prop(self, "use_topology_distance")


class MESH_MT_select_path_presets(Menu):
    bl_label = "Operator Preset"
    preset_subdir = os.path.join("path_tool", "wm")
    preset_operator = "script.execute_preset"
    draw = Menu.draw_preset


class MESH_OT_select_path_preset_add(AddPresetBase, Operator):
    """Add \"Select Path\" preset"""
    bl_idname = "mesh.select_path_preset_add"
    bl_label = ""
    bl_translation_context = 'MESH_OT_select_path_preset_add'
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
    preset_subdir = os.path.join("path_tool", "wm")

    @classmethod
    def description(cls, _context: Context, properties: OperatorProperties) -> str:
        msgctxt = cls.__qualname__

        if properties.remove_active:
            return pgettext("Remove preset", msgctxt)
        else:
            return pgettext("Add preset", msgctxt)
