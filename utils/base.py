if "bpy" in locals():
    import importlib

    if "unified_path" in locals():
        importlib.reload(unified_path)
    if "draw" in locals():
        importlib.reload(draw)
    if "redo" in locals():
        importlib.reload(redo)

from enum import Enum

import bpy
import bmesh
from mathutils import Vector

from . import unified_path
from . import draw
from . import redo

Path = unified_path.Path


class InteractEvent(Enum):
    """Control element interaction mode"""
    ADD = 1
    ADD_NEW_PATH = 2
    REMOVE = 3
    DRAG = 6
    CLOSE = 7
    CHDIR = 8
    RELEASE = 9


class PathUtils:
    @property
    def active_path(self):
        if (self._active_path_index is not None) and (self._active_path_index <= len(self.path_seq) - 1):
            return self.path_seq[self._active_path_index]

    @active_path.setter
    def active_path(self, value: Path):
        if value not in self.path_seq:
            self.path_seq.append(value)
        self._active_path_index = self.path_seq.index(value)

    @staticmethod
    def set_selection_state(elem_seq, state=True):
        for elem in elem_seq:
            elem.select = state

    def get_selected_elements(self, mesh_elements):
        selected_elements = []
        for _, bm in self.bm_seq:
            selected_elements.extend([n for n in getattr(bm, mesh_elements) if n.select])
        return selected_elements

    def gen_bmeshes(self, context):
        # Bmesh (bpy.types.Object - bmesh.Bmesh) pairs
        self.bm_seq = []
        for ob in context.objects_in_mode:
            bm = bmesh.from_edit_mesh(ob.data)
            for elem_seq in (bm.verts, bm.edges, bm.faces):
                elem_seq.ensure_lookup_table()
            self.bm_seq.append((ob, bm))

    def get_element_by_mouse(self, context, event):
        """Methon for element selection by mouse.
        For edges are selected verts (they used as control elements), for faces selected faces
        Return's tuple (BMElement, bpy.types.Object)"""
        tool_settings = context.scene.tool_settings
        initial_select_mode = tuple(tool_settings.mesh_select_mode)
        if initial_select_mode[1]:  # Change select mode for edges path (select verts)
            tool_settings.mesh_select_mode = (True, False, False)
        bpy.ops.mesh.select_all(action='DESELECT')
        mouse_location = (event.mouse_region_x, event.mouse_region_y)
        bpy.ops.view3d.select(location=mouse_location)

        elem = None
        ob = None
        for ob, bm in self.bm_seq:
            elem = bm.select_history.active
            if elem:
                break
        tool_settings.mesh_select_mode = initial_select_mode
        return elem, ob

    def get_linked_island_index(self, context, elem):
        for i, linked_island in enumerate(self.mesh_islands):
            if elem in linked_island:
                return i

        tool_settings = context.scene.tool_settings
        initial_select_mode = tuple(tool_settings.mesh_select_mode)

        # https://developer.blender.org/T75128 (Resolved)

        mesh_elements = "faces"
        if initial_select_mode[1]:  # Change select mode for edges path (select verts)
            mesh_elements = "verts"
            tool_settings.mesh_select_mode = (True, False, False)

        bpy.ops.mesh.select_all(action='DESELECT')
        elem.select_set(True)
        bpy.ops.mesh.select_linked(delimit={'NORMAL'})
        linked_island = self.get_selected_elements(mesh_elements)
        tool_settings.mesh_select_mode = initial_select_mode
        bpy.ops.mesh.select_all(action='DESELECT')
        self.mesh_islands.append(linked_island)
        return len(self.mesh_islands) - 1

    def update_meshes(self, context):
        for ob, bm in self.bm_seq:
            bm.select_flush_mode()
            bmesh.update_edit_mesh(ob.data, False, False)

    def update_path_beetween(self, context, elem_0, elem_1):
        tool_settings = context.scene.tool_settings
        initial_select_mode = tuple(tool_settings.mesh_select_mode)
        mesh_elements = "faces"
        if initial_select_mode[1]:  # Change select mode for edges path (select verts)
            mesh_elements = "edges"
            tool_settings.mesh_select_mode = (True, False, False)

        bpy.ops.mesh.select_all(action='DESELECT')
        self.set_selection_state((elem_0, elem_1), True)
        bpy.ops.mesh.shortest_path_select()
        self.set_selection_state((elem_0, elem_1), False)
        fill_seq = self.get_selected_elements(mesh_elements)
        bpy.ops.mesh.select_all(action='DESELECT')
        # Exception if control points in one edge
        if (not fill_seq) and initial_select_mode[1]:
            for edge in elem_0.link_edges:
                if edge.other_vert(elem_0) == elem_1:
                    fill_seq = [edge]
        tool_settings.mesh_select_mode = initial_select_mode
        return fill_seq

    def update_fills_by_element_index(self, context, path, elem_index):
        pairs_items = path.get_pairs_items(elem_index)
        for item in pairs_items:
            elem_0, elem_1, fill_index = item
            fill_seq = self.update_path_beetween(context, elem_0, elem_1)

            path.fill_elements[fill_index] = fill_seq
            batch = draw.gen_batch_fill_elements(context, fill_seq)
            path.batch_seq_fills[fill_index] = batch

    def gen_final_elements_seq(self, context):
        tool_settings = context.scene.tool_settings
        select_mode = tuple(tool_settings.mesh_select_mode)
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
                if select_mode[1]:  # Edges
                    index_markup_seq = index_select_seq
                if select_mode[2]:  # Faces
                    # For face selection mode control elements are required too
                    index_select_seq.extend([face.index for face in path.control_elements])
                    tmp = path.fill_elements
                    tmp.append(path.control_elements)
                    for fill_seq in tmp:
                        for face in fill_seq:
                            index_markup_seq.extend([e.index for e in face.edges])
            # Remove duplicates
            self.select_only_seq[ob.as_pointer()] = list(dict.fromkeys(index_select_seq))
            self.markup_seq[ob.as_pointer()] = list(dict.fromkeys(index_markup_seq))

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
                            if not path.close:
                                path.close = True
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
                            batch, _ = draw.gen_batch_control_elements(context, path == self.active_path, path)  # Draw
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
                    (not path.close) and (not other_path.close) and
                    (
                        (path.control_elements[0] == other_path.control_elements[0]) or
                        (path.control_elements[-1] == other_path.control_elements[-1]) or
                        (path.control_elements[-1] == other_path.control_elements[0]) or
                        (path.control_elements[0] == other_path.control_elements[-1])
                    )
                ):
                    path += other_path
                    self.path_seq.remove(other_path)
                    self._active_path_index = i

                    batch, _ = draw.gen_batch_control_elements(context, path == self.active_path, path)  # Draw
                    path.batch_control_elements = batch
                    self.report(type={'INFO'}, message="Joined two paths")

    def interact_control_element(self, context, elem, ob, interact_event):
        """Main method of interacting with all pathes"""
        if elem and interact_event is InteractEvent.ADD:
            # Only the first click
            if not self.path_seq:
                self.interact_control_element(context, elem, ob, InteractEvent.ADD_NEW_PATH)
                return

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
                batch, self.active_index = draw.gen_batch_control_elements(context, True, self.active_path)  # Draw
                self.active_path.batch_control_elements = batch

            if elem_index is not None:
                self.drag_elem_indices = [path.is_in_control_elements(elem) for path in self.path_seq]
                self._just_closed_path = False
            self._drag_elem = elem

            if self._just_closed_path:
                self.interact_control_element(context, elem, ob, InteractEvent.ADD_NEW_PATH)
                return

            if new_elem_index is not None:
                # Add a new control element to active path
                linked_island_index = self.get_linked_island_index(context, elem)
                if self.active_path.island_index != linked_island_index:
                    self.interact_control_element(context, elem, ob, InteractEvent.ADD_NEW_PATH)
                    return

                self.active_path.insert_control_element(new_elem_index, elem)
                self.update_fills_by_element_index(context, self.active_path, new_elem_index)

                batch, self.active_index = draw.gen_batch_control_elements(context, True, self.active_path)  # Draw
                self.active_path.batch_control_elements = batch

                self.drag_elem_indices = [path.is_in_control_elements(elem) for path in self.path_seq]

        elif elem and interact_event is InteractEvent.ADD_NEW_PATH:
            # Adding new path
            linked_island_index = self.get_linked_island_index(context, elem)
            self.active_path = Path(elem, linked_island_index, ob)
            # Recursion used to add new control element to newly created path
            self._just_closed_path = False
            self.interact_control_element(context, elem, ob, InteractEvent.ADD)
            self.report(type={'INFO'}, message="Created new path")
            return

        elif elem and interact_event is InteractEvent.REMOVE:
            # Remove control element
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

                # Remove the last control element from path
                if not len(self.active_path.control_elements):
                    self.path_seq.remove(self.active_path)
                    if len(self.path_seq):
                        self.active_path = self.path_seq[-1]
                else:
                    self.update_fills_by_element_index(context, self.active_path, elem_index)
                    batch, self.active_index = draw.gen_batch_control_elements(context, True, self.active_path)  # Draw
                    self.active_path.batch_control_elements = batch

        elif elem and interact_event is InteractEvent.DRAG:
            # Drag control element
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
                        batch, self.active_index = draw.gen_batch_control_elements(
                            context, path == self.active_path, path)  # Draw
                        path.batch_control_elements = batch

        # Switch active path direction
        elif interact_event is InteractEvent.CHDIR:
            self.active_path.reverse()
            batch, self.active_index = draw.gen_batch_control_elements(context, True, self.active_path)  # Draw
            self.active_path.batch_control_elements = batch
            self._just_closed_path = False

        # Close active path
        elif interact_event is InteractEvent.CLOSE:
            self.active_path.close = not self.active_path.close

            if self.active_path.close:
                self.update_fills_by_element_index(context, self.active_path, 0)
                if len(self.active_path.control_elements) > 2:
                    self._just_closed_path = True
            else:
                self.active_path.fill_elements[-1] = []
                self.active_path.batch_seq_fills[-1] = None
                self._just_closed_path = False
                self.check_join_pathes(context)

        # Release interact event event
        elif interact_event is InteractEvent.RELEASE:
            self.drag_elem_indices = []
            self._drag_elem = None

            # Remove doubles from every existing path
            for path in self.path_seq:
                self.remove_path_doubles(context, path)
            # Join any end-end pathes
            self.check_join_pathes(context)

            # # Register current state after adding new, dragging or removing control elements, pathes
            # # or when toggle open/close path or changed path direction
            redo.register_undo_step(self)

        # Uncomment line to see formatted path in the console
        # print(self.active_path)
