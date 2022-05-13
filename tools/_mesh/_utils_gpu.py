import gpu
from bpy.types import SpaceView3D
import bmesh
from gpu_extras.batch import batch_for_shader

from . import _annotations
from ..common import Path, PathFlag
from ... import __package__ as addon_pkg
from ... import bhqab


class MeshOperatorGPUUtils(_annotations.MeshOperatorVariables):
    @staticmethod
    def _gpu_gen_batch_faces_seq(fill_seq, is_active, shader):
        tmp_bm = bmesh.new()
        for face in fill_seq:
            tmp_bm.faces.new((tmp_bm.verts.new(v.co, v) for v in face.verts), face)

        tmp_bm.verts.index_update()
        tmp_bm.faces.ensure_lookup_table()

        tmp_loops = tmp_bm.calc_loop_triangles()

        r_batch = batch_for_shader(shader, 'TRIS', {
            "pos": tuple((v.co for v in tmp_bm.verts))},
            indices=tuple(((loop.vert.index for loop in tri) for tri in tmp_loops))
        )

        r_active_face_tri_start_index = None

        if is_active:
            r_active_face_tri_start_index = len(tmp_loops)
            tmp_bm = bmesh.new()
            face = fill_seq[-1]
            tmp_bm.faces.new((tmp_bm.verts.new(v.co, v) for v in face.verts), face)
            r_active_face_tri_start_index -= len(tmp_bm.calc_loop_triangles())

        return r_batch, r_active_face_tri_start_index

    def gen_batch_control_elements(self, is_active, path):
        shader = bhqab.gpu_extras.shader.vert_uniform_color

        r_batch = None
        r_active_elem_start_index = None

        if self.prior_ts_msm[1]:
            r_batch = batch_for_shader(shader, 'POINTS', {"pos": tuple((v.co for v in path.control_elements))})
            if is_active:
                r_active_elem_start_index = len(path.control_elements) - 1
        elif self.prior_ts_msm[2]:
            r_batch, r_active_elem_start_index = super(type(self), self)._gpu_gen_batch_faces_seq(
                path.control_elements,
                is_active,
                shader
            )

        return r_batch, r_active_elem_start_index

    def remove_gpu_handle(self) -> None:
        dh = getattr(self, "gpu_handle", None)
        if dh:
            SpaceView3D.draw_handler_remove(dh, 'WINDOW')

    def draw_callback_3d(self, context):
        preferences = context.preferences.addons[addon_pkg].preferences

        gpu.state.point_size_set(preferences.point_size)
        gpu.state.line_width_set(preferences.line_width)
        gpu.state.blend_set('ADDITIVE')
        gpu.state.depth_mask_set(True)
        gpu.state.depth_test_set('LESS_EQUAL')
        gpu.state.face_culling_set('NONE')

        draw_list: list[Path] = [_ for _ in self.path_seq if _ != self.active_path]
        draw_list.append(self.active_path)

        shader_ce = bhqab.gpu_extras.shader.vert_uniform_color
        shader_path = bhqab.gpu_extras.shader.path_uniform_color

        for path in draw_list:
            active_index = 0
            color = preferences.color_control_element
            color_active = color
            color_path = preferences.color_path
            if path.flag & PathFlag.TOPOLOGY:
                color_path = preferences.color_path_topology

            if path == self.active_path:
                active_index = self.active_index

                color = preferences.color_active_path_control_element
                color_active = preferences.color_active_control_element
                color_path = preferences.color_active_path

                if path.flag & PathFlag.TOPOLOGY:
                    color_path = preferences.color_active_path_topology

            shader_path.bind()

            for batch in path.batch_seq_fills:
                if batch:
                    shader_path.uniform_float("ModelMatrix", path.ob.matrix_world)
                    shader_path.uniform_float("color", color_path)
                    batch.draw(shader_path)

            shader_ce.bind()

            if path.batch_control_elements:
                shader_ce.uniform_float("ModelMatrix", path.ob.matrix_world)
                shader_ce.uniform_float("color", color)
                shader_ce.uniform_float("color_active", color_active)
                shader_ce.uniform_int("active_index", (active_index,))

                path.batch_control_elements.draw(shader_ce)
