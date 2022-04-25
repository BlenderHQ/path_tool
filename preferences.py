import bpy
from bpy.types import AddonPreferences
from bpy.props import (
    EnumProperty,
    FloatVectorProperty,
    FloatProperty,
)

from . import bhqab


class Preferences(AddonPreferences):
    bl_idname = __package__

    tab: EnumProperty(
        name="Tab",
        description="User preferences tab to be displayed",
        items=(
            ('APPEARANCE', "Appearance", "Appearance user preferences"),
            ('KEYMAP', "Keymap", "Keymap settings"),
        ),
        default='APPEARANCE',
        options={'HIDDEN', 'SKIP_SAVE'},
    )

    color_control_element: FloatVectorProperty(
        name="Control Element",
        default=[0.622574, 0.685957, 0.666101, 1.000000],
        subtype="COLOR", size=4, min=0.0, max=1.0,
        description="Control element color"
    )

    color_active_path_control_element: FloatVectorProperty(
        name="Active Path Control Element",
        default=[0.969922, 0.969922, 0.969922, 1.000000],
        subtype="COLOR", size=4, min=0.0, max=1.0,
        description="Control element color"
    )

    color_active_control_element: FloatVectorProperty(
        name="Active Control Element",
        default=[0.039087, 0.331906, 0.940392, 1.000000],
        subtype="COLOR", size=4, min=0.0, max=1.0,
        description="Control element color"
    )

    color_path: FloatVectorProperty(
        name="Path",
        default=[0.000000, 0.700000, 1.000000, 1.000000],
        subtype="COLOR", size=4, min=0.0, max=1.0,
        description="Path color"
    )

    color_active_path: FloatVectorProperty(
        name="Active Path",
        default=[1.000000, 0.100000, 0.100000, 1.000000],
        subtype="COLOR", size=4, min=0.0, max=1.0,
        description="Path color"
    )

    point_size: FloatProperty(
        name="Vertex Size",
        default=4.0,
        min=1.0, max=10.0, subtype='PIXEL'
    )

    line_width: FloatProperty(
        name="Edge Width",
        default=3.0,
        min=1.0, max=10.0, subtype='PIXEL'
    )

    def draw(self, context: bpy.types.Context):
        layout: bpy.types.UILayout = self.layout

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
            col.separator()
            col.prop(self, "point_size")
            col.prop(self, "line_width")
        elif self.tab == 'KEYMAP':
            bhqab.utils_ui.template_tool_keymap(context, layout, "3D View Tool: Edit Mesh, Path Tool")
