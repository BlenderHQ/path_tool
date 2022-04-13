import os
import enum
from typing import (Union, Iterable)
import collections

import bpy
import gpu
from gpu_extras.batch import batch_for_shader
import bgl
import bmesh

from . import shaders

_PackedEvent_T = tuple[str, str, bool, bool, bool]
_EventKey_T = Union[bpy.types.KeyMapItem, bpy.types.Event]
_ControlPoint_T = Union[bmesh.types.BMVert, bmesh.types.BMFace]
_ObjectBMesh = tuple[bpy.types.Object, bmesh.types.BMesh]


class InteractEvent(enum.Enum):
    ADD = enum.auto()
    ADD_NEW_PATH = enum.auto()
    REMOVE = enum.auto()
    DRAG = enum.auto()
    CLOSE = enum.auto()
    CHDIR = enum.auto()
    RELEASE = enum.auto()


class PathFlag(enum.IntFlag):
    CLOSE = enum.auto()
    REVERSE = enum.auto()


class Path:
    """
    Structure:

     [0]        [1]        [2]        [3]        [n]
      |  \\      |  \\      |  \\      |  \\      |
    ce_0 [...] ce_1 [...] ce_2 [...] ce_3 [...] ce_n   [...]
           |          |          |          |            |
        (fill_0)  (fill_1)   (fill_2)   (fill_3)   (fill_close)
           |          |          |          |            |
        (fba_0)    (fba_0)    (fba_0)    (fba_0)    (fba_close)

    Note:
        If elem parameter passed at instance initialization,
        will be added placeholders to fill_elements and batch_seq_fills.
    """

    __slots__ = (
        "island_index",
        "ob",
        "batch_control_elements",
        "control_elements",
        "fill_elements",
        "batch_seq_fills",
        "flag",
    )

    island_index: int
    ob: bpy.types.Object
    batch_control_elements: gpu.types.GPUBatch
    control_elements: list
    fill_elements: list
    batch_seq_fills: list[gpu.types.GPUBatch]
    flag: PathFlag

    def __init__(self, elem=None, linked_island_index=0, ob=None):
        self.island_index = linked_island_index
        self.ob = ob
        self.batch_control_elements = None

        self.control_elements = list()
        self.fill_elements = list()
        self.batch_seq_fills = list()

        if elem is not None:
            self.control_elements.append(elem)
            self.fill_elements.append([])
            self.batch_seq_fills.append(None)

        self.flag = 0

    def copy(self):
        new_path = Path()
        new_path.control_elements = self.control_elements.copy()
        new_path.fill_elements = self.fill_elements.copy()
        new_path.batch_seq_fills = self.batch_seq_fills.copy()

        new_path.batch_control_elements = self.batch_control_elements
        new_path.island_index = self.island_index
        new_path.ob = self.ob
        new_path.flag = self.flag

        return new_path

    def __repr__(self):
        # For development purposes only
        batch_seq_fills_formatted = []
        for i, batch in enumerate(self.batch_seq_fills):
            if batch:
                batch_seq_fills_formatted.append("fb_%d" % i)
                continue
            batch_seq_fills_formatted.append(batch)

        ["fb_%d" % i for i in range(len(self.batch_seq_fills))]
        return "\nPath[%d]:\n    ce: %s\n    fe: %s\n    fb: %s" % (
            id(self),
            str([n.index for n in self.control_elements]),
            str([len(n) for n in self.fill_elements]),
            str(batch_seq_fills_formatted)
        )

    def __add__(self, other):
        assert self.island_index == other.island_index

        is_found_merged_elements = False
        for i in (0, -1):
            elem = self.control_elements[i]
            for j in (0, -1):
                other_elem = other.control_elements[j]
                if elem == other_elem:
                    is_found_merged_elements = True

                    if i == -1 and j == 0:
                        # End-First
                        self.control_elements.pop(-1)
                        self.fill_elements.pop(-1)
                        self.batch_seq_fills.pop(-1)

                        self.control_elements.extend(other.control_elements)
                        self.fill_elements.extend(other.fill_elements)
                        self.batch_seq_fills.extend(other.batch_seq_fills)

                    elif i == 0 and j == -1:
                        # First-End

                        self.control_elements.pop(0)

                        other.fill_elements.pop(-1)
                        other.batch_seq_fills.pop(-1)

                        other.control_elements.extend(self.control_elements)
                        other.fill_elements.extend(self.fill_elements)
                        other.batch_seq_fills.extend(self.batch_seq_fills)

                        self.control_elements = other.control_elements
                        self.fill_elements = other.fill_elements
                        self.batch_seq_fills = other.batch_seq_fills

                    elif i == 0 and j == 0:
                        # First-First
                        self.control_elements.pop(0)

                        other.control_elements.reverse()
                        other.fill_elements.reverse()
                        other.batch_seq_fills.reverse()

                        other.fill_elements.pop(0)
                        other.batch_seq_fills.pop(0)

                        other.control_elements.extend(self.control_elements)
                        other.fill_elements.extend(self.fill_elements)
                        other.batch_seq_fills.extend(self.batch_seq_fills)

                        self.control_elements = other.control_elements
                        self.fill_elements = other.fill_elements
                        self.batch_seq_fills = other.batch_seq_fills

                    elif i == -1 and j == -1:
                        # End-End
                        other.reverse()
                        self.control_elements.pop(-1)
                        self.fill_elements.pop(-1)
                        self.batch_seq_fills.pop(-1)

                        self.control_elements.extend(other.control_elements)
                        self.fill_elements.extend(other.fill_elements)
                        self.batch_seq_fills.extend(other.batch_seq_fills)

            if is_found_merged_elements:
                break

        return self

    def reverse(self):
        self.control_elements.reverse()
        close_path_fill = self.fill_elements.pop(-1)
        close_path_batch = self.batch_seq_fills.pop(-1)
        self.fill_elements.reverse()
        self.batch_seq_fills.reverse()
        self.fill_elements.append(close_path_fill)
        self.batch_seq_fills.append(close_path_batch)

        self.flag ^= PathFlag.REVERSE

        return self

    def is_in_control_elements(self, elem):
        """
        Return's element index in self.control_elements if exist, otherwise None
        """
        if elem in self.control_elements:
            return self.control_elements.index(elem)

    def is_in_fill_elements(self, elem):
        """
        Return's index of fill in self.fill_elements if element exist in any fill, otherwise None
        """
        for fill_index, fill_seq in enumerate(self.fill_elements):
            if isinstance(elem, bmesh.types.BMVert):
                for edge in fill_seq:
                    for vert in edge.verts:
                        if elem == vert:
                            return fill_index
            elif isinstance(elem, bmesh.types.BMFace):
                if elem in fill_seq:
                    return fill_index

    def insert_control_element(self, elem_index, elem):
        """
        Insert
        - new control element
        - empty list for fill elements after this element
        - placeholder for fill batch
        """
        self.control_elements.insert(elem_index, elem)
        self.fill_elements.insert(elem_index, [])
        self.batch_seq_fills.insert(elem_index, None)

    def remove_control_element(self, elem):
        elem_index = self.control_elements.index(elem)
        self.pop_control_element(elem_index)

    def pop_control_element(self, elem_index):
        elem = self.control_elements.pop(elem_index)
        pop_index = elem_index - 1
        if elem_index == 0:
            pop_index = 0
        self.fill_elements.pop(pop_index)
        self.batch_seq_fills.pop(pop_index)
        return elem

    def get_pairs_items(self, elem_index):
        """
        Return's pairs_items list in format:
        pairs_items = [[elem_0, elem_1, fill_index_0],
                       (optional)[elem_0, elem_2, fill_index_1]]
        Used to update fill elements from and to given element
        """
        pairs_items = []
        control_elements_count = len(self.control_elements)
        if control_elements_count < 2:
            return pairs_items

        if elem_index > control_elements_count - 1:
            elem_index = control_elements_count - 1

        elem = self.control_elements[elem_index]

        if elem_index == 0:
            # First control element
            pairs_items = [[elem, self.control_elements[1], 0]]
        elif elem_index == len(self.control_elements) - 1:
            # Last control element
            pairs_items = [
                [elem, self.control_elements[elem_index - 1], elem_index - 1]]
        elif len(self.control_elements) > 2:
            # At least 3 control elements
            pairs_items = [[elem, self.control_elements[elem_index - 1], elem_index - 1],
                           [elem, self.control_elements[elem_index + 1], elem_index]]

        if (self.flag & PathFlag.CLOSE) and (control_elements_count > 2) and (elem_index in (0, control_elements_count - 1)):
            pairs_items.extend(
                [[self.control_elements[0], self.control_elements[-1], -1]])

        return pairs_items


class OPMode(enum.Enum):
    MEDGE = enum.auto()
    MFACE = enum.auto()


class MESH_OT_select_path(bpy.types.Operator):
    bl_idname = "mesh.path_tool"
    bl_label = "Path Tool"
    bl_options = {'REGISTER', 'UNDO'}

    __slots__ = (
        # Input variables.
        "select_mb",
        "pie_mb",
        "modal_events",
        "undo_redo_events",
        "nav_events",

        "bm_arr",
        "initial_select",
        "is_mouse_pressed",
        "is_navigation_active",
        "path_seq",
        "mesh_islands",
        "drag_elem_indices",
        "_active_path_index",
        "_drag_elem",
        "_just_closed_path",
        "undo_history",
        "redo_history",
        "draw_handle_3d",
        "select_only_seq",
        "markup_seq",
        "active_index",
    )

    # Input variables.
    select_mb: str
    pie_mb: str
    modal_events: dict[tuple[_PackedEvent_T], str]
    undo_redo_events: dict[tuple[_PackedEvent_T], str]
    nav_events: tuple[_PackedEvent_T]
    is_mouse_pressed: bool
    is_navigation_active: bool

    #
    bm_arr: tuple[_ObjectBMesh]
    initial_select: tuple[_ControlPoint_T]
    mesh_islands: list[tuple[_ControlPoint_T]]
    drag_elem_indices: list[bool]
    _active_path_index: int
    _drag_elem: _ControlPoint_T
    _just_closed_path: bool
    undo_history: collections.deque[tuple[int, tuple[Path]]]
    redo_history: collections.deque[tuple[int, tuple[Path]]]
    draw_handle_3d: object
    select_only_seq: dict
    markup_seq: dict
    active_index: int
    #
    path_seq: list[Path]

    context_action: bpy.props.EnumProperty(
        items=(
            ('TCLPATH', "Toggle Close Path",
             "Close the path from the first to the last control point", '', 2),
            ('CHDIR', "Change direction", "Changes the direction of the path", '', 4),
            ('APPLY', "Apply All", "Apply all paths and make changes to the mesh", '', 8),
        ),
        options={'ENUM_FLAG'},
        default=set(),
    )

    context_undo: bpy.props.EnumProperty(
        items=(
            ('UNDO', "Undo", "Undo one step", 'LOOP_BACK', 2),
            ('REDO', "Redo", "Redo one step", 'LOOP_FORWARDS', 4),
        ),
        options={'ENUM_FLAG'},
        default=set(),
    )

    mark_select: bpy.props.EnumProperty(
        items=(
            ('EXTEND', "Extend", "Extend existing selection", 'SELECT_EXTEND', 1),
            ('NONE', "Do nothing", "Do nothing", "X", 2),
            ('SUBTRACT', "Subtract", "Subtract existing selection", 'SELECT_SUBTRACT', 3),
            ('INVERT', "Invert", "Inverts existing selection", 'SELECT_DIFFERENCE', 4)
        ),
        default='EXTEND',
        name="Select",
        description="Selection options",
    )

    mark_seam: bpy.props.EnumProperty(
        items=(
            ('MARK', "Mark", "Mark seam path elements", 'RESTRICT_SELECT_OFF', 1),
            ('NONE', "Do nothing", "Do nothing", 'X', 2),
            ('CLEAR', "Clear", "Clear seam path elements", 'RESTRICT_SELECT_ON', 3),
            ('TOGGLE', "Toggle", "Toggle seams on path elements", 'ACTION_TWEAK', 4)
        ),
        default='NONE',
        name="Seams",
        description="Mark seam options",
    )

    mark_sharp: bpy.props.EnumProperty(
        items=(
            ('MARK', "Mark", "Mark sharp path elements", 'RESTRICT_SELECT_OFF', 1),
            ('NONE', "Do nothing", "Do nothing", 'X', 2),
            ('CLEAR', "Clear", "Clear sharp path elements", 'RESTRICT_SELECT_ON', 3),
            ('TOGGLE', "Toggle", "Toggle sharpness on path", 'ACTION_TWEAK', 4)
        ),
        default="NONE",
        name="Sharp",
        description="Mark sharp options",
    )

    def draw(self, _context: bpy.types.Context) -> None:
        layout = self.layout
        layout.use_property_split = True

        col = layout.column(align=True)

        col.row().prop(self, "mark_select", text="Select", icon_only=True, expand=True)
        col.row().prop(self, "mark_seam", text="Seam", icon_only=True, expand=True)
        col.row().prop(self, "mark_sharp", text="Sharp", icon_only=True, expand=True)

    def popup_menu_pie_draw(self, popup: bpy.types.UIPieMenu, context: bpy.types.Context) -> None:
        layout = popup.layout
        pie = layout.menu_pie()

        box = pie.box()

        col = box.column(align=True)

        col.row().prop(self, "mark_select", text="Select", icon_only=True, expand=True)
        col.row().prop(self, "mark_seam", text="Seam", icon_only=True, expand=True)
        col.row().prop(self, "mark_sharp", text="Sharp", icon_only=True, expand=True)

        scol = col.column()
        scol.emboss = 'NORMAL'
        row = scol.row(align=True)
        row.prop(self, "context_undo", expand=True)

        pie.prop_tabs_enum(self, "context_action")

    @staticmethod
    def _pack_event(item: _EventKey_T) -> _PackedEvent_T:
        return item.type, item.value, item.alt, item.ctrl, item.shift

    @staticmethod
    def _eval_meshes(context: bpy.types.Context) -> tuple[_ObjectBMesh]:
        ret = []
        for ob in context.objects_in_mode:
            ob: bpy.types.Object

            bm = bmesh.from_edit_mesh(ob.data)
            for elem_arr in (bm.verts, bm.edges, bm.faces):
                elem_arr.ensure_lookup_table()
            ret.append((ob, bm))
        return tuple(ret)

    @staticmethod
    def gen_batch_faces_seq(fill_seq, is_active, shader) -> tuple[gpu.types.GPUBatch, int]:
        tmp_bm = bmesh.new()
        for face in fill_seq:
            tmp_bm.faces.new((tmp_bm.verts.new(v.co, v) for v in face.verts), face)

        tmp_bm.verts.index_update()
        tmp_bm.faces.ensure_lookup_table()

        tmp_loops = tmp_bm.calc_loop_triangles()

        r_batch = batch_for_shader(shader, 'TRIS', {
            "pos": tuple((v.co for v in tmp_bm.verts))},
            indices=tuple(((loop.vert.index for loop in tri)
                          for tri in tmp_loops))
        )

        r_active_face_tri_start_index = None

        if is_active:
            r_active_face_tri_start_index = len(tmp_loops)
            tmp_bm = bmesh.new()
            face = fill_seq[-1]
            tmp_bm.faces.new((tmp_bm.verts.new(v.co, v) for v in face.verts), face)
            r_active_face_tri_start_index -= len(tmp_bm.calc_loop_triangles())

        return r_batch, r_active_face_tri_start_index

    @staticmethod
    def gen_batch_control_elements(context: bpy.types.Context, is_active, path):
        shader = shaders.shader.vert_uniform_color
        select_mode = tuple(context.scene.tool_settings.mesh_select_mode)

        r_batch = None
        r_active_elem_start_index = None

        if select_mode[1]:
            r_batch = batch_for_shader(
                shader, 'POINTS', {"pos": tuple((v.co for v in path.control_elements))})
            if is_active:
                r_active_elem_start_index = len(path.control_elements) - 1
        elif select_mode[2]:
            r_batch, r_active_elem_start_index = MESH_OT_select_path.gen_batch_faces_seq(
                path.control_elements,
                is_active,
                shader
            )

        return r_batch, r_active_elem_start_index

    @staticmethod
    def gen_batch_fill_elements(context, fill_seq):
        shader = shaders.shader.path_uniform_color
        select_mode = tuple(context.scene.tool_settings.mesh_select_mode)
        r_batch = None
        if select_mode[1]:
            pos = []
            for edge in fill_seq:
                pos.extend([vert.co for vert in edge.verts])
            r_batch = batch_for_shader(shader, 'LINES', {"pos": pos})
        elif select_mode[2]:
            r_batch, _ = MESH_OT_select_path.gen_batch_faces_seq(
                fill_seq, False, shader)

        return r_batch

    def draw_callback_3d(self, context: bpy.types.Context):
        preferences = context.preferences.addons[__package__].preferences

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

        shader_ce = shaders.shader.vert_uniform_color
        shader_path = shaders.shader.path_uniform_color

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
    def set_selection_state(elem_seq: Iterable[Union[bmesh.types.BMVert, bmesh.types.BMEdge, bmesh.types.BMFace]], state: bool = True):
        for elem in elem_seq:
            elem.select = state

    def get_selected_elements(self, mesh_elements):
        ret = tuple()
        for _, bm in self.bm_arr:
            elem_arr = getattr(bm, mesh_elements)
            ret += tuple((n for n in elem_arr if n.select))
        return ret

    def get_element_by_mouse(self, context: bpy.types.Context, event: bpy.types.Event):
        tool_settings = context.scene.tool_settings
        initial_select_mode = tuple(tool_settings.mesh_select_mode)
        # Change select mode for edges path (select verts)
        if initial_select_mode[1]:
            tool_settings.mesh_select_mode = (True, False, False)
        bpy.ops.mesh.select_all(action='DESELECT')
        mouse_location = (event.mouse_region_x, event.mouse_region_y)
        bpy.ops.view3d.select(location=mouse_location)

        elem = None
        ob = None
        for ob, bm in self.bm_arr:
            elem = bm.select_history.active
            if elem:
                break
        tool_settings.mesh_select_mode = initial_select_mode
        return elem, ob

    def get_current_state_copy(self):
        return tuple((self._active_path_index, tuple(n.copy() for n in self.path_seq)))

    def undo(self, context: bpy.types.Context):
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

    def redo(self, context: bpy.types.Context):
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

    def get_linked_island_index(self, context: bpy.types.Context, elem: _ControlPoint_T):
        for i, linked_island in enumerate(self.mesh_islands):
            if elem in linked_island:
                return i

        tool_settings = context.scene.tool_settings
        initial_select_mode = tuple(tool_settings.mesh_select_mode)

        mesh_elements = "faces"
        if initial_select_mode[1]:
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

    def update_meshes(self, _context: bpy.types.Context):
        for ob, bm in self.bm_arr:
            bm.select_flush_mode()
            bmesh.update_edit_mesh(
                mesh=ob.data, loop_triangles=False, destructive=False)

    def update_path_beetween(self, context: bpy.types.Context, elem_0: _ControlPoint_T, elem_1: _ControlPoint_T):
        tool_settings = context.scene.tool_settings
        initial_select_mode = tuple(tool_settings.mesh_select_mode)
        mesh_elements = "faces"
        # Change select mode for edges path (select verts)
        if initial_select_mode[1]:
            mesh_elements = "edges"
            tool_settings.mesh_select_mode = (True, False, False)

        bpy.ops.mesh.select_all(action='DESELECT')
        self.set_selection_state((elem_0, elem_1), True)
        bpy.ops.mesh.shortest_path_select()
        self.set_selection_state((elem_0, elem_1), False)
        r_fill_seq = self.get_selected_elements(mesh_elements)
        bpy.ops.mesh.select_all(action='DESELECT')
        # Exception if control points in one edge
        if (not r_fill_seq) and initial_select_mode[1]:
            for edge in elem_0.link_edges:
                if edge.other_vert(elem_0) == elem_1:
                    r_fill_seq = [edge]
        tool_settings.mesh_select_mode = initial_select_mode
        return r_fill_seq

    def update_fills_by_element_index(self, context: bpy.types.Context, path: Path, elem_index: int):
        pairs_items = path.get_pairs_items(elem_index)
        for item in pairs_items:
            elem_0, elem_1, fill_index = item
            fill_seq = self.update_path_beetween(context, elem_0, elem_1)

            path.fill_elements[fill_index] = fill_seq
            batch = self.gen_batch_fill_elements(context, fill_seq)
            path.batch_seq_fills[fill_index] = batch

    def gen_final_elements_seq(self, context: bpy.types.Context):
        select_mode = tuple(context.scene.tool_settings.mesh_select_mode)
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
                    index_select_seq.extend(
                        [face.index for face in path.control_elements])
                    tmp = path.fill_elements
                    tmp.append(path.control_elements)
                    for fill_seq in tmp:
                        for face in fill_seq:
                            index_markup_seq.extend(
                                [e.index for e in face.edges])
            # Remove duplicates
            self.select_only_seq[ob.as_pointer()] = list(
                dict.fromkeys(index_select_seq))
            self.markup_seq[ob.as_pointer()] = list(
                dict.fromkeys(index_markup_seq))

    def remove_path_doubles(self, context: bpy.types.Context, path: Path):
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
                                self.update_fills_by_element_index(
                                    context, path, 0)

                                message = "Closed path"
                                if path == self.active_path:
                                    self._just_closed_path = True
                                    message = "Closed active path"
                                self.report(type={'INFO'}, message=message)
                            else:
                                self.update_fills_by_element_index(
                                    context, path, 0)
                        # Adjacent control elements
                        elif i in (j - 1, j + 1):
                            path.pop_control_element(j)
                            batch, _ = self.gen_batch_control_elements(
                                context, path == self.active_path, path)
                            path.batch_control_elements = batch
                            self.report(
                                type={'INFO'}, message="Merged adjacent control elements")
                        else:
                            # Maybe, undo here?
                            pass

    def check_join_pathes(self, context: bpy.types.Context):
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

                    batch, _ = self.gen_batch_control_elements(
                        context, path == self.active_path, path)
                    path.batch_control_elements = batch
                    self.report(type={'INFO'}, message="Joined two paths")

    def interact_control_element(
            self, context: bpy.types.Context,
            elem: _ControlPoint_T,
            ob: bpy.types.Object,
            interact_event: InteractEvent) -> None:
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
                batch, self.active_index = self.gen_batch_control_elements(context, True, self.active_path)
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

                batch, self.active_index = self.gen_batch_control_elements(context, True, self.active_path)
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
                    self.update_fills_by_element_index(
                        context, self.active_path, elem_index)
                    batch, self.active_index = self.gen_batch_control_elements(context, True, self.active_path)
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
                            context,
                            path == self.active_path,
                            path)

        elif interact_event is InteractEvent.CHDIR:
            self.active_path.reverse()
            batch, self.active_index = self.gen_batch_control_elements(context, True, self.active_path)
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

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        wm = context.window_manager

        # Input keymaps:
        kc = wm.keyconfigs.user
        km_path_tool = kc.keymaps["3D View Tool: Edit Mesh, Path Tool"]
        kmi = km_path_tool.keymap_items[0]

        # Select and context pie menu mouse buttons.
        self.select_mb = kmi.type
        self.pie_mb = 'LEFTMOUSE'
        if self.select_mb == 'LEFTMOUSE':
            self.pie_mb = 'RIGHTMOUSE'

        # Operator's modal keymap.
        km_standard_modal = kc.keymaps["Standard Modal Map"]
        modal_events = dict()

        for kmi in km_standard_modal.keymap_items:
            ev = list(self._pack_event(kmi))
            ev[2:5] = (False, False, False)
            modal_events[tuple(ev)] = kmi.propvalue
        self.modal_events = modal_events

        # Operator's undo/redo keymap.
        undo_redo_events = {}
        km_screen = kc.keymaps['Screen']

        kmi = km_screen.keymap_items.find_from_operator(idname='ed.undo')
        undo_redo_events[self._pack_event(kmi)] = 'UNDO'

        kmi = km_screen.keymap_items.find_from_operator(idname='ed.redo')
        undo_redo_events[self._pack_event(kmi)] = 'REDO'
        self.undo_redo_events = undo_redo_events

        # Navigation events which would be passed through operator's modal cycle.
        km_view3d = kc.keymaps['3D View']

        nav_events = []
        for kmi in km_view3d.keymap_items:
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

        # Mesh select mode:
        tool_settings = context.scene.tool_settings
        initial_select_mode = tuple(tool_settings.mesh_select_mode)
        mesh_mode = (False, True, False)
        header_text_mode = "Edge Selection"
        if initial_select_mode[2]:
            mesh_mode = (False, False, True)
            header_text_mode = "Face Selection"
        tool_settings.mesh_select_mode = mesh_mode

        # Evaluate meshes:
        self.bm_arr = self._eval_meshes(context)

        mesh_elements = "verts"
        if initial_select_mode[2]:
            mesh_elements = "faces"

        self.initial_select = self.get_selected_elements(mesh_elements)
        self.draw_handle_3d = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_callback_3d, (context,), 'WINDOW', 'POST_VIEW'
        )

        # Prevent first click empty space
        elem, _ = self.get_element_by_mouse(context, event)
        if not elem:
            tool_settings.mesh_select_mode = initial_select_mode
            self.cancel(context)
            return {'CANCELLED'}

        self.is_mouse_pressed = False
        self.is_navigation_active = False
        # Set header and statusbar information.
        area = context.area
        area.header_text_set("Path Tool (%s)" % header_text_mode)
        workspace = context.workspace
        workspace.status_text_set(
            f"Select Mesh Element: {self.select_mb.capitalize()}; "
            f"Context Menu: {self.pie_mb.capitalize()}"
            f""
        )

        wm.modal_handler_add(self)

        self.path_seq = []
        self.mesh_islands = []
        self.drag_elem_indices = []

        self._active_path_index = None
        self._drag_elem = None
        self._just_closed_path = False

        undo_steps = context.preferences.edit.undo_steps
        self.undo_history = collections.deque(maxlen=undo_steps)
        self.redo_history = collections.deque(maxlen=undo_steps)

        self.select_only_seq = {}
        self.markup_seq = {}

        self.modal(context, event)
        return {'RUNNING_MODAL'}

    def cancel(self, context: bpy.types.Context):
        bpy.types.SpaceView3D.draw_handler_remove(
            self.draw_handle_3d, 'WINDOW')
        self.set_selection_state(self.initial_select, True)
        self.update_meshes(context)
        workspace = context.workspace
        workspace.status_text_set(text=None)
        area = context.area
        area.header_text_set(None)

    def modal(self, context: bpy.types.Context, event: bpy.types.Event):
        wm = context.window_manager
        evkey = self._pack_event(event)
        modal_action = self.modal_events.get(evkey, None)
        undo_redo_action = self.undo_redo_events.get(evkey, None)
        interact_event = None

        # Navigation
        if evkey in self.nav_events:
            return {'PASS_THROUGH'}

        elif self.is_navigation_active and event.value == 'RELEASE':
            self.is_navigation_active = False
            self.set_selection_state(self.initial_select, True)
            self.update_meshes(context)
            return {'RUNNING_MODAL'}

        # Cancel
        elif modal_action == 'CANCEL':
            self.cancel(context)
            return {'CANCELLED'}

        # Apply all
        elif (modal_action == 'APPLY') or ('APPLY' in self.context_action):
            self.context_action = set()

            self.gen_final_elements_seq(context)

            area = context.area
            area.header_text_set(None)

            workspace = context.workspace
            workspace.status_text_set(text=None)

            bpy.types.SpaceView3D.draw_handler_remove(
                self.draw_handle_3d, 'WINDOW')
            return self.execute(context)

        # Close path
        elif 'TCLPATH' in self.context_action:
            self.context_action = set()
            interact_event = InteractEvent.CLOSE

        # Switch direction
        elif 'CHDIR' in self.context_action:
            self.context_action = set()
            interact_event = InteractEvent.CHDIR

        # Undo
        elif (undo_redo_action == 'UNDO') or ('UNDO' in self.context_undo):
            self.context_undo = set()
            return self.undo(context)

        # Redo
        elif (undo_redo_action == 'REDO') or ('REDO' in self.context_undo):
            self.context_undo = set()
            self.redo(context)

        # Open context pie menu
        elif evkey == (self.pie_mb, 'PRESS', False, False, False):  # Context menu mouse button
            wm = context.window_manager
            wm.popup_menu_pie(
                event=event, draw_func=self.popup_menu_pie_draw, title='Path Tool', icon='NONE')

        # Select mouse button
        elif evkey == (self.select_mb, 'PRESS', False, False, False):
            self.is_mouse_pressed = True
            interact_event = InteractEvent.ADD

        # Select mouse button + Shift
        elif evkey == (self.select_mb, 'PRESS', False, False, True):
            self.is_mouse_pressed = True
            interact_event = InteractEvent.ADD_NEW_PATH

        # Select mouse button + Ctrl
        elif evkey == (self.select_mb, 'PRESS', False, True, False):
            self.is_mouse_pressed = False
            interact_event = InteractEvent.REMOVE

        # Release select mouse event
        elif evkey in ((self.select_mb, 'RELEASE', False, False, False),
                       (self.select_mb, 'RELEASE', False, True, False),
                       (self.select_mb, 'RELEASE', False, False, True),
                       ):
            self.is_mouse_pressed = False
            interact_event = InteractEvent.RELEASE

        if self.is_mouse_pressed:
            if evkey[0] == 'MOUSEMOVE':
                interact_event = InteractEvent.DRAG

        if interact_event is not None:
            elem, matrix_world = self.get_element_by_mouse(context, event)
            self.interact_control_element(context, elem, matrix_world, interact_event)

            self.set_selection_state(self.initial_select, True)
            self.update_meshes(context)

        # If removed the last control element of the last path
        if not len(self.path_seq):
            self.cancel(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def execute(self, context: bpy.types.Context):
        tool_settings = context.scene.tool_settings
        initial_select_mode = tuple(tool_settings.mesh_select_mode)
        if initial_select_mode[0]:
            tool_settings.mesh_select_mode = (False, True, False)

        self._eval_meshes(context)

        for ob, bm in self.bm_arr:
            ptr = ob.as_pointer()

            if self.mark_select != 'NONE':
                if ptr not in self.select_only_seq:
                    print(
                        "Not found object %s in self.select_only_seq! This should never happen." % ob.name)
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
                print(
                    "Not found object %s in self.markup_seq! This should never happen." % ob.name)
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

        self.update_meshes(context)
        return {'FINISHED'}


class PathToolMesh(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'

    bl_idname = "mesh.path_tool"
    bl_label = "Path Tool"
    bl_description = (
        "Tool for selecting and marking up\n"
        "mesh object elements"
    )
    bl_icon = os.path.join(os.path.dirname(__file__),
                           "icons", "ops.mesh.path_tool")
    bl_keymap = (
        (
            MESH_OT_select_path.bl_idname, dict(
                type='LEFTMOUSE',
                value='PRESS',
            ), None
        ),
    )

    def draw_settings(context, layout, tool):
        layout.use_property_split = True

        props = tool.operator_properties(MESH_OT_select_path.bl_idname)
