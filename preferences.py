import bpy
from bpy.types import (
    Context,
    UILayout,
    AddonPreferences
)
from bpy.props import (
    EnumProperty,
    FloatVectorProperty,
    IntProperty,
)

from . import bhqab


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

    color_active_path: FloatVectorProperty(
        default=(1.0, 0.1, 0.1),
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        name="Active Path",
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
            col.separator()
            col.prop(self, "point_size")
            col.prop(self, "line_width")

        elif self.tab == 'KEYMAP':
            bhqab.utils_ui.template_tool_keymap(context, layout, "3D View Tool: Edit Mesh, Path Tool")
