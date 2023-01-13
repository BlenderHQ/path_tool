from __future__ import annotations

import os

from bpy.types import (
    AddonPreferences,
    Context,
    Menu,
    Operator,
    UILayout,
)
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatVectorProperty,
    IntProperty,
)
from bl_operators.presets import AddPresetBase

from . import __package__ as addon_pkg
from .lib import bhqab

TOOL_KM_NAME = "3D View Tool: Edit Mesh, Select Path"
PREF_TEXTS = dict()


class Properties:

    tab: EnumProperty(
        items=(
            ('APPEARANCE', "Appearance", "Appearance settings"),
            ('BEHAVIOR', "Behavior", "Behavior settings"),
            ('KEYMAP', "Keymap", "Keymap settings"),
            ('INFO', "Info", "How to use the addon, relative links and licensing information"),
        ),
        default='APPEARANCE',
        options={'HIDDEN', 'SKIP_SAVE'},
        name="Tab",
        description="User preferences tab to be displayed",
    )

    info_tab: EnumProperty(
        items=(
            ('README', "How To Use the Addon", ""),
            ('LICENSE', "License", ""),
            ('LINKS', "Links", ""),
        ),
        default={'LINKS'},
        options={'ENUM_FLAG', 'HIDDEN', 'SKIP_SAVE'},
    )

    color_control_element: FloatVectorProperty(
        default=(0.8, 0.8, 0.8, 0.8),
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        options={'HIDDEN', 'SKIP_SAVE'},
        name="Control Element",
        description="Control element color",
    )

    color_active_control_element: FloatVectorProperty(
        default=(0.039087, 0.331906, 0.940392, 0.8),
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        options={'HIDDEN', 'SKIP_SAVE'},
        name="Active Control Element",
        description="Color of active control element",
    )

    color_path: FloatVectorProperty(
        default=(0.593397, 0.708376, 0.634955, 0.8),
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        options={'HIDDEN', 'SKIP_SAVE'},
        name="Path",
        description="Regular path color",
    )

    color_path_topology: FloatVectorProperty(
        default=(1.0, 0.952328, 0.652213, 0.8),
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        options={'HIDDEN', 'SKIP_SAVE'},
        name="Topology Path",
        description="Color of paths which uses topology calculation method",
    )

    color_active_path: FloatVectorProperty(
        default=(0.304987, 0.708376, 0.450786, 0.8),
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        options={'HIDDEN', 'SKIP_SAVE'},
        name="Active Path",
        description="Active path color",
    )

    color_active_path_topology: FloatVectorProperty(
        default=(1.0, 0.883791, 0.152213, 0.8),
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        options={'HIDDEN', 'SKIP_SAVE'},
        name="Active Topology Path",
        description="Color of active path which uses topology calculation method",
    )

    point_size: IntProperty(
        default=3,
        min=0,
        max=50,
        soft_max=20,
        subtype='FACTOR',
        options={'HIDDEN', 'SKIP_SAVE'},
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
        options={'HIDDEN', 'SKIP_SAVE'},
        name="Edge Width",
        description="",
    )

    aa_method: bhqab.utils_gpu.draw_framework.DrawFramework.prop_aa_method
    fxaa_preset: bhqab.utils_gpu.draw_framework.FXAA.prop_preset
    fxaa_value: bhqab.utils_gpu.draw_framework.FXAA.prop_value
    smaa_preset: bhqab.utils_gpu.draw_framework.SMAA.prop_preset

    auto_tweak_options: BoolProperty(
        default=False,
        name="Auto Tweak Options",
        options={'HIDDEN', 'SKIP_SAVE'},
        description=(
            "Adjust operator options. If no mesh element is initially selected, the selection option will be changed "
            "to \"Extend\". If all elements are selected, it will be changed to \"Do nothing\"")
    )


class Preferences(AddonPreferences, Properties):
    bl_idname = __package__

    __slots__ = (
        "tab",
        "color_control_element",
        "color_active_control_element",
        "color_path",
        "color_active_path",
        "point_size",
        "line_width",
    )

    def draw(self, context: Context) -> None:
        layout: UILayout = self.layout

        layout.use_property_split = True

        row = layout.row()
        row.prop_tabs_enum(self, "tab")

        match self.tab:
            case 'APPEARANCE':
                bhqab.utils_ui.template_preset(
                    layout,
                    menu=PREFERENCES_MT_path_tool_appearance_preset,
                    operator=PREFERENCES_OT_path_tool_appearance_preset.bl_idname
                )

                col = layout.column(align=True)

                col.prop(self, "color_control_element")
                col.prop(self, "color_active_control_element")
                col.separator()
                col.prop(self, "color_path")
                col.prop(self, "color_active_path")
                col.separator()
                col.prop(self, "color_path_topology")
                col.prop(self, "color_active_path_topology")
                col.separator()
                col.prop(self, "point_size")
                col.prop(self, "line_width")
                col.separator()

                row = col.row(align=True)
                row.prop(self, "aa_method", expand=True)

                if self.aa_method == 'FXAA':
                    col.prop(self, "fxaa_preset")
                    scol = col.column(align=True)
                    scol.enabled = (self.fxaa_preset not in {'NONE', 'ULTRA'})
                    scol.prop(self, "fxaa_value")
                elif self.aa_method == 'SMAA':
                    col.prop(self, "smaa_preset")
                else:
                    col.label(text="Unknown Anti-Aliasing Method.")

            case 'BEHAVIOR':
                layout.prop(self, "auto_tweak_options")

            case 'KEYMAP':
                bhqab.utils_ui.template_tool_keymap(context, layout, km_name=TOOL_KM_NAME)

            case 'INFO':
                base_dir = os.path.join(os.path.dirname(__file__), "data", "info")

                for flag in ('README', 'LICENSE'):
                    if bhqab.utils_ui.template_disclosure_enum_flag(
                            layout, item=self, prop_enum_flag="info_tab", flag=flag):
                        if flag not in PREF_TEXTS:
                            with open(os.path.join(base_dir, f"{flag}.txt"), 'r') as file:
                                PREF_TEXTS[flag] = file.read()
                        if flag in PREF_TEXTS:
                            text = PREF_TEXTS[flag]
                        else:
                            text = "Looks like your addon installation is corrupted."

                        bhqab.utils_ui.draw_wrapped_text(context, layout, text=text)

                if bhqab.utils_ui.template_disclosure_enum_flag(
                        layout, item=self, prop_enum_flag="info_tab", flag='LINKS'):

                    props = layout.operator("wm.url_open", text="Release Notes")
                    props.url = "https://github.com/BlenderHQ/path_tool#release-notes"

                    props = layout.operator("wm.url_open", text="BlenderHQ on GitHub")
                    props.url = "https://github.com/BlenderHQ"


class PREFERENCES_MT_path_tool_appearance_preset(Menu):
    bl_label = "Appearance Preset"
    preset_subdir = os.path.join("path_tool", "preferences", "appearance")
    preset_operator = "script.execute_preset"
    draw = Menu.draw_preset


class PREFERENCES_OT_path_tool_appearance_preset(AddPresetBase, Operator):
    bl_idname = "preferences.path_tool_appearance_preset"
    bl_label = "Add Preset"
    preset_menu = PREFERENCES_MT_path_tool_appearance_preset.__name__
    preset_defines = [
        f"addon_pref = bpy.context.preferences.addons[\"{addon_pkg}\"].preferences"
    ]
    preset_values = [
        "addon_pref.color_control_element",
        "addon_pref.color_active_control_element",
        "addon_pref.color_path",
        "addon_pref.color_path_topology",
        "addon_pref.color_active_path",
        "addon_pref.color_active_path_topology",
        "addon_pref.point_size",
        "addon_pref.line_width",
    ]
    preset_subdir = os.path.join("path_tool", "preferences", "appearance")
