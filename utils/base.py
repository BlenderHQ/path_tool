from collections import deque
from enum import Enum

import bpy
import bmesh

from . import path

if "_rc" in locals():
    import importlib
    importlib.reload(path)

_rc = None

Path = path.Path


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

    def __init__(self):
        self.path_seq = []
        self.mesh_islands = []
        self.drag_elem = None

        self._active_path_index = None

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

    def get_element_by_mouse(self, context, event):
        """Methon for element selection by mouse.
        For edges are selected verts (they used as control elements), for faces selected faces
        Return's tuple (BMElement, bpy.types.Object.matrix_world)"""
        tool_settings = context.scene.tool_settings

        initial_select_mode = tuple(tool_settings.mesh_select_mode)
        if initial_select_mode[1]:  # Change select mode for edges path (select verts)
            tool_settings.mesh_select_mode = (True, False, False)

        bpy.ops.mesh.select_all(action='DESELECT')

        mouse_location = (event.mouse_region_x, event.mouse_region_y)
        bpy.ops.view3d.select(location=mouse_location)

        elem = None
        matrix_world = None

        for ob, bm in self.bm_seq:
            elem = bm.select_history.active
            if elem:
                matrix_world = ob.matrix_world
                break
        tool_settings.mesh_select_mode = initial_select_mode
        bpy.ops.mesh.select_all(action='DESELECT')  # ---------
        return elem, matrix_world

    def get_linked_island_index(self, context, elem):
        for i, linked_island in enumerate(self.mesh_islands):
            if elem in linked_island:
                return i

        tool_settings = context.scene.tool_settings
        initial_select_mode = tuple(tool_settings.mesh_select_mode)
        mesh_elements = "faces"
        if initial_select_mode[1]:  # Change select mode for edges path (select verts)
            mesh_elements = "verts"
            tool_settings.mesh_select_mode = (True, False, False)

        bpy.ops.mesh.select_all(action='DESELECT')
        elem.select_set(True)
        bpy.ops.mesh.select_linked(delimit={'SEAM'})
        linked_island = self.get_selected_elements(mesh_elements)
        tool_settings.mesh_select_mode = initial_select_mode
        bpy.ops.mesh.select_all(action='DESELECT')
        self.mesh_islands.append(linked_island)
        return len(self.mesh_islands) - 1

    def update_meshes(self, context):
        for ob, bm in self.bm_seq:
            bm.select_flush_mode()
        for ob in context.objects_in_mode:
            bmesh.update_edit_mesh(ob.data, False, False)

    def get_path_by_control_element(self, elem):
        for path in self.path_seq:
            if elem in path.control_elements:
                return path

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

    def update_fills_by_element(self, context, elem):
        pairs_items = self.active_path.get_pairs_items(elem)
        for item in pairs_items:
            elem_0, elem_1, fill_index = item
            fill_seq = self.update_path_beetween(context, elem_0, elem_1)

            self.active_path.fill_elements[fill_index] = fill_seq
            batch = self.gen_batch_fill_elements(context, fill_seq)
            self.active_path.batch_seq_fills[fill_index] = batch

    def interact_control_element(self, context, elem, matrix_world, interact_event):
        if interact_event is InteractEvent.ADD:
            # Only the first click
            if not self.path_seq:
                self.interact_control_element(context, elem, matrix_world, InteractEvent.ADD_NEW_PATH)
                return

            # Check is element in any existing path, if so - make this path active
            existing_path = self.get_path_by_control_element(elem)
            if existing_path:
                self.active_path = existing_path

            if elem not in self.active_path.control_elements:
                # Check mesh island before appending new control element to active path
                linked_island_index = self.get_linked_island_index(context, elem)
                if self.active_path.island_index != linked_island_index:
                    self.interact_control_element(context, elem, matrix_world, InteractEvent.ADD_NEW_PATH)
                    return
                new_elem_index = len(self.active_path.control_elements)
                # Add a new control element to active path
                self.active_path.insert_control_element(new_elem_index, elem)
                self.update_fills_by_element(context, elem)

            batch = self.gen_batch_control_elements(context, self.active_path)  # Draw
            self.active_path.batch_control_elements = batch

            self.drag_elem = elem  # Before mouse released element can be dragged

        elif interact_event is InteractEvent.ADD_NEW_PATH:
            # Adding new path
            linked_island_index = self.get_linked_island_index(context, elem)
            self.active_path = Path(elem, linked_island_index, matrix_world)
            # Recursion used to add new control element to newly created path
            self.interact_control_element(context, elem, matrix_world, InteractEvent.ADD)
            return

        elif interact_event is InteractEvent.REMOVE:
            # Remove control element
            existing_path = self.get_path_by_control_element(elem)
            if existing_path:
                self.active_path = existing_path
                self.active_path.remove_control_element(elem)

                # Remove the last control element from path
                if not len(self.active_path.control_elements):
                    self.path_seq.remove(self.active_path)
                    if len(self.path_seq):
                        self.active_path = self.path_seq[-1]

                batch = self.gen_batch_control_elements(context, self.active_path)  # Draw
                self.active_path.batch_control_elements = batch

        elif interact_event is InteractEvent.DRAG:
            # Drag control element
            if not self.drag_elem:
                return
            linked_island_index = self.get_linked_island_index(context, elem)
            if self.active_path.island_index == linked_island_index:
                drag_elem_index = self.active_path.control_elements.index(self.drag_elem)
                self.active_path.control_elements[drag_elem_index] = elem
                self.drag_elem = elem
                self.update_fills_by_element(context, elem)
                batch = self.gen_batch_control_elements(context, self.active_path)  # Draw
                self.active_path.batch_control_elements = batch

        # Switch active path direction
        elif interact_event is InteractEvent.CHDIR:
            self.active_path.reverse()

        # Close active path
        elif interact_event is InteractEvent.CLOSE:
            self.active_path

            # Release interact event event
        elif interact_event is InteractEvent.RELEASE:
            self.drag_elem = None

            # Check and handle duplicated control elements
            non_doubles = []
            for path in self.path_seq:
                for i, control_element in enumerate(path.control_elements):
                    if control_element in non_doubles:
                        continue
                    for other_path in self.path_seq:
                        doubles_count = other_path.control_elements.count(control_element)

                        if other_path == path:
                            if doubles_count > 1:  # Double same path
                                for j, other_control_element in enumerate(path.control_elements):
                                    if i == j:  # Skip current control element
                                        continue
                                    if other_control_element == control_element:
                                        # First-last control element same path
                                        if i == 0 and j == len(path.control_elements) - 1:
                                            self.report(type={'INFO'}, message="Closed active path")
                                        else:
                                            print("Same path. Not interesting moment. just undo here")
                        elif doubles_count >= 1:  # Double different path
                            for j, other_control_element in enumerate(other_path.control_elements):
                                if other_control_element == control_element:
                                    # Endpoint control element different path
                                    if ((i in (0, len(path.control_elements) - 1)) and
                                            (j in (0, len(other_path.control_elements) - 1))):
                                        path += other_path
                                        self.path_seq.remove(other_path)
                                        self.active_path = path
                                        batch = self.gen_batch_control_elements(context, self.active_path)  # Draw
                                        self.active_path.batch_control_elements = batch
                                        self.report(type={'INFO'}, message="Joined two paths")
                        else:
                            non_doubles.append(control_element)
        print(self.active_path)
