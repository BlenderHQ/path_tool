import bpy
from bpy.props import FloatProperty, FloatVectorProperty, EnumProperty


class PathToolPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    color_control_element: FloatVectorProperty(
        name="Control Element",
        default=[1.0, 1.0, 1.0, 1.0],
        subtype="COLOR", size=4, min=0.0, max=1.0,
        description="Control element color"
    )

    color_active_control_element: FloatVectorProperty(
        name="Active Control Element",
        default=[1.0, 0.0, 0.5, 1.0],
        subtype="COLOR", size=4, min=0.0, max=1.0,
        description="Control element color"
    )

    color_path: FloatVectorProperty(
        name="Path",
        default=[0.0, 0.7, 1.0, 0.7],
        subtype="COLOR", size=4, min=0.0, max=1.0,
        description="Path color"
    )

    color_active_path: FloatVectorProperty(
        name="Active Path",
        default=[1.0, 0.1, 0.1, 1.0],
        subtype="COLOR", size=4, min=0.0, max=1.0,
        description="Path color"
    )

    point_size: FloatProperty(
        name="Vertex Size",
        default=4.0,
        min=1.0, max=10.0, subtype='PIXEL')

    line_width: FloatProperty(
        name="Edge Width",
        default=3.0,
        min=1.0, max=10.0, subtype='PIXEL')

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col_flow = layout.column_flow(columns=2, align=True)

        col_flow.use_property_split = True
        col_flow.use_property_decorate = False

        col_flow.prop(self, "color_control_element")
        col_flow.prop(self, "color_active_control_element")
        col_flow.prop(self, "color_path")
        col_flow.prop(self, "color_active_path")
        col_flow.prop(self, "point_size")
        col_flow.prop(self, "line_width")
