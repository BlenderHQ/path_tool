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


class Preferences(AddonPreferences):
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
        default=(0.8, 0.8, 0.8),
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        options={'HIDDEN', 'SKIP_SAVE'},
        name="Control Element",
        description="Control element color",
    )

    color_active_control_element: FloatVectorProperty(
        default=(0.039087, 0.331906, 0.940392),
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        options={'HIDDEN', 'SKIP_SAVE'},
        name="Active Control Element",
        description="Color of active control element",
    )

    color_path: FloatVectorProperty(
        default=(0.593397, 0.708376, 0.634955),
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        options={'HIDDEN', 'SKIP_SAVE'},
        name="Path",
        description="Regular path color",
    )

    color_path_topology: FloatVectorProperty(
        default=(1.0, 0.952328, 0.652213),
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        options={'HIDDEN', 'SKIP_SAVE'},
        name="Topology Path",
        description="Color of paths which uses topology calculation method",
    )

    color_active_path: FloatVectorProperty(
        default=(0.304987, 0.708376, 0.450786),
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        options={'HIDDEN', 'SKIP_SAVE'},
        name="Active Path",
        description="Active path color",
    )

    color_active_path_topology: FloatVectorProperty(
        default=(1.0, 0.883791, 0.152213),
        subtype='COLOR',
        size=3,
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

    def draw(self, context: Context) -> None:
        layout: UILayout = self.layout

        layout.use_property_split = True

        row = layout.row()
        row.prop_tabs_enum(self, "tab")

        if self.tab == 'APPEARANCE':
            col = layout.column(align=True)

            bhqab.utils_ui.template_preset(
                col,
                menu=PREFERENCES_MT_path_tool_appearance_preset,
                operator=PREFERENCES_OT_path_tool_add_appearance.bl_idname
            )

            col.separator()
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

        elif self.tab == 'KEYMAP':
            bhqab.utils_ui.template_tool_keymap(context, layout, km_name="3D View Tool: Edit Mesh, Select Path")


class PREFERENCES_MT_path_tool_appearance_preset(Menu):
    bl_label = "Appearance Preset"
    preset_subdir = os.path.join("path_tool", "preferences", "appearance")
    preset_operator = "script.execute_preset"
    draw = Menu.draw_preset


class PREFERENCES_OT_path_tool_add_appearance(AddPresetBase, Operator):
    bl_idname = "preferences.path_tool_preferences_add_appearance"
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
