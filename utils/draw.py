import bpy
import bgl
from gpu_extras.batch import batch_for_shader

from .. import shaders
from .. import __package__ as addon_pkg

if "_rc" in locals():
    import importlib
    importlib.reload(shaders)

_rc = None


class DrawUtils:
    @staticmethod
    def gen_batch_control_elements(context, path):
        shader = shaders.shader.vert_uniform_color
        tool_settings = context.scene.tool_settings
        select_mode = tuple(tool_settings.mesh_select_mode)

        if select_mode[1]:
            pos = [v.co for v in path.control_elements]
            return batch_for_shader(shader, 'POINTS', {"pos": pos})

        elif select_mode[2]:
            print("draw faces")

    @staticmethod
    def gen_batch_fill_elements(context, fill_seq):
        shader = shaders.shader.path_uniform_color
        tool_settings = context.scene.tool_settings
        select_mode = tuple(tool_settings.mesh_select_mode)

        if select_mode[1]:
            pos = []
            for edge in fill_seq:
                pos.extend([vert.co for vert in edge.verts])
            return batch_for_shader(shader, 'LINES', {"pos": pos})

        elif select_mode[2]:
            print("draw faces")

    def draw_callback_3d(self):
        preferences = bpy.context.preferences.addons[addon_pkg].preferences

        bgl.glPointSize(preferences.point_size)
        bgl.glLineWidth(preferences.line_width)

        bgl.glEnable(bgl.GL_MULTISAMPLE)
        bgl.glEnable(bgl.GL_LINE_SMOOTH)
        bgl.glHint(bgl.GL_LINE_SMOOTH_HINT, bgl.GL_NICEST)

        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)
        bgl.glEnable(bgl.GL_BLEND)

        bgl.glEnable(bgl.GL_POLYGON_SMOOTH)
        bgl.glHint(bgl.GL_POLYGON_SMOOTH_HINT, bgl.GL_NICEST)

        # bgl.glEnable(bgl.GL_DEPTH_TEST)

        # bgl.glEnable(bgl.GL_POLYGON_OFFSET_FILL)
        # bgl.glPolygonOffset(1.0, 1.0)

        for path in self.path_seq:
            active_index = 0
            color = preferences.color_control_element
            color_active = color
            color_path = preferences.color_path

            if path == self.active_path:
                if path.direction:
                    active_index = len(path.control_elements) - 1
                color = preferences.color_control_element
                color_active = preferences.color_active_control_element
                color_path = preferences.color_active_path

            shader_path = shaders.shader.path_uniform_color
            shader_path.bind()

            for batch in path.batch_seq_fills:
                if batch:
                    shader_path.uniform_float("ModelMatrix", path.matrix_world)
                    shader_path.uniform_float("color", color_path)
                    batch.draw(shader_path)

            shader_ce = shaders.shader.vert_uniform_color
            shader_ce.bind()

            if path.batch_control_elements:
                shader_ce.uniform_float("ModelMatrix", path.matrix_world)
                shader_ce.uniform_float("color", color)
                shader_ce.uniform_float("color_active", color_active)
                shader_ce.uniform_int("active_index", (active_index,))

                path.batch_control_elements.draw(shader_ce)

        bgl.glDisable(bgl.GL_BLEND)
        # bgl.glDisable(bgl.GL_DEPTH_TEST)
        bgl.glPointSize(1.0)
        bgl.glLineWidth(1.0)
