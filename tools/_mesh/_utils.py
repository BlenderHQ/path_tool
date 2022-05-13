from typing import Literal, Union

import bpy
from bpy.types import (
    Context,
    Event,
    UIPieMenu,
    KeyMapItem,
    Object,
    UILayout,
)

import bmesh
from bmesh.types import (
    BMesh,
    BMVert,
    BMEdge,
    BMFace
)
from gpu_extras.batch import batch_for_shader

from . import _annotations
from ..common import InteractEvent, PathFlag, Path
from ... import bhqab

HARDCODED_APPLY_KMI = ('SPACE', 'PRESS', False, False, False)
HARDCODED_CLOSE_PATH_KMI = ('C', 'PRESS', False, False, False)
HARDCODED_CHANGE_DIRECTION_KMI = ('D', 'PRESS', False, False, False)
HARDCODED_TOPOLOGY_DISTANCE_KMI = ('T', 'PRESS', False, False, False)


class MeshOperatorUtils(_annotations.MeshOperatorVariables):
    def draw_func(self, layout: UILayout) -> None:
        layout.row().prop(self, "mark_select", text="Select", icon_only=True, expand=True)
        layout.row().prop(self, "mark_seam", text="Seam", icon_only=True, expand=True)
        layout.row().prop(self, "mark_sharp", text="Sharp", icon_only=True, expand=True)

    def draw(self, _context: Context) -> None:
        self.draw_func(self.layout)

    def draw_popup_menu_pie(self, popup: UIPieMenu, context: Context) -> None:
        pie = popup.layout.menu_pie()
        pie.prop_tabs_enum(self, "context_action")
        col = pie.box().column()
        col.use_property_split = True
        self.draw_func(col)

    @staticmethod
    def draw_statusbar(self, context: Context) -> None:
        layout = self.layout
        layout: UILayout

        wm = context.window_manager

        cancel_keys = set()
        apply_keys = {HARDCODED_APPLY_KMI[0]}

        kc = wm.keyconfigs.user
        for kmi in kc.keymaps["Standard Modal Map"].keymap_items:
            kmi: KeyMapItem
            if kmi.propvalue == 'CANCEL':
                cancel_keys.add(kmi.type)
            elif kmi.propvalue == 'APPLY' and 'MOUSE' not in kmi.type:
                apply_keys.add(kmi.type)

        bhqab.utils_ui.template_input_info_kmi_from_type(layout, "Cancel", cancel_keys)
        bhqab.utils_ui.template_input_info_kmi_from_type(layout, "Apply", apply_keys)
        bhqab.utils_ui.template_input_info_kmi_from_type(layout, "Close Path", {HARDCODED_CLOSE_PATH_KMI[0]})
        bhqab.utils_ui.template_input_info_kmi_from_type(
            layout, "Change Direction", {HARDCODED_CHANGE_DIRECTION_KMI[0]}
        )
        bhqab.utils_ui.template_input_info_kmi_from_type(
            layout, "Topology Distance", {HARDCODED_TOPOLOGY_DISTANCE_KMI[0]}
        )

    @staticmethod
    def _pack_event(item: Union[KeyMapItem, Event]) -> tuple[
            Union[int, str], Union[int, str],
            Union[int, bool], Union[int, bool], Union[int, bool]]:
        return item.type, item.value, item.alt, item.ctrl, item.shift

    @staticmethod
    def _eval_meshes(context: Context) -> tuple[tuple[Object, BMesh]]:
        ret = []
        for ob in context.objects_in_mode:
            ob: Object

            bm = bmesh.from_edit_mesh(ob.data)
            for elem_arr in (bm.verts, bm.edges, bm.faces):
                elem_arr.ensure_lookup_table()
            ret.append((ob, bm))
        return tuple(ret)

    @property
    def active_path(self) -> Union[None, Path]:
        if (self._active_path_index is not None) and (self._active_path_index <= len(self.path_seq) - 1):
            return self.path_seq[self._active_path_index]

    @active_path.setter
    def active_path(self, value: Union[None, Path]) -> None:
        if value not in self.path_seq:
            self.path_seq.append(value)
        self._active_path_index = self.path_seq.index(value)

    @staticmethod
    def set_selection_state(elem_seq: tuple[Union[BMVert, BMEdge, BMFace]], state: bool = True) -> None:
        for elem in elem_seq:
            elem.select = state

    def get_element_by_mouse(self, context: Context, event: Event) -> tuple[
            Union[None, BMVert, BMEdge, BMFace], Union[None, Object]]:

        ts = context.tool_settings
        ts.mesh_select_mode = self.select_ts_msm

        bpy.ops.mesh.select_all(action='DESELECT')
        mouse_location = (event.mouse_region_x, event.mouse_region_y)
        bpy.ops.view3d.select(location=mouse_location)

        elem = None
        ob = None
        for ob, bm in self.bm_arr:
            elem = bm.select_history.active
            if elem:
                break
        ts.mesh_select_mode = self.prior_ts_msm
        return elem, ob

    def get_current_state_copy(self) -> tuple[int, tuple[Path]]:
        return tuple((self._active_path_index, tuple(n.copy() for n in self.path_seq)))

    def undo(self, context: Context) -> set[Literal['CANCELLED', 'RUNNING_MODAL']]:
        if len(self.undo_history) == 1:
            self.cancel(context)
            return {'CANCELLED'}

        elif len(self.undo_history) > 1:
            step = self.undo_history.pop()
            self.redo_history.append(step)
            undo_step_active_path_index, undo_step_path_seq = self.undo_history[-1]
            self._active_path_index = undo_step_active_path_index
            self.path_seq = list(undo_step_path_seq)
            self._just_closed_path = False

        context.area.tag_redraw()

        return {'RUNNING_MODAL'}

    def redo(self, context: Context) -> None:
        if len(self.redo_history) > 0:
            step = self.redo_history.pop()
            self.undo_history.append(step)
            undo_step_active_path_index, undo_step_path_seq = self.undo_history[-1]
            self._active_path_index = undo_step_active_path_index
            self.path_seq = undo_step_path_seq
            context.area.tag_redraw()
        else:
            self.report({'WARNING'}, message="Can not redo anymore")

    def register_undo_step(self) -> None:
        step = self.get_current_state_copy()
        self.undo_history.append(step)
        self.redo_history.clear()

    def get_linked_island_index(self, context: Context, elem: Union[BMVert, BMFace]) -> int:
        ts = context.tool_settings

        for i, linked_island in enumerate(self.mesh_islands):
            if elem in linked_island:
                return i

        ts.mesh_select_mode = self.select_ts_msm

        bpy.ops.mesh.select_all(action='DESELECT')
        elem.select_set(True)
        bpy.ops.mesh.select_linked(delimit={'NORMAL'})

        linked_island = self.get_selected_elements(self.select_mesh_elements)

        ts.mesh_select_mode = self.prior_ts_msm

        bpy.ops.mesh.select_all(action='DESELECT')
        self.mesh_islands.append(linked_island)
        return len(self.mesh_islands) - 1

    def update_meshes(self) -> None:
        for ob, bm in self.bm_arr:
            bm.select_flush_mode()
            bmesh.update_edit_mesh(mesh=ob.data, loop_triangles=False, destructive=False)

    def update_fills_by_element_index(self, context: Context, path: Path, elem_index: int) -> None:
        ts = context.tool_settings

        pairs_items = path.get_pairs_items(elem_index)
        for item in pairs_items:
            elem_0, elem_1, fill_index = item

            ts.mesh_select_mode = self.select_ts_msm

            bpy.ops.mesh.select_all(action='DESELECT')
            self.set_selection_state((elem_0, elem_1), True)
            bpy.ops.mesh.shortest_path_select(use_topology_distance=bool(path.flag & PathFlag.TOPOLOGY))
            self.set_selection_state((elem_0, elem_1), False)
            fill_seq = self.get_selected_elements(self.prior_mesh_elements)
            bpy.ops.mesh.select_all(action='DESELECT')

            # Exception if control points in one edge
            if (not fill_seq) and isinstance(elem_0, BMVert):
                for edge in elem_0.link_edges:
                    edge: BMEdge
                    if edge.other_vert(elem_0) == elem_1:
                        fill_seq = tuple((edge,))

            ts.mesh_select_mode = self.prior_ts_msm

            path.fill_elements[fill_index] = fill_seq

            shader = bhqab.gpu_extras.shader.path_uniform_color
            batch = None
            if self.prior_ts_msm[1]:  # Edge mesh select mode
                pos = []
                for edge in fill_seq:
                    pos.extend([vert.co for vert in edge.verts])
                batch = batch_for_shader(shader, 'LINES', {"pos": pos})

            elif self.prior_ts_msm[2]:  # Faces mesh select mode
                batch, _ = super(type(self), self)._gpu_gen_batch_faces_seq(fill_seq, False, shader)

            path.batch_seq_fills[fill_index] = batch

    def gen_final_elements_seq(self, context: Context) -> None:
        self.select_only_seq = {}
        self.markup_seq = {}

        for ob in context.objects_in_mode:
            ob: Object

            index_select_seq = []
            index_markup_seq = []

            for path in self.path_seq:
                if path.ob != ob:
                    continue
                for fill_seq in path.fill_elements:
                    index_select_seq.extend([n.index for n in fill_seq])
                if self.prior_ts_msm:  # Edges mesh select mode
                    index_markup_seq = index_select_seq
                if self.prior_ts_msm[2]:  # Faces mesh select mode
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

    def remove_path_doubles(self, context: Context, path: Path) -> None:
        for i, control_element in enumerate(path.control_elements):
            if path.control_elements.count(control_element) > 1:
                for j, other_control_element in enumerate(path.control_elements):
                    if i == j:  # Skip current control element
                        continue
                    if other_control_element == control_element:
                        # First-last control element same path
                        if i == 0 and j == len(path.control_elements) - 1:
                            path.pop_control_element(-1)
                            if (path.flag ^ PathFlag.CLOSED):
                                path.flag |= PathFlag.CLOSED
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

    def check_join_pathes(self) -> None:
        for i, path in enumerate(self.path_seq):
            for other_path in self.path_seq:
                if path == other_path:
                    continue

                # Join two pathes
                if (((path.flag ^ PathFlag.CLOSED and other_path.flag ^ PathFlag.CLOSED)) and ((
                    path.control_elements[0] == other_path.control_elements[0])
                    or (path.control_elements[-1] == other_path.control_elements[-1])
                    or (path.control_elements[-1] == other_path.control_elements[0])
                    or (path.control_elements[0] == other_path.control_elements[-1])
                )):
                    path += other_path
                    self.path_seq.remove(other_path)
                    self._active_path_index = i

                    batch, _ = self.gen_batch_control_elements(path == self.active_path, path)
                    path.batch_control_elements = batch
                    self.report(type={'INFO'}, message="Joined two paths")

    def get_selected_elements(self, mesh_elements: str) -> tuple[Union[BMVert, BMEdge, BMFace]]:
        ret = tuple()

        for _, bm in self.bm_arr:
            elem_arr = getattr(bm, mesh_elements)
            ret += tuple((n for n in elem_arr if n.select))
        return ret

    def interact_control_element(self,
                                 context: Context,
                                 elem: Union[None, BMVert, BMFace],
                                 ob: Object,
                                 interact_event: InteractEvent) -> None:
        if elem and interact_event is InteractEvent.ADD_CP:
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
                            self.interact_control_element(context, elem, ob, InteractEvent.ADD_CP)
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
            self.interact_control_element(context, elem, ob, InteractEvent.ADD_CP)
            self.report(type={'INFO'}, message="Created new path")
            return

        elif elem and interact_event is InteractEvent.REMOVE_CP:
            self._just_closed_path = False

            elem_index = self.active_path.is_in_control_elements(elem)
            if elem_index is None:
                for path in self.path_seq:
                    other_elem_index = path.is_in_control_elements(elem)
                    if other_elem_index is not None:
                        self.active_path = path
                        self.interact_control_element(context, elem, ob, InteractEvent.REMOVE_CP)
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

        elif elem and interact_event is InteractEvent.DRAG_CP:
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

        elif interact_event is InteractEvent.CHANGE_DIRECTION:
            self.active_path.reverse()
            batch, self.active_index = self.gen_batch_control_elements(True, self.active_path)
            self.active_path.batch_control_elements = batch
            self._just_closed_path = False

        elif interact_event is InteractEvent.CLOSE_PATH:
            self.active_path.flag ^= PathFlag.CLOSED

            if self.active_path.flag & PathFlag.CLOSED:
                self.update_fills_by_element_index(context, self.active_path, 0)
                if len(self.active_path.control_elements) > 2:
                    self._just_closed_path = True
            else:
                self.active_path.fill_elements[-1] = []
                self.active_path.batch_seq_fills[-1] = None
                self._just_closed_path = False
                self.check_join_pathes()

        elif interact_event is InteractEvent.TOPOLOGY_DISTANCE:
            self.active_path.flag ^= PathFlag.TOPOLOGY
            for j in range(0, len(self.active_path.control_elements), 2):
                self.update_fills_by_element_index(context, self.active_path, j)

        elif interact_event is InteractEvent.RELEASE_PATH:
            self.drag_elem_indices = []
            self._drag_elem = None

            for path in self.path_seq:
                self.remove_path_doubles(context, path)
            self.check_join_pathes()

            self.register_undo_step()
