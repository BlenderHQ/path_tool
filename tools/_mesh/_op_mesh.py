from enum import IntFlag, auto
from collections import deque

import bpy
import bgl
from bpy.types import Operator, SpaceView3D
from bpy.props import EnumProperty
import bmesh
from gpu_extras.batch import batch_for_shader

from ..common import InteractEvent, PathFlag, Path, OPMode
from ... import __package__ as addon_pkg
from ... import bhqab


class MESH_OT_select_path(Operator):
    bl_idname = "mesh.path_tool"
    bl_label = "Path Tool"
    bl_options = {'REGISTER', 'UNDO'}

    context_action: EnumProperty(
        items=(
            ('TCLPATH', "Toggle Close Path", "Close the path from the first to the last control point", '', 2),
            ('CHDIR', "Change direction", "Changes the direction of the path", '', 4),
            ('APPLY', "Apply All", "Apply all paths and make changes to the mesh", '', 8),
        ),
        options={'ENUM_FLAG'},
        default=set(),
    )

    context_undo: EnumProperty(
        items=(
            ('UNDO', "Undo", "Undo one step", 'LOOP_BACK', 2),
            ('REDO', "Redo", "Redo one step", 'LOOP_FORWARDS', 4),
        ),
        options={'ENUM_FLAG'},
        default=set(),
        name="Action History",
    )

    mark_select: EnumProperty(
        items=(
            ('EXTEND', "Extend", "Extend existing selection", 'SELECT_EXTEND', 1),
            ('NONE', "Do nothing", "Do nothing", "X", 2),
            ('SUBTRACT', "Subtract", "Subtract existing selection", 'SELECT_SUBTRACT', 3),
            ('INVERT', "Invert", "Inverts existing selection", 'SELECT_DIFFERENCE', 4),
        ),
        default='EXTEND',
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
        name="Seams",
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
        name="Sharp",
        description="Mark sharp options",
    )

    def draw_func(self, layout):
        layout.row().prop(self, "mark_select", text="Select", icon_only=True, expand=True)
        layout.row().prop(self, "mark_seam", text="Seam", icon_only=True, expand=True)
        layout.row().prop(self, "mark_sharp", text="Sharp", icon_only=True, expand=True)

    def draw(self, _context):
        self.draw_func(self.layout)

    def popup_menu_pie_draw(self, popup, context):
        pie = popup.layout.menu_pie()
        col = pie.box().column()
        col.use_property_split = True
        self.draw_func(col)
        col.prop(self, "context_undo", text="Action", expand=True)
        pie.prop_tabs_enum(self, "context_action")

    @staticmethod
    def _pack_event(item):
        return item.type, item.value, item.alt, item.ctrl, item.shift

    @staticmethod
    def _eval_meshes(context):
        ret = []
        for ob in context.objects_in_mode:

            bm = bmesh.from_edit_mesh(ob.data)
            for elem_arr in (bm.verts, bm.edges, bm.faces):
                elem_arr.ensure_lookup_table()
            ret.append((ob, bm))
        return tuple(ret)

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

        if self.op_mode is OPMode.MEDGE:
            r_batch = batch_for_shader(shader, 'POINTS', {"pos": tuple((v.co for v in path.control_elements))})
            if is_active:
                r_active_elem_start_index = len(path.control_elements) - 1
        elif self.op_mode is OPMode.MFACE:
            r_batch, r_active_elem_start_index = MESH_OT_select_path._gpu_gen_batch_faces_seq(
                path.control_elements,
                is_active,
                shader
            )

        return r_batch, r_active_elem_start_index

    def draw_callback_3d(self, context):
        preferences = context.preferences.addons[addon_pkg].preferences

        bgl.glPointSize(preferences.point_size)
        bgl.glLineWidth(preferences.line_width)

        bgl.glEnable(bgl.GL_MULTISAMPLE)
        bgl.glEnable(bgl.GL_LINE_SMOOTH)
        bgl.glHint(bgl.GL_LINE_SMOOTH_HINT, bgl.GL_NICEST)

        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)
        bgl.glEnable(bgl.GL_BLEND)

        bgl.glHint(bgl.GL_POLYGON_SMOOTH_HINT, bgl.GL_NICEST)

        bgl.glEnable(bgl.GL_DEPTH_TEST)
        bgl.glDepthFunc(bgl.GL_LEQUAL)

        bgl.glDisable(bgl.GL_POLYGON_OFFSET_FILL)
        bgl.glPolygonOffset(1.0, 0.0)

        draw_list = [_ for _ in self.path_seq if _ != self.active_path]
        draw_list.append(self.active_path)

        shader_ce = bhqab.gpu_extras.shader.vert_uniform_color
        shader_path = bhqab.gpu_extras.shader.path_uniform_color

        for path in draw_list:
            active_index = 0
            color = preferences.color_control_element
            color_active = color
            color_path = preferences.color_path

            if path == self.active_path:
                active_index = self.active_index

                color = preferences.color_active_path_control_element
                color_active = preferences.color_active_control_element
                color_path = preferences.color_active_path

            shader_path.bind()

            for batch in path.batch_seq_fills:
                if batch:
                    shader_path.uniform_float(
                        "ModelMatrix", path.ob.matrix_world)
                    shader_path.uniform_float("color", color_path)
                    batch.draw(shader_path)

            shader_ce.bind()

            if path.batch_control_elements:
                shader_ce.uniform_float("ModelMatrix", path.ob.matrix_world)
                shader_ce.uniform_float("color", color)
                shader_ce.uniform_float("color_active", color_active)
                shader_ce.uniform_int("active_index", (active_index,))

                path.batch_control_elements.draw(shader_ce)

        bgl.glDisable(bgl.GL_BLEND)
        bgl.glPointSize(1.0)
        bgl.glLineWidth(1.0)

    @property
    def active_path(self):
        if (self._active_path_index is not None) and (self._active_path_index <= len(self.path_seq) - 1):
            return self.path_seq[self._active_path_index]

    @active_path.setter
    def active_path(self, value):
        if value not in self.path_seq:
            self.path_seq.append(value)
        self._active_path_index = self.path_seq.index(value)

    @staticmethod
    def set_selection_state(elem_seq, state=True):
        for elem in elem_seq:
            elem.select = state

    def get_element_by_mouse(self, context, event):

        initial_select_mode = self._set_ts_mesh_select_mode(context, self.op_mode)

        bpy.ops.mesh.select_all(action='DESELECT')
        mouse_location = (event.mouse_region_x, event.mouse_region_y)
        bpy.ops.view3d.select(location=mouse_location)

        elem = None
        ob = None
        for ob, bm in self.bm_arr:
            elem = bm.select_history.active
            if elem:
                break
        self._set_ts_mesh_select_mode(context, initial_select_mode)
        return elem, ob

    def get_current_state_copy(self):
        return tuple((self._active_path_index, tuple(n.copy() for n in self.path_seq)))

    def undo(self, context):
        if len(self.undo_history) == 1:
            self.cancel(context)
            return {'CANCELLED'}

        elif len(self.undo_history) > 1:
            step = self.undo_history.pop()
            self.redo_history.append(step)
            self._active_path_index, self.path_seq = self.undo_history[-1]
            self._just_closed_path = False

        context.area.tag_redraw()

        return {'RUNNING_MODAL'}

    def redo(self, context):
        if len(self.redo_history) > 0:
            step = self.redo_history.pop()
            self.undo_history.append(step)
            self._active_path_index, self.path_seq = self.undo_history[-1]
            context.area.tag_redraw()
        else:
            self.report({'WARNING'}, message="Can not redo anymore")

    def register_undo_step(self):
        step = self.get_current_state_copy()
        self.undo_history.append(step)
        self.redo_history.clear()

    def get_linked_island_index(self, context, elem):
        for i, linked_island in enumerate(self.mesh_islands):
            if elem in linked_island:
                return i

        sm = self._set_ts_mesh_select_mode(context, self.op_mode)

        bpy.ops.mesh.select_all(action='DESELECT')
        elem.select_set(True)
        bpy.ops.mesh.select_linked(delimit={'NORMAL'})

        linked_island = self.get_selected_elements(self.op_mode)
        self._set_ts_mesh_select_mode(context, sm)

        bpy.ops.mesh.select_all(action='DESELECT')
        self.mesh_islands.append(linked_island)
        return len(self.mesh_islands) - 1

    def update_meshes(self):
        for ob, bm in self.bm_arr:
            bm.select_flush_mode()
            bmesh.update_edit_mesh(mesh=ob.data, loop_triangles=False, destructive=False)

    def update_path_beetween(self, context, elem_0, elem_1):
        sm = self._set_ts_mesh_select_mode(context, self.op_mode)

        bpy.ops.mesh.select_all(action='DESELECT')
        self.set_selection_state((elem_0, elem_1), True)
        bpy.ops.mesh.shortest_path_select()
        self.set_selection_state((elem_0, elem_1), False)
        r_fill_seq = self.get_selected_elements(self.op_mode)
        bpy.ops.mesh.select_all(action='DESELECT')
        # Exception if control points in one edge
        if (not r_fill_seq) and (sm & OPMode.MEDGE):
            for edge in elem_0.link_edges:
                if edge.other_vert(elem_0) == elem_1:
                    r_fill_seq = [edge]

        self._set_ts_mesh_select_mode(context, sm)
        return r_fill_seq

    def update_fills_by_element_index(self, context, path, elem_index):
        pairs_items = path.get_pairs_items(elem_index)
        for item in pairs_items:
            elem_0, elem_1, fill_index = item
            fill_seq = self.update_path_beetween(context, elem_0, elem_1)

            path.fill_elements[fill_index] = fill_seq

            shader = bhqab.gpu_extras.shader.path_uniform_color
            batch = None
            if self.op_mode & OPMode.MEDGE:
                pos = []
                for edge in fill_seq:
                    pos.extend([vert.co for vert in edge.verts])
                batch = batch_for_shader(shader, 'LINES', {"pos": pos})

            elif self.op_mode & OPMode.MFACE:
                batch, _ = MESH_OT_select_path._gpu_gen_batch_faces_seq(fill_seq, False, shader)

            path.batch_seq_fills[fill_index] = batch

    def gen_final_elements_seq(self, context):
        self.select_only_seq = {}
        self.markup_seq = {}

        for ob in context.objects_in_mode:
            index_select_seq = []
            index_markup_seq = []

            for path in self.path_seq:
                if path.ob != ob:
                    continue
                for fill_seq in path.fill_elements:
                    index_select_seq.extend([n.index for n in fill_seq])
                if self.op_mode & OPMode.MEDGE:
                    index_markup_seq = index_select_seq
                if self.op_mode & OPMode.MFACE:
                    # For face selection mode control elements are required too
                    index_select_seq.extend([face.index for face in path.control_elements])
                    tmp = path.fill_elements
                    tmp.append(path.control_elements)
                    for fill_seq in tmp:
                        for face in fill_seq:
                            index_markup_seq.extend([e.index for e in face.edges])
            # Remove duplicates
            self.select_only_seq[ob.as_pointer()] = list(
                dict.fromkeys(index_select_seq))
            self.markup_seq[ob.as_pointer()] = list(
                dict.fromkeys(index_markup_seq))

    def remove_path_doubles(self, context, path):
        for i, control_element in enumerate(path.control_elements):
            if path.control_elements.count(control_element) > 1:
                for j, other_control_element in enumerate(path.control_elements):
                    if i == j:  # Skip current control element
                        continue
                    if other_control_element == control_element:
                        # First-last control element same path
                        if i == 0 and j == len(path.control_elements) - 1:
                            path.pop_control_element(-1)
                            if (path.flag ^ PathFlag.CLOSE):
                                path.flag |= PathFlag.CLOSE
                                self.update_fills_by_element_index(context, path, 0)

                                message = "Closed path"
                                if path == self.active_path:
                                    self._just_closed_path = True
                                    message = "Closed active path"
                                self.report(type={'INFO'}, message=message)
                            else:
                                self.update_fills_by_element_index(context, path, 0)
                        # Adjacent control elements
                        elif i in (j - 1, j + 1):
                            path.pop_control_element(j)
                            batch, _ = self.gen_batch_control_elements(path == self.active_path, path)
                            path.batch_control_elements = batch
                            self.report(type={'INFO'}, message="Merged adjacent control elements")
                        else:
                            # Maybe, undo here?
                            pass

    def check_join_pathes(self, context):
        for i, path in enumerate(self.path_seq):
            for other_path in self.path_seq:
                if path == other_path:
                    continue

                # Join two pathes
                if (
                    ((path.flag & other_path.flag) ^ PathFlag.CLOSE) and (
                        (path.control_elements[0] == other_path.control_elements[0])
                        or (path.control_elements[-1] == other_path.control_elements[-1])
                        or (path.control_elements[-1] == other_path.control_elements[0])
                        or (path.control_elements[0] == other_path.control_elements[-1])
                    )
                ):
                    path += other_path
                    self.path_seq.remove(other_path)
                    self._active_path_index = i

                    batch, _ = self.gen_batch_control_elements(path == self.active_path, path)
                    path.batch_control_elements = batch
                    self.report(type={'INFO'}, message="Joined two paths")

    def interact_control_element(self, context, elem, ob, interact_event):
        if elem and interact_event is InteractEvent.ADD:
            if not self.path_seq:
                return self.interact_control_element(context, elem, ob, InteractEvent.ADD_NEW_PATH)

            new_elem_index = None

            elem_index = self.active_path.is_in_control_elements(elem)
            if elem_index is None:
                new_elem_index = len(self.active_path.control_elements)

                fill_index = self.active_path.is_in_fill_elements(elem)
                if fill_index is None:
                    is_found_in_other_path = False
                    for path in self.path_seq:
                        if path == self.active_path:
                            continue
                        other_elem_index = path.is_in_control_elements(elem)
                        if other_elem_index is None:
                            other_fill_index = path.is_in_fill_elements(elem)
                            if other_fill_index is not None:
                                is_found_in_other_path = True
                        else:
                            is_found_in_other_path = True

                        if is_found_in_other_path:
                            self.active_path = path
                            self._just_closed_path = False
                            self.interact_control_element(context, elem, ob, InteractEvent.ADD)
                            return
                else:
                    new_elem_index = fill_index + 1
                    self._just_closed_path = False

            elif len(self.active_path.control_elements) == 1:
                batch, self.active_index = self.gen_batch_control_elements(True, self.active_path)
                self.active_path.batch_control_elements = batch

            if elem_index is not None:
                self.drag_elem_indices = [path.is_in_control_elements(elem) for path in self.path_seq]
                self._just_closed_path = False
            self._drag_elem = elem

            if self._just_closed_path:
                return self.interact_control_element(context, elem, ob, InteractEvent.ADD_NEW_PATH)

            if new_elem_index is not None:
                linked_island_index = self.get_linked_island_index(context, elem)
                if self.active_path.island_index != linked_island_index:
                    return self.interact_control_element(context, elem, ob, InteractEvent.ADD_NEW_PATH)

                self.active_path.insert_control_element(new_elem_index, elem)
                self.update_fills_by_element_index(context, self.active_path, new_elem_index)

                batch, self.active_index = self.gen_batch_control_elements(True, self.active_path)
                self.active_path.batch_control_elements = batch

                self.drag_elem_indices = [path.is_in_control_elements(elem) for path in self.path_seq]

        elif elem and interact_event is InteractEvent.ADD_NEW_PATH:
            linked_island_index = self.get_linked_island_index(context, elem)
            self.active_path = Path(elem, linked_island_index, ob)
            self._just_closed_path = False
            self.interact_control_element(context, elem, ob, InteractEvent.ADD)
            self.report(type={'INFO'}, message="Created new path")
            return

        elif elem and interact_event is InteractEvent.REMOVE:
            self._just_closed_path = False

            elem_index = self.active_path.is_in_control_elements(elem)
            if elem_index is None:
                for path in self.path_seq:
                    other_elem_index = path.is_in_control_elements(elem)
                    if other_elem_index is not None:
                        self.active_path = path
                        self.interact_control_element(context, elem, ob, InteractEvent.REMOVE)
                        return
            else:
                self.active_path.pop_control_element(elem_index)

                if not len(self.active_path.control_elements):
                    self.path_seq.remove(self.active_path)
                    if len(self.path_seq):
                        self.active_path = self.path_seq[-1]
                else:
                    self.update_fills_by_element_index(context, self.active_path, elem_index)
                    batch, self.active_index = self.gen_batch_control_elements(True, self.active_path)
                    self.active_path.batch_control_elements = batch

        elif elem and interact_event is InteractEvent.DRAG:
            if (not self._drag_elem) or (len(self.drag_elem_indices) != len(self.path_seq)):
                return
            self._just_closed_path = False

            linked_island_index = self.get_linked_island_index(context, elem)
            if self.active_path.island_index == linked_island_index:
                self._drag_elem = elem

                for i, path in enumerate(self.path_seq):
                    j = self.drag_elem_indices[i]
                    if j is not None:
                        path.control_elements[j] = elem

                        self.update_fills_by_element_index(context, path, j)
                        path.batch_control_elements, self.active_index = self.gen_batch_control_elements(
                            path == self.active_path,
                            path
                        )

        elif interact_event is InteractEvent.CHDIR:
            self.active_path.reverse()
            batch, self.active_index = self.gen_batch_control_elements(True, self.active_path)
            self.active_path.batch_control_elements = batch
            self._just_closed_path = False

        elif interact_event is InteractEvent.CLOSE:
            self.active_path.flag ^= PathFlag.CLOSE

            if self.active_path.flag & PathFlag.CLOSE:
                self.update_fills_by_element_index(context, self.active_path, 0)
                if len(self.active_path.control_elements) > 2:
                    self._just_closed_path = True
            else:
                self.active_path.fill_elements[-1] = []
                self.active_path.batch_seq_fills[-1] = None
                self._just_closed_path = False
                self.check_join_pathes(context)

        elif interact_event is InteractEvent.RELEASE:
            self.drag_elem_indices = []
            self._drag_elem = None

            for path in self.path_seq:
                self.remove_path_doubles(context, path)
            self.check_join_pathes(context)

            self.register_undo_step()

    @property
    def initial_op_mode(self):
        return self._initial_op_mode

    @property
    def op_mode(self):
        return self._op_mode

    @staticmethod
    def _set_ts_mesh_select_mode(context, mode_flag=OPMode.NONE):
        ts = context.scene.tool_settings

        # Initial select mode flag.
        r_initial_msm = OPMode.PRIMARY
        if ts.mesh_select_mode[0]:
            r_initial_msm |= OPMode.MVERT
        if ts.mesh_select_mode[1]:
            r_initial_msm |= OPMode.MEDGE
        if ts.mesh_select_mode[2]:
            r_initial_msm |= OPMode.MFACE

        if mode_flag ^ OPMode.NONE:
            if mode_flag & OPMode.PRIMARY:
                msm = (
                    bool(mode_flag & OPMode.MVERT),
                    bool(mode_flag & OPMode.MEDGE),
                    bool(mode_flag & OPMode.MFACE)
                )
            else:
                msm = (
                    bool(mode_flag & (OPMode.MVERT | OPMode.MEDGE)),
                    False,
                    bool((mode_flag & OPMode.MFACE) and (mode_flag ^ (OPMode.MVERT | OPMode.MEDGE)))
                )

            if ts.mesh_select_mode != msm:
                ts.mesh_select_mode = msm
        return r_initial_msm

    def get_selected_elements(self, m_flag=OPMode.NONE):
        ret = tuple()

        if m_flag & OPMode.PRIMARY:
            if m_flag & OPMode.MEDGE:
                attr = "edges"
            elif m_flag & OPMode.MVERT:
                attr = "verts"

            if m_flag & OPMode.MFACE:
                attr = "faces"
        else:
            if m_flag & (OPMode.MEDGE | OPMode.MVERT):
                attr = "verts"
            elif self.op_mode & OPMode.MFACE:
                attr = "faces"

        for _, bm in self.bm_arr:
            elem_arr = getattr(bm, attr)
            ret += tuple((n for n in elem_arr if n.select))
        return ret

    def invoke(self, context, event):
        wm = context.window_manager
        ts = context.scene.tool_settings
        num_undo_steps = context.preferences.edit.undo_steps

        # ____________________________________________________________________ #
        # Input keymaps:

        kc = wm.keyconfigs.user
        km_path_tool = kc.keymaps["3D View Tool: Edit Mesh, Path Tool"]
        kmi = km_path_tool.keymap_items[0]

        # Select and context pie menu mouse buttons.
        self.select_mb = kmi.type
        self.pie_mb = 'LEFTMOUSE'
        if self.select_mb == 'LEFTMOUSE':
            self.pie_mb = 'RIGHTMOUSE'

        # Modal keymap.
        self.modal_events = dict()
        for kmi in kc.keymaps["Standard Modal Map"].keymap_items:
            ev = self._pack_event(kmi)
            self.modal_events[(ev[0], ev[1], False, False, False)] = kmi.propvalue

        # Operator's undo/redo keymap.
        self.undo_redo_events = dict()
        km_screen = kc.keymaps['Screen']

        kmi = km_screen.keymap_items.find_from_operator(idname='ed.undo')
        self.undo_redo_events[self._pack_event(kmi)] = 'UNDO'

        kmi = km_screen.keymap_items.find_from_operator(idname='ed.redo')
        self.undo_redo_events[self._pack_event(kmi)] = 'REDO'

        # Navigation events which would be passed through operator's modal cycle.
        nav_events = []
        for kmi in kc.keymaps['3D View'].keymap_items:
            kmi: bpy.types.KeyMapItem

            if kmi.idname in (
                "view3d.rotate",
                "view3d.move",
                "view3d.zoom",
                "view3d.dolly",
                "view3d.view_center_camera",
                "view3d.view_center_lock",
                "view3d.view_all",
                "view3d.navigate",
                "view3d.view_camera",
                "view3d.view_axis",
                "view3d.view_orbit",
                "view3d.view_persportho",
                "view3d.view_pan",
                "view3d.view_roll",
                "view3d.view_center_pick",
                "view3d.view_selected",
            ):
                ev = list(self._pack_event(kmi))
                if ev[0] == 'WHEELINMOUSE':
                    ev[0] = 'WHEELUPMOUSE'
                elif ev[0] == 'WHEELOUTMOUSE':
                    ev[0] = 'WHEELDOWNMOUSE'
                nav_events.append(tuple(ev))
        self.nav_events = tuple(nav_events)

        self.is_mouse_pressed = False
        self.is_navigation_active = False

        # ____________________________________________________________________ #
        # Initialize variables.

        self.path_seq = list()
        self.mesh_islands = list()
        self.drag_elem_indices = list()

        self._active_path_index = None
        self._drag_elem = None
        self._just_closed_path = False

        self.undo_history = deque(maxlen=num_undo_steps)
        self.redo_history = deque(maxlen=num_undo_steps)

        self.select_only_seq = dict()
        self.markup_seq = dict()

        # ____________________________________________________________________ #
        # Meshes context setup.
        self._op_mode = OPMode.MEDGE
        if ts.mesh_select_mode[2]:
            self._op_mode = OPMode.MFACE

        # Evaluate meshes:
        self.bm_arr = self._eval_meshes(context)

        self._initial_op_mode = self._set_ts_mesh_select_mode(context, OPMode.NONE | OPMode.PRIMARY)
        self.initial_select = self.get_selected_elements(self.initial_op_mode)

        # Prevent first click empty space
        elem, _ = self.get_element_by_mouse(context, event)
        if not elem:
            self.cancel(context)
            return {'CANCELLED'}

        # print(self.op_mode)
        self._set_ts_mesh_select_mode(context, self.op_mode)

        self.gpu_handle = SpaceView3D.draw_handler_add(self.draw_callback_3d, (context,), 'WINDOW', 'POST_VIEW')
        wm.modal_handler_add(self)
        self.modal(context, event)
        return {'RUNNING_MODAL'}

    def remove_gpu_handle(self) -> None:
        dh = getattr(self, "gpu_handle", None)
        if dh:
            SpaceView3D.draw_handler_remove(dh, 'WINDOW')

    def cancel(self, context):
        self._set_ts_mesh_select_mode(context, self.initial_op_mode)
        self.set_selection_state(self.initial_select, True)
        self.update_meshes()
        self.remove_gpu_handle()

    def modal(self, context, event):
        ev = self._pack_event(event)
        modal_action = self.modal_events.get(ev, None)
        undo_redo_action = self.undo_redo_events.get(ev, None)
        interact_event = None

        if ev in self.nav_events:
            return {'PASS_THROUGH'}

        elif self.is_navigation_active and event.value == 'RELEASE':
            self.is_navigation_active = False
            self.set_selection_state(self.initial_select, True)
            self.update_meshes()
            return {'RUNNING_MODAL'}

        elif modal_action == 'CANCEL':
            self.cancel(context)
            return {'CANCELLED'}

        elif (modal_action == 'APPLY') or ('APPLY' in self.context_action):
            self.context_action = set()

            self.gen_final_elements_seq(context)
            self.remove_gpu_handle()
            return self.execute(context)

        elif 'TCLPATH' in self.context_action:
            self.context_action = set()
            interact_event = InteractEvent.CLOSE

        elif 'CHDIR' in self.context_action:
            self.context_action = set()
            interact_event = InteractEvent.CHDIR

        elif (undo_redo_action == 'UNDO') or ('UNDO' in self.context_undo):
            self.context_undo = set()
            return self.undo(context)

        elif (undo_redo_action == 'REDO') or ('REDO' in self.context_undo):
            self.context_undo = set()
            self.redo(context)

        elif ev == (self.pie_mb, 'PRESS', False, False, False):
            context.window_manager.popup_menu_pie(
                event=event,
                draw_func=self.popup_menu_pie_draw,
                title="Path Tool",
                icon='NONE'
            )

        elif ev == (self.select_mb, 'PRESS', False, False, False):
            self.is_mouse_pressed = True
            interact_event = InteractEvent.ADD

        elif ev == (self.select_mb, 'PRESS', False, False, True):
            self.is_mouse_pressed = True
            interact_event = InteractEvent.ADD_NEW_PATH

        elif ev == (self.select_mb, 'PRESS', False, True, False):
            self.is_mouse_pressed = False
            interact_event = InteractEvent.REMOVE

        elif ev in ((self.select_mb, 'RELEASE', False, False, False),
                    (self.select_mb, 'RELEASE', False, True, False),
                    (self.select_mb, 'RELEASE', False, False, True),
                    ):
            self.is_mouse_pressed = False
            interact_event = InteractEvent.RELEASE

        if self.is_mouse_pressed:
            if ev[0] == 'MOUSEMOVE':
                interact_event = InteractEvent.DRAG

        if interact_event is not None:
            elem, ob = self.get_element_by_mouse(context, event)
            self.interact_control_element(context, elem, ob, interact_event)

            self.set_selection_state(self.initial_select, True)
            self.update_meshes()

        if not len(self.path_seq):
            self.cancel(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def execute(self, context):
        tool_settings = context.scene.tool_settings
        initial_select_mode = tuple(tool_settings.mesh_select_mode)
        if initial_select_mode[0]:
            tool_settings.mesh_select_mode = (False, True, False)

        self._eval_meshes(context)

        for ob, bm in self.bm_arr:
            ptr = ob.as_pointer()

            if self.mark_select != 'NONE':
                if ptr not in self.select_only_seq:
                    print("Not found object %s in self.select_only_seq! This should never happen." % ob.name)
                else:
                    index_select_seq = self.select_only_seq[ptr]
                    elem_seq = bm.edges
                    if initial_select_mode[2]:
                        elem_seq = bm.faces
                    if self.mark_select == 'EXTEND':
                        for i in index_select_seq:
                            elem_seq[i].select_set(True)
                    elif self.mark_select == 'SUBTRACT':
                        for i in index_select_seq:
                            elem_seq[i].select_set(False)
                    elif self.mark_select == 'INVERT':
                        for i in index_select_seq:
                            elem_seq[i].select_set(not elem_seq[i].select)

            if ptr not in self.markup_seq:
                print("Not found object %s in self.markup_seq! This should never happen." % ob.name)
            else:
                index_markup_seq = self.markup_seq[ptr]
                elem_seq = bm.edges
                if self.mark_seam != 'NONE':
                    if self.mark_seam == 'MARK':
                        for i in index_markup_seq:
                            elem_seq[i].seam = True
                    elif self.mark_seam == 'CLEAR':
                        for i in index_markup_seq:
                            elem_seq[i].seam = False
                    elif self.mark_seam == 'TOGGLE':
                        for i in index_markup_seq:
                            elem_seq[i].seam = not elem_seq[i].seam

                if self.mark_sharp != 'NONE':
                    if self.mark_sharp == 'MARK':
                        for i in index_markup_seq:
                            elem_seq[i].smooth = False
                    elif self.mark_sharp == 'CLEAR':
                        for i in index_markup_seq:
                            elem_seq[i].smooth = True
                    elif self.mark_sharp == 'TOGGLE':
                        for i in index_markup_seq:
                            elem_seq[i].smooth = not elem_seq[i].smooth

        self.update_meshes()
        return {'FINISHED'}
