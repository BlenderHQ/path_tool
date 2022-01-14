# NOTE: Keep this file at addon root directory. Otherwise, `__package__` would
# give wrong information.

import sys
import bpy
import rna_keymap_ui


def tested_bver_older() -> tuple:
    bl_info = getattr(sys.modules[__package__], "bl_info")
    return bl_info["blender"]


def tested_bver_latest() -> tuple:
    bl_info = getattr(sys.modules[__package__], "bl_info")
    return bl_info["version"]


class PathToolPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    color_control_element: bpy.props.FloatVectorProperty(
        name="Control Element",
        default=[0.622574, 0.685957, 0.666101, 1.000000],
        subtype="COLOR", size=4, min=0.0, max=1.0,
        description="Control element color"
    )

    color_active_path_control_element: bpy.props.FloatVectorProperty(
        name="Active Path Control Element",
        default=[0.969922, 0.969922, 0.969922, 1.000000],
        subtype="COLOR", size=4, min=0.0, max=1.0,
        description="Control element color"
    )

    color_active_control_element: bpy.props.FloatVectorProperty(
        name="Active Control Element",
        default=[0.039087, 0.331906, 0.940392, 1.000000],
        subtype="COLOR", size=4, min=0.0, max=1.0,
        description="Control element color"
    )

    color_path: bpy.props.FloatVectorProperty(
        name="Path",
        default=[0.000000, 0.700000, 1.000000, 1.000000],
        subtype="COLOR", size=4, min=0.0, max=1.0,
        description="Path color"
    )

    color_active_path: bpy.props.FloatVectorProperty(
        name="Active Path",
        default=[1.000000, 0.100000, 0.100000, 1.000000],
        subtype="COLOR", size=4, min=0.0, max=1.0,
        description="Path color"
    )

    point_size: bpy.props.FloatProperty(
        name="Vertex Size",
        default=4.0,
        min=1.0, max=10.0, subtype='PIXEL'
    )

    line_width: bpy.props.FloatProperty(
        name="Edge Width",
        default=3.0,
        min=1.0, max=10.0, subtype='PIXEL'
    )

    def draw(self, _context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        # Check Blender version for compatibility.
        def _draw_compatibility_link(lay) -> None:
            lay.label(text="Please, read the documentation about compatibility support:")
            col.operator("wm.url_open", text="Read about compatibility",
                         icon='URL').url = "https://github.com/BlenderHQ/path_tool/blob/master/README.md#compatibility"

        if bpy.app.version < tested_bver_older():
            col = layout.column(align=True)
            col.label(
                text="You Blender version is less than minimal supported!",
                icon='ERROR'
            )
            _draw_compatibility_link(col)
            return

        elif bpy.app.version > tested_bver_latest():
            col = layout.column(align=True)
            col.label(text="Your Blender version may be not tested", icon='INFO')
            _draw_compatibility_link(col)

        col = layout.column(align=True)

        col.prop(self, "color_control_element")
        col.prop(self, "color_active_path_control_element")
        col.prop(self, "color_active_control_element")
        col.prop(self, "color_path")
        col.prop(self, "color_active_path")
        col.separator()
        col.prop(self, "point_size")
        col.prop(self, "line_width")
