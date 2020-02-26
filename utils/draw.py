import bpy
import bgl
import bmesh
from gpu_extras.batch import batch_for_shader

from .. import shaders
from .. import __package__ as addon_pkg

if "_rc" in locals():
    import importlib
    importlib.reload(shaders)

_rc = None


def gen_batch_faces_seq(fill_seq, shader):
    temp_bmesh = bmesh.new()
    for face in fill_seq:
        temp_bmesh.faces.new((temp_bmesh.verts.new(v.co, v) for v in face.verts), face)
    temp_bmesh.verts.index_update()
    temp_bmesh.faces.ensure_lookup_table()

    pos = [v.co for v in temp_bmesh.verts]
    indices = [(loop.vert.index for loop in looptris) for looptris in temp_bmesh.calc_loop_triangles()]

    return batch_for_shader(shader, 'TRIS', {"pos": pos}, indices=indices)


def gen_batch_control_elements(context, path):
    shader = shaders.shader.vert_uniform_color
    tool_settings = context.scene.tool_settings
    select_mode = tuple(tool_settings.mesh_select_mode)

    if select_mode[1]:
        pos = [v.co for v in path.control_elements]
        return batch_for_shader(shader, 'POINTS', {"pos": pos})

    elif select_mode[2]:
        return gen_batch_faces_seq(path.control_elements, shader)


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
        return gen_batch_faces_seq(fill_seq, shader)


def draw_callback_3d(self):
    preferences = bpy.context.preferences.addons[addon_pkg].preferences

    bgl.glPointSize(preferences.point_size)
    bgl.glLineWidth(preferences.line_width)

    bgl.glEnable(bgl.GL_PROGRAM_POINT_SIZE)

    bgl.glEnable(bgl.GL_MULTISAMPLE)
    bgl.glEnable(bgl.GL_LINE_SMOOTH)
    bgl.glHint(bgl.GL_LINE_SMOOTH_HINT, bgl.GL_NICEST)

    bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)
    bgl.glEnable(bgl.GL_BLEND)

    # bgl.glEnable(bgl.GL_POLYGON_SMOOTH)
    bgl.glHint(bgl.GL_POLYGON_SMOOTH_HINT, bgl.GL_NICEST)

    bgl.glEnable(bgl.GL_DEPTH_TEST)
    bgl.glDepthFunc(bgl.GL_LEQUAL)
    bgl.glDepthRange(0.00001, 0.99999)

    # bgl.glDisable(bgl.GL_POLYGON_OFFSET_FILL)
    #bgl.glPolygonOffset(1.0, 0.0)

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
