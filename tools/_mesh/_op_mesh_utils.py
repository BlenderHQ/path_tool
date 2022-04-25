import bpy
import bmesh
from gpu_extras.batch import batch_for_shader

from ..common import InteractEvent, PathFlag, Path, OPMode
from ... import bhqab


class MeshOperatorUtils:

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
                batch, _ = super(type(self), self)._gpu_gen_batch_faces_seq(fill_seq, False, shader)

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
