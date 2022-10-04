from __future__ import annotations

import os
from typing import Literal
import collections
from enum import auto, IntFlag

import bpy
from bpy.types import (
    Area,
    Context,
    Event,
    KeyMapItem,
    Object,
    Object,
    Operator,
    Region,
    RegionView3D,
    SpaceView3D,
    STATUSBAR_HT_header,
    UILayout,
    UIPieMenu,
    Window,
)

import bmesh
from bmesh.types import (
    BMEdge,
    BMesh,
    BMFace,
    BMVert,
)
import gpu
from gpu.types import GPUBatch
from gpu_extras.batch import batch_for_shader

from .lib import bhqab

from . import __package__ as addon_pkg

HARDCODED_APPLY_KMI = ('SPACE', 'PRESS', False, False, False)
HARDCODED_CLOSE_PATH_KMI = ('C', 'PRESS', False, False, False)
HARDCODED_CHANGE_DIRECTION_KMI = ('D', 'PRESS', False, False, False)
HARDCODED_TOPOLOGY_DISTANCE_KMI = ('T', 'PRESS', False, False, False)

# _____________________________________________________
# TODO: Move to `bhqab`?
_REGION_VIEW_3D_N_PANEL_TABS_WIDTH_PX = 21


def eval_view3d_n_panel_width(context: Context) -> int:
    return _REGION_VIEW_3D_N_PANEL_TABS_WIDTH_PX * context.preferences.view.ui_scale

# _____________________________________________________


class InteractEvent(IntFlag):
    ADD_CP = auto()
    "Add new control point"

    ADD_NEW_PATH = auto()
    "Add new path"

    REMOVE_CP = auto()
    "Remove control point"

    DRAG_CP = auto()
    "Drag control point"

    CLOSE_PATH = auto()
    "Close path"

    CHANGE_DIRECTION = auto()
    "Switch path direction"

    TOPOLOGY_DISTANCE = auto()
    "Use topology distance"

    RELEASE_PATH = auto()
    "Release path"

    UNDO = auto()
    "Undo last event"

    REDO = auto()
    "Redo last event"

    APPLY_PATHES = auto()
    "Apply all pathes"

    CANCEL = auto()
    "Cancel"


class PathFlag(IntFlag):
    CLOSED = auto()
    "Controls filament between first and last control point of path"

    REVERSED = auto()
    "Controls path direction due to initial control point order"

    TOPOLOGY = auto()
    "Path uses topology distance operator method"


_PackedEvent_T = tuple[int | str, int | str, int | bool, int | bool, int | bool]


class Path:
    """
     [0]        [1]        [2]        [3]        [n]
      |  \\      |  \\      |  \\      |  \\      |
    ce_0 [...] ce_1 [...] ce_2 [...] ce_3 [...] ce_n   [...]
           |          |          |          |            |
        (fill_0)  (fill_1)   (fill_2)   (fill_3)   (fill_close)
           |          |          |          |            |
        (fba_0)    (fba_0)    (fba_0)    (fba_0)    (fba_close)

    Note:
        If elem parameter passed at instance initialization, will be added placeholders to `fill_elements` and
        `batch_seq_fills`.
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
    ob: Object
    batch_control_elements: None | GPUBatch
    control_elements: list[BMVert | BMFace]
    fill_elements: list[list[BMEdge | BMFace]]
    batch_seq_fills: list[GPUBatch]
    flag: PathFlag

    def __init__(self,
                 elem: None | BMVert | BMFace = None,
                 linked_island_index: int = 0,
                 ob: None | Object = None) -> None:

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

        self.flag = PathFlag(0)

    def __repr__(self):
        # NOTE: For dev purposes only
        batch_seq_fills_formatted = []
        for i, batch in enumerate(self.batch_seq_fills):
            if batch:
                batch_seq_fills_formatted.append("fb_%d" % i)
                continue
            batch_seq_fills_formatted.append(batch)

        ["fb_%d" % i for i in range(len(self.batch_seq_fills))]
        return "\nPath [id:%d]:\n    ce: %s\n    fe: %s\n    fb: %s" % (
            id(self),
            str([n.index for n in self.control_elements]),
            str([len(n) for n in self.fill_elements]),
            str(batch_seq_fills_formatted)
        )

    def copy(self) -> Path:
        new_path = Path()
        new_path.control_elements = self.control_elements.copy()
        new_path.fill_elements = self.fill_elements.copy()
        new_path.batch_seq_fills = self.batch_seq_fills.copy()

        new_path.batch_control_elements = self.batch_control_elements
        new_path.island_index = self.island_index
        new_path.ob = self.ob
        new_path.flag = self.flag

        return new_path

    def reverse(self) -> Path:
        self.control_elements.reverse()
        close_path_fill = self.fill_elements.pop(-1)
        close_path_batch = self.batch_seq_fills.pop(-1)
        self.fill_elements.reverse()
        self.batch_seq_fills.reverse()
        self.fill_elements.append(close_path_fill)
        self.batch_seq_fills.append(close_path_batch)

        self.flag ^= PathFlag.REVERSED

        return self

    def is_in_control_elements(self, elem: BMVert | BMFace) -> None | int:
        if elem in self.control_elements:
            return self.control_elements.index(elem)

    def is_in_fill_elements(self, elem: BMVert | BMFace) -> None | int:
        if isinstance(elem, BMVert):
            for i, arr in enumerate(self.fill_elements):
                arr: list[BMEdge]

                for edge in arr:
                    edge: BMEdge

                    for vert in edge.verts:
                        vert: BMVert
                        if elem == vert:
                            return i
                del arr

        # elif isinstance(elem, BMFace):
        for i, arr in enumerate(self.fill_elements):
            arr: list[BMFace]

            if elem in arr:
                return i

    def insert_control_element(self, elem_index, elem):
        self.control_elements.insert(elem_index, elem)
        self.fill_elements.insert(elem_index, [])
        self.batch_seq_fills.insert(elem_index, None)

    def remove_control_element(self, elem) -> None:
        elem_index = self.control_elements.index(elem)
        self.pop_control_element(elem_index)

    def pop_control_element(self, elem_index: int) -> BMVert | BMFace:
        elem = self.control_elements.pop(elem_index)
        pop_index = elem_index - 1
        if elem_index == 0:
            pop_index = 0
        self.fill_elements.pop(pop_index)
        self.batch_seq_fills.pop(pop_index)
        return elem

    def get_pairs_items(self, elem_index):
        r_pairs = list()

        num_ce = len(self.control_elements)
        if num_ce < 2:
            return r_pairs

        if elem_index > num_ce - 1:
            elem_index = num_ce - 1

        elem = self.control_elements[elem_index]

        if elem_index == 0:
            r_pairs = [[elem, self.control_elements[1], 0]]

        elif elem_index == len(self.control_elements) - 1:
            r_pairs = [[elem, self.control_elements[elem_index - 1], elem_index - 1]]

        elif len(self.control_elements) > 2:
            r_pairs = [[elem, self.control_elements[elem_index - 1], elem_index - 1],
                       [elem, self.control_elements[elem_index + 1], elem_index]]

        if ((self.flag & PathFlag.CLOSED)
                and (num_ce > 2)
                and (elem_index in (0, num_ce - 1))):
            r_pairs.extend([[self.control_elements[0], self.control_elements[-1], -1]])

        return r_pairs


# NOTE: Keep items display names length for visual symmetry.
# UI layout of pie-menu is next:
# -------------------------------------------
# |                 Apply                   |
# |        Undo                Redo         |
# | Direction         O          Close Path |
# |    Topology                Options      |
# |                 Cancel                  |
# -------------------------------------------
_context_action_items = (
    # West
    (
        InteractEvent.CHANGE_DIRECTION.name,
        "Direction",
        ("Change the direction of the active path.\n"
         "The active element of the path will be the final element "
         "from the opposite end of the path, from it will be formed a section to the next control element that "
         "you create."),
        'NONE',  # 'CON_CHILDOF',
        InteractEvent.CHANGE_DIRECTION.value,
    ),
    # *** East ***
    (
        InteractEvent.CLOSE_PATH.name,
        "Close Path",
        "Connect between the beginning and end of the active path",
        'NONE',  # 'MESH_CIRCLE',
        InteractEvent.CLOSE_PATH.value,
    ),
    # *** South ***
    (
        InteractEvent.CANCEL.name,
        "Cancel",
        "Cancel editing pathes",
        'EVENT_ESC',
        InteractEvent.CANCEL.value,
    ),
    # *** North ***
    (
        InteractEvent.APPLY_PATHES.name,
        "Apply",  # 5 chars
        "Apply the created mesh paths according to the selected options",
        'EVENT_RETURN',
        InteractEvent.APPLY_PATHES.value,
    ),
    # *** North-East ***
    (
        InteractEvent.UNDO.name,
        "Undo",
        "Take a step back",
        'LOOP_BACK',
        InteractEvent.UNDO.value,
    ),
    # *** North-West ***
    (
        InteractEvent.REDO.name,
        "Redo",
        "Redo previous undo",
        'LOOP_FORWARDS',
        InteractEvent.REDO.value,
    ),
    # *** South-West ***
    (
        InteractEvent.TOPOLOGY_DISTANCE.name,
        "Topology",
        ("Algorithm for calculating the path: simple or using a mesh topology"
         "(Find the minimum number of steps, ignoring spatial distance)"),
        'NONE',  # 'DRIVER_DISTANCE',
        InteractEvent.TOPOLOGY_DISTANCE.value,
    ),
    # *** South-East *** - reserved for "Options" panel (MESH_PT_select_path_context)
)


class MESH_PT_select_path_context(bpy.types.Panel):
    bl_label = "Options"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'

    def draw(cls, context: Context) -> None:
        layout = cls.layout
        layout.use_property_split = True
        props = context.window_manager.select_path
        props.ui_draw_func_runtime(layout)


def __validate_context_action_items_display_symmetry_concept(bias: int = 1):
    W, E, S, N, NE, NW, SW = (_[1] for _ in _context_action_items)
    SE = MESH_PT_select_path_context.bl_label

    len_cmp_order = {
        "West <> East (important!)": (W, E),
        "North <> South (important!)": (N, S),
        "North-East <> South-East": (NE, SE),
        "North-West <> South-West": (NW, SW),
        "North-West <> North-East (important!)": (NW, NE),
        "South-West <> South-East (important!)": (SW, SE),
    }

    for desc, pair in len_cmp_order.items():
        l, r = pair

        if abs(len(l) - len(r)) > bias:
            print(f"'_context_action_items' may look asymmetrical in direction: {desc}\n"
                  f"\t\"{l}\" {len(l)} characters\n"
                  f"\t\"{r}\" {len(r)} characters\n")


# TODO: (dev only) Uncomment next line to validate context action label symmetry if you change something in the context
# menu:
# __validate_context_action_items_display_symmetry_concept(bias=1)

del __validate_context_action_items_display_symmetry_concept


class MESH_OT_select_path(Operator):
    bl_idname = "mesh.select_path"
    bl_label = "Select Path"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    windows: set[Window] = set()

    __slots__ = ()

    context_action: bpy.props.EnumProperty(
        items=_context_action_items,
        default=set(),
        options={'ENUM_FLAG', 'HIDDEN', 'SKIP_SAVE'},
    )

    # Input events and keys
    select_mb: Literal['LEFTMOUSE', 'RIGHTMOUSE']
    "Select mouse button"
    pie_mb: Literal['LEFTMOUSE', 'RIGHTMOUSE']
    "Contextual pie menu mouse button"
    modal_events: dict[_PackedEvent_T, str]
    "Standard modal keymap modal events: ``'APPLY'``, ``'CANCEL'``, ect."
    undo_redo_events: dict[_PackedEvent_T, Literal['UNDO', 'REDO']]
    "Standard keymap undo and redo keys"
    nav_events: tuple[_PackedEvent_T]
    "Standard 3D View navigation events"
    is_mouse_pressed: bool

    # Tool settings mesh select modes and mesh elements
    initial_ts_msm: tuple[int | bool, int | bool, int | bool]
    """Initial tool settings mesh select mode with which operator was initialized"""
    initial_mesh_elements: Literal['edges', 'faces']
    """Mesh elements attribute with which operator retrieves initially selected mesh elements. If operator would run in
    faces mode, it would be ``"faces"``, and ``"edges"`` otherwise"""

    prior_ts_msm: tuple[int | bool, int | bool, int | bool]
    """If operator was initialized with verts or edges tool settings mesh selection mode flag enabled and faces flag
    disabled this attribute would be set to ``(False, True, False)`` (edges selection only). If faces flag was enabled
    (in any set of flags), it would be ``(False, False, True)`` (faces only)
    """
    prior_mesh_elements: Literal['edges', 'faces']
    """If operator was initialized with verts or edges tool settings mesh selection mode flag enabled and faces flag
    disabled this attribute would be set to ``"edges"`` (edge selection only). If faces flag was enabled (in any set of
    flags), it would be ``"faces"`` (faces only)
    """

    select_ts_msm: tuple[int | bool, int | bool, int | bool]
    """If operator was initialized with verts or edges tool settings mesh selection mode flag enabled and faces flag
    disabled this attribute would be set to ``(True, False, False)`` (vertices selection only). If faces flag was
    enabled (in any set of flags), it would be ``(False, False, True)`` (faces only)
    """
    select_mesh_elements: Literal['verts', 'faces']
    """If operator was initialized with verts or edges tool settings mesh selection mode flag enabled and faces flag
    disabled this attribute would be set to ``"verts"`` (verts selection only). If faces flag was enabled (in any set of
    flags), it would be ``"faces"`` (faces only)
    """

    # Initial selected mesh elements
    initial_select: tuple[BMVert | BMEdge | BMFace]

    # BMesh elements caches
    bm_arr: tuple[tuple[Object, BMesh]]

    path_arr: list[Path] = list()
    mesh_islands: list[tuple[BMVert | BMEdge | BMFace]]
    drag_elem_indices: list[None | int]
    _active_path_index: int = 0
    _drag_elem: None | BMVert | BMFace = None
    _just_closed_path: bool = False

    gpu_shaders: dict[str, gpu.types.GPUShader] = dict()
    gpu_draw_framework: None | bhqab.utils_gpu.draw_framework.DrawFramework = None
    gpu_handles: list = list()

    undo_history: collections.deque[tuple[int, tuple[Path]]]
    redo_history: collections.deque[tuple[int, tuple[Path]]]

    exec_select_arr: dict[Object, list[tuple[int]]]
    exec_markup_arr: dict[Object, list[tuple[int]]]

    @staticmethod
    def _pack_event(item: KeyMapItem | Event) -> _PackedEvent_T:
        return item.type, item.value, item.alt, item.ctrl, item.shift

    @classmethod
    def _eval_meshes(cls, context: Context) -> None:
        ret: list[tuple[Object, BMesh]] = list()

        props = context.window_manager.select_path

        for ob in context.objects_in_mode:
            ob: Object

            bm = bmesh.from_edit_mesh(ob.data)
            if cls.prior_ts_msm[1]:
                bm.edges.ensure_lookup_table()
            elif cls.prior_ts_msm[2]:
                bm.faces.ensure_lookup_table()
                if props.mark_seam != 'NONE' or props.mark_sharp != 'NONE':
                    bm.edges.ensure_lookup_table()
            ret.append((ob, bm))
        cls.bm_arr = tuple(ret)

    @classmethod
    @property
    def active_path(cls) -> Path:
        if len(cls.path_arr) - 1 > cls._active_path_index:
            return cls.path_arr[cls._active_path_index]
        return cls.path_arr[-1]

    @classmethod
    def set_active_path(cls, value: Path) -> None:
        cls._active_path_index = cls.path_arr.index(value)

    @staticmethod
    def _set_selection_state(elem_seq: tuple[BMVert | BMEdge | BMFace], state: bool = True) -> None:
        for elem in elem_seq:
            elem.select = state

    @staticmethod
    def _get_interactive_ui_under_mouse(context: Context, event: Event) -> None | tuple[Area, Region, RegionView3D]:
        mx, my = event.mouse_x, event.mouse_y

        for area in bpy.context.window.screen.areas:
            area: Area

            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        if ((region.x < mx < region.x + region.width - eval_view3d_n_panel_width(context))
                                and (region.y < my < region.y + region.height)):
                            for space in area.spaces:
                                if space.type == 'VIEW_3D':
                                    space: SpaceView3D

                                    if space.region_quadviews:
                                        region_data = space.region_quadviews
                                    else:
                                        region_data = space.region_3d
                            return area, region, region_data

    @classmethod
    def _get_element_by_mouse(cls, context: Context, event: Event) \
            -> tuple[None | BMVert | BMEdge | BMFace, None | Object]:

        ts = context.tool_settings
        ts.mesh_select_mode = cls.select_ts_msm

        bpy.ops.mesh.select_all(action='DESELECT')

        ui = MESH_OT_select_path._get_interactive_ui_under_mouse(context, event)

        if ui is not None:
            area, region, region_data = ui

            with context.temp_override(window=bpy.context.window, area=area, region=region, region_data=region_data):
                bpy.ops.view3d.select('EXEC_DEFAULT', location=(event.mouse_x - region.x, event.mouse_y - region.y))

        elem = None
        ob = None
        for ob, bm in cls.bm_arr:
            elem = bm.select_history.active
            if elem:
                elem.select = False
                bm.select_history.clear()
                break

        ts.mesh_select_mode = cls.prior_ts_msm
        return elem, ob

    @classmethod
    def _get_current_state_copy(cls) -> tuple[int, tuple[Path]]:
        return tuple((cls._active_path_index, tuple(n.copy() for n in cls.path_arr)))

    def _undo(self, context: Context) -> set[Literal['CANCELLED', 'RUNNING_MODAL']]:
        cls = self.__class__

        if len(cls.undo_history) == 1:
            cls._cancel_all_instances(context)
            return {'CANCELLED'}

        elif len(cls.undo_history) > 1:
            step = cls.undo_history.pop()
            cls.redo_history.append(step)
            undo_step_active_path_index, undo_step_path_seq = cls.undo_history[-1]
            cls._active_path_index = undo_step_active_path_index
            cls.path_arr = list(undo_step_path_seq)
            cls._just_closed_path = False

        context.area.tag_redraw()

        return {'RUNNING_MODAL'}

    def _redo(self, context: Context) -> None:
        cls = self.__class__

        if len(cls.redo_history) > 0:
            step = cls.redo_history.pop()
            cls.undo_history.append(step)
            undo_step_active_path_index, undo_step_path_seq = cls.undo_history[-1]
            cls._active_path_index = undo_step_active_path_index
            cls.path_arr = undo_step_path_seq
            context.area.tag_redraw()
        else:
            self.report({'WARNING'}, message="Can not redo anymore")

    @classmethod
    def _register_undo_step(cls) -> None:
        step = cls._get_current_state_copy()
        cls.undo_history.append(step)
        cls.redo_history.clear()

    @classmethod
    def _get_linked_island_index(cls, context: Context, elem: BMVert | BMFace) -> int:
        ts = context.tool_settings

        for i, linked_island in enumerate(cls.mesh_islands):
            if elem in linked_island:
                return i

        ts.mesh_select_mode = cls.select_ts_msm

        bpy.ops.mesh.select_all(action='DESELECT')
        elem.select_set(True)
        bpy.ops.mesh.select_linked(delimit={'NORMAL'})

        linked_island = cls._get_selected_elements(cls.select_mesh_elements)

        ts.mesh_select_mode = cls.prior_ts_msm

        bpy.ops.mesh.select_all(action='DESELECT')
        cls.mesh_islands.append(linked_island)
        return len(cls.mesh_islands) - 1

    @classmethod
    def _update_meshes(cls) -> None:
        for ob, bm in cls.bm_arr:
            bm.select_flush_mode()
            bmesh.update_edit_mesh(mesh=ob.data, loop_triangles=True, destructive=False)

    @classmethod
    def _update_fills_by_element_index(cls, context: Context, path: Path, elem_index: int) -> None:
        ts = context.tool_settings

        pairs_items = path.get_pairs_items(elem_index)
        for elem_0, elem_1, fill_index in pairs_items:

            ts.mesh_select_mode = cls.select_ts_msm

            bpy.ops.mesh.select_all(action='DESELECT')
            cls._set_selection_state((elem_0, elem_1), True)
            bpy.ops.mesh.shortest_path_select(use_topology_distance=bool(path.flag & PathFlag.TOPOLOGY))
            cls._set_selection_state((elem_0, elem_1), False)
            fill_seq = cls._get_selected_elements(cls.prior_mesh_elements)
            bpy.ops.mesh.select_all(action='DESELECT')

            # Exception if control points in one edge
            if (not fill_seq) and isinstance(elem_0, BMVert):
                for edge in elem_0.link_edges:
                    edge: BMEdge
                    if edge.other_vert(elem_0) == elem_1:
                        fill_seq = tuple((edge,))

            ts.mesh_select_mode = cls.prior_ts_msm

            path.fill_elements[fill_index] = fill_seq

            batch = None
            if cls.prior_ts_msm[1]:  # Edge mesh select mode
                shader = cls.gpu_shaders["path_edge"]
                coord = []
                for edge in fill_seq:
                    coord.extend([vert.co for vert in edge.verts])
                batch = batch_for_shader(shader, 'LINES', dict(Coord=coord))

            elif cls.prior_ts_msm[2]:  # Faces mesh select mode
                shader = cls.gpu_shaders["path_face"]
                batch, _ = cls._gpu_gen_batch_faces_seq(fill_seq, False, shader)

            path.batch_seq_fills[fill_index] = batch

    def _remove_path_doubles(self, context: Context, path: Path) -> None:
        cls = self.__class__
        for i, control_element in enumerate(path.control_elements):
            if path.control_elements.count(control_element) > 1:
                for j, other_control_element in enumerate(path.control_elements):
                    if i != j and other_control_element == control_element:
                        # First-last control element same path
                        if i == 0 and j == len(path.control_elements) - 1:
                            path.pop_control_element(-1)
                            if (path.flag ^ PathFlag.CLOSED):
                                path.flag |= PathFlag.CLOSED
                                cls._update_fills_by_element_index(context, path, 0)

                                message = "Closed path"
                                if path == cls.active_path:
                                    cls._just_closed_path = True
                                    message = "Closed active path"
                                self.report(type={'INFO'}, message=message)
                            else:
                                cls._update_fills_by_element_index(context, path, 0)
                        # Adjacent control elements
                        elif i in (j - 1, j + 1):
                            path.pop_control_element(j)
                            batch, _ = cls._gpu_gen_batch_control_elements(path == cls.active_path, path)
                            path.batch_control_elements = batch
                            self.report(type={'INFO'}, message="Merged adjacent control elements")
                        # else:
                        #     # Maybe, undo here?

    def _join_adjacent_to_active_path(self) -> None:
        cls = self.__class__

        if cls.active_path.flag ^ PathFlag.CLOSED:
            l_path = cls.active_path

            for i, r_path in enumerate(cls.path_arr):
                if (
                    i != cls._active_path_index
                    and l_path.island_index == r_path.island_index
                    and r_path.flag ^ PathFlag.CLOSED
                ):

                    is_joined = True

                    # End-First
                    if l_path.control_elements[-1] == r_path.control_elements[0]:
                        l_path.control_elements.pop(-1)
                        l_path.fill_elements.pop(-1)
                        l_path.batch_seq_fills.pop(-1)

                        l_path.control_elements.extend(r_path.control_elements)
                        l_path.fill_elements.extend(r_path.fill_elements)
                        l_path.batch_seq_fills.extend(r_path.batch_seq_fills)

                    # First-End
                    elif l_path.control_elements[0] == r_path.control_elements[-1]:
                        l_path.control_elements.pop(0)

                        r_path.fill_elements.pop(-1)
                        r_path.batch_seq_fills.pop(-1)

                        r_path.control_elements.extend(l_path.control_elements)
                        r_path.fill_elements.extend(l_path.fill_elements)
                        r_path.batch_seq_fills.extend(l_path.batch_seq_fills)

                        l_path.control_elements = r_path.control_elements
                        l_path.fill_elements = r_path.fill_elements
                        l_path.batch_seq_fills = r_path.batch_seq_fills

                    # First-First
                    elif l_path.control_elements[-1] == r_path.control_elements[0]:
                        l_path.control_elements.pop(0)

                        r_path.control_elements.reverse()
                        r_path.fill_elements.reverse()
                        r_path.batch_seq_fills.reverse()

                        r_path.fill_elements.pop(0)
                        r_path.batch_seq_fills.pop(0)

                        r_path.control_elements.extend(l_path.control_elements)
                        r_path.fill_elements.extend(l_path.fill_elements)
                        r_path.batch_seq_fills.extend(l_path.batch_seq_fills)

                        l_path.control_elements = r_path.control_elements
                        l_path.fill_elements = r_path.fill_elements
                        l_path.batch_seq_fills = r_path.batch_seq_fills

                    # End-End
                    elif l_path.control_elements[-1] == r_path.control_elements[-1]:
                        r_path.reverse()
                        l_path.control_elements.pop(-1)
                        l_path.fill_elements.pop(-1)
                        l_path.batch_seq_fills.pop(-1)

                        l_path.control_elements.extend(r_path.control_elements)
                        l_path.fill_elements.extend(r_path.fill_elements)
                        l_path.batch_seq_fills.extend(r_path.batch_seq_fills)
                    else:
                        is_joined = False

                    if is_joined:
                        cls.path_arr.remove(r_path)
                        cls._active_path_index = cls.path_arr.index(cls.active_path)

                        batch, cls.active_index = cls._gpu_gen_batch_control_elements(True, cls.active_path)
                        cls.active_path.batch_control_elements = batch
                        self.report(type={'INFO'}, message="Joined two paths")
                        return

    @classmethod
    def _get_selected_elements(cls, mesh_elements: str) -> tuple[BMVert | BMEdge | BMFace]:
        ret = tuple()

        for _, bm in cls.bm_arr:
            elem_arr = getattr(bm, mesh_elements)
            ret += tuple((n for n in elem_arr if n.select))
        return ret

    def _ui_draw_popup_menu_pie(self, popup: UIPieMenu, context: Context) -> None:
        pie = popup.layout.menu_pie()
        pie.prop_tabs_enum(self, "context_action")
        pie.popover(MESH_PT_select_path_context.__name__)

    @staticmethod
    def _ui_draw_statusbar(self, context: Context) -> None:
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

        bhqab.utils_ui.template_input_info_kmi_from_type(layout, label="Cancel", event_types=cancel_keys)
        bhqab.utils_ui.template_input_info_kmi_from_type(layout, label="Apply", event_types=apply_keys)
        bhqab.utils_ui.template_input_info_kmi_from_type(
            layout, label="Close Path", event_types={HARDCODED_CLOSE_PATH_KMI[0]}
        )
        bhqab.utils_ui.template_input_info_kmi_from_type(
            layout, label="Change Direction", event_types={HARDCODED_CHANGE_DIRECTION_KMI[0]}
        )
        bhqab.utils_ui.template_input_info_kmi_from_type(
            layout, label="Topology Distance", event_types={HARDCODED_TOPOLOGY_DISTANCE_KMI[0]}
        )

    @staticmethod
    def _gpu_gen_batch_faces_seq(fill_seq, is_active, shader):
        tmp_bm = bmesh.new()
        for face in fill_seq:
            tmp_bm.faces.new((tmp_bm.verts.new(v.co, v) for v in face.verts), face)

        tmp_bm.verts.index_update()
        tmp_bm.faces.ensure_lookup_table()

        tmp_loops = tmp_bm.calc_loop_triangles()

        r_batch = batch_for_shader(
            shader, 'TRIS',
            dict(Coord=tuple((v.co for v in tmp_bm.verts))),
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

    @classmethod
    def _gpu_gen_batch_control_elements(cls, is_active, path):
        shader = cls.gpu_shaders["cp_vert"]
        if cls.prior_ts_msm[2]:
            shader = cls.gpu_shaders["cp_face"]

        r_batch = None
        r_active_elem_start_index = 0

        if cls.prior_ts_msm[1]:
            r_batch = batch_for_shader(shader, 'POINTS', dict(Coord=tuple((v.co for v in path.control_elements))))
            if is_active:
                r_active_elem_start_index = len(path.control_elements) - 1
        elif cls.prior_ts_msm[2]:
            r_batch, r_active_elem_start_index = cls._gpu_gen_batch_faces_seq(
                path.control_elements,
                is_active,
                shader
            )

        return r_batch, r_active_elem_start_index

    @classmethod
    def _gpu_remove_handles(cls) -> None:
        for handle in cls.gpu_handles:
            SpaceView3D.draw_handler_remove(handle, 'WINDOW')
        cls.gpu_handles.clear()

    @classmethod
    def _gpu_draw_callback(cls: MESH_OT_select_path) -> None:
        addon_pref = bpy.context.preferences.addons[addon_pkg].preferences

        draw_list: list[Path] = [_ for _ in cls.path_arr if _ != cls.active_path]
        draw_list.append(cls.active_path)

        # if cls.prior_ts_msm[1]:
        shader_ce = cls.gpu_shaders["cp_vert"]
        if cls.prior_ts_msm[2]:
            shader_ce = cls.gpu_shaders["cp_face"]

        shader_path = cls.gpu_shaders["path_edge"]
        if cls.prior_ts_msm[2]:
            shader_path = cls.gpu_shaders["path_face"]

        depth_map = bhqab.utils_gpu.draw_framework.get_depth_map()
        viewport_metrics = bhqab.utils_gpu.draw_framework.get_viewport_metrics()

        offscreen = cls.gpu_draw_framework.get(index=0)

        with offscreen.bind():
            fb = gpu.state.active_framebuffer_get()
            fb.clear(color=(0.0, 0.0, 0.0, 0.0))

            with gpu.matrix.push_pop():
                gpu.state.line_width_set(addon_pref.line_width)
                gpu.state.blend_set('ALPHA_PREMULT')
                gpu.state.face_culling_set('NONE')

                for path in draw_list:
                    active_ce_index = 0
                    color_ce = addon_pref.color_control_element
                    color_active_ce = color_ce
                    color_path = addon_pref.color_path
                    if path.flag & PathFlag.TOPOLOGY:
                        color_path = addon_pref.color_path_topology

                    if path == cls.active_path:
                        active_ce_index = cls.active_index

                        color_active_ce = addon_pref.color_active_control_element
                        color_path = addon_pref.color_active_path

                        if path.flag & PathFlag.TOPOLOGY:
                            color_path = addon_pref.color_active_path_topology

                    shader_path.bind()
                    for batch in path.batch_seq_fills:
                        if batch:
                            shader_path.uniform_float("ModelMatrix", path.ob.matrix_world)
                            shader_path.uniform_float("ColorPath", color_path)
                            shader_path.uniform_sampler("OriginalViewDepthMap", depth_map)
                            shader_path.uniform_float("viewportMetrics", viewport_metrics)
                            batch.draw(shader_path)

                    shader_ce.bind()

                    if path.batch_control_elements:
                        shader_ce.uniform_float("ModelMatrix", path.ob.matrix_world)
                        shader_ce.uniform_float("ColorControlElement", color_ce)
                        shader_ce.uniform_float("ColorActiveControlElement", color_active_ce)
                        shader_ce.uniform_int("ActiveControlElementIndex", (active_ce_index,))
                        shader_ce.uniform_sampler("OriginalViewDepthMap", depth_map)
                        shader_ce.uniform_float("viewportMetrics", viewport_metrics)
                        if cls.prior_ts_msm[1]:
                            shader_ce.uniform_float("DiskRadius", (addon_pref.point_size + 6))

                        path.batch_control_elements.draw(shader_ce)

        cls.gpu_draw_framework.draw(texture=offscreen.texture_color)

    def _interact_control_element(self,
                                  context: Context,
                                  elem: None | BMVert | BMFace,
                                  ob: Object,
                                  interact_event: InteractEvent) -> None:

        cls = self.__class__

        props = context.window_manager.select_path

        if elem and interact_event is InteractEvent.ADD_CP:
            if not cls.path_arr:
                return self._interact_control_element(context, elem, ob, InteractEvent.ADD_NEW_PATH)

            new_elem_index = None

            elem_index = cls.active_path.is_in_control_elements(elem)
            if elem_index is None:
                new_elem_index = len(cls.active_path.control_elements)

                fill_index = cls.active_path.is_in_fill_elements(elem)
                if fill_index is None:
                    is_found_in_other_path = False
                    for path in cls.path_arr:
                        if path == cls.active_path:
                            continue
                        other_elem_index = path.is_in_control_elements(elem)
                        if other_elem_index is None:
                            other_fill_index = path.is_in_fill_elements(elem)
                            if other_fill_index is not None:
                                is_found_in_other_path = True
                        else:
                            is_found_in_other_path = True

                        if is_found_in_other_path:
                            cls.set_active_path(path)
                            cls._just_closed_path = False
                            self._interact_control_element(context, elem, ob, InteractEvent.ADD_CP)
                            return
                else:
                    new_elem_index = fill_index + 1
                    cls._just_closed_path = False

            elif len(cls.active_path.control_elements) == 1:
                batch, cls.active_index = cls._gpu_gen_batch_control_elements(True, cls.active_path)
                cls.active_path.batch_control_elements = batch

            if elem_index is not None:
                cls.drag_elem_indices = [path.is_in_control_elements(elem) for path in cls.path_arr]
                cls._just_closed_path = False
            cls._drag_elem = elem

            if cls._just_closed_path:
                return self._interact_control_element(context, elem, ob, InteractEvent.ADD_NEW_PATH)

            if new_elem_index is not None:
                linked_island_index = cls._get_linked_island_index(context, elem)
                if cls.active_path.island_index != linked_island_index:
                    return self._interact_control_element(context, elem, ob, InteractEvent.ADD_NEW_PATH)

                cls.active_path.insert_control_element(new_elem_index, elem)
                cls._update_fills_by_element_index(context, cls.active_path, new_elem_index)

                batch, cls.active_index = cls._gpu_gen_batch_control_elements(True, cls.active_path)
                cls.active_path.batch_control_elements = batch

                cls.drag_elem_indices = [path.is_in_control_elements(elem) for path in cls.path_arr]

        elif elem and interact_event is InteractEvent.ADD_NEW_PATH:
            linked_island_index = cls._get_linked_island_index(context, elem)
            new_path = Path(elem, linked_island_index, ob)

            if props.use_topology_distance:
                new_path.flag |= PathFlag.TOPOLOGY

            cls.path_arr.append(new_path)
            cls.set_active_path(new_path)
            cls._just_closed_path = False
            self._interact_control_element(context, elem, ob, InteractEvent.ADD_CP)
            self.report(type={'INFO'}, message="Created new path")
            # return

        elif elem and interact_event is InteractEvent.REMOVE_CP:
            cls._just_closed_path = False

            elem_index = cls.active_path.is_in_control_elements(elem)
            if elem_index is None:
                for path in cls.path_arr:
                    other_elem_index = path.is_in_control_elements(elem)
                    if other_elem_index is not None:
                        cls.set_active_path(path)
                        self._interact_control_element(context, elem, ob, InteractEvent.REMOVE_CP)
                        return
            else:
                cls.active_path.pop_control_element(elem_index)

                if not len(cls.active_path.control_elements):
                    cls.path_arr.remove(cls.active_path)
                    if len(cls.path_arr):
                        cls.set_active_path(cls.path_arr[-1])
                else:
                    cls._update_fills_by_element_index(context, cls.active_path, elem_index)
                    batch, cls.active_index = cls._gpu_gen_batch_control_elements(True, cls.active_path)
                    cls.active_path.batch_control_elements = batch

        elif elem and interact_event is InteractEvent.DRAG_CP:
            if (not cls._drag_elem) or (len(cls.drag_elem_indices) != len(cls.path_arr)):
                return
            cls._just_closed_path = False

            linked_island_index = cls._get_linked_island_index(context, elem)
            if cls.active_path.island_index == linked_island_index:
                cls._drag_elem = elem

                for i, path in enumerate(cls.path_arr):
                    j = cls.drag_elem_indices[i]
                    if j is not None:
                        path.control_elements[j] = elem

                        cls._update_fills_by_element_index(context, path, j)
                        path.batch_control_elements, cls.active_index = cls._gpu_gen_batch_control_elements(
                            path == cls.active_path,
                            path
                        )

        elif interact_event is InteractEvent.CHANGE_DIRECTION:
            cls.active_path.reverse()
            batch, cls.active_index = cls._gpu_gen_batch_control_elements(True, cls.active_path)
            cls.active_path.batch_control_elements = batch
            cls._just_closed_path = False

        elif interact_event is InteractEvent.CLOSE_PATH:
            cls.active_path.flag ^= PathFlag.CLOSED

            if cls.active_path.flag & PathFlag.CLOSED:
                cls._update_fills_by_element_index(context, cls.active_path, 0)
                if len(cls.active_path.control_elements) > 2:
                    cls._just_closed_path = True
            else:
                cls.active_path.fill_elements[-1] = []
                cls.active_path.batch_seq_fills[-1] = None
                cls._just_closed_path = False
                self._join_adjacent_to_active_path()

        elif interact_event is InteractEvent.TOPOLOGY_DISTANCE:
            cls.active_path.flag ^= PathFlag.TOPOLOGY
            for j in range(0, len(cls.active_path.control_elements), 2):
                cls._update_fills_by_element_index(context, cls.active_path, j)

        elif interact_event is InteractEvent.RELEASE_PATH:
            cls.drag_elem_indices.clear()
            cls._drag_elem = None

            for path in cls.path_arr:
                self._remove_path_doubles(context, path)
            self._join_adjacent_to_active_path()

            cls._register_undo_step()

    def draw(self, context: Context) -> None:
        layout = self.layout
        layout.use_property_split = True
        props = context.window_manager.select_path
        props.ui_draw_func(layout)

    def invoke(self, context: bpy.types.Context, event):
        cls = self.__class__
        wm = context.window_manager

        if not cls.windows:
            cls.windows.add(context.window)

            for window in wm.windows:
                window: Window

                if context.window != window:
                    for area in window.screen.areas:
                        area: Area

                        if area.type == 'VIEW_3D':
                            for region in area.regions:
                                region: Region

                                if region.type == 'WINDOW':
                                    break
                            else:
                                continue
                            break
                    else:
                        continue
                    with context.temp_override(window=window, area=area, region=region):
                        bpy.ops.mesh.select_path('INVOKE_DEFAULT')
                        cls.windows.add(window)
        else:
            wm.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        props = wm.select_path
        ts = context.scene.tool_settings
        num_undo_steps = context.preferences.edit.undo_steps

        # ____________________________________________________________________ #
        # Input keymaps:

        kc = wm.keyconfigs.user
        km_path_tool = kc.keymaps["3D View Tool: Edit Mesh, Select Path"]
        kmi = km_path_tool.keymap_items[0]

        # Select and context pie menu mouse buttons.
        cls.select_mb = kmi.type
        cls.pie_mb = 'LEFTMOUSE'
        if cls.select_mb == 'LEFTMOUSE':
            cls.pie_mb = 'RIGHTMOUSE'

        # Modal keymap.
        cls.modal_events = dict()
        for kmi in kc.keymaps["Standard Modal Map"].keymap_items:
            ev = cls._pack_event(kmi)
            cls.modal_events[(ev[0], ev[1], False, False, False)] = kmi.propvalue

        # Operator's undo/redo keymap.
        cls.undo_redo_events = dict()
        km_screen = kc.keymaps['Screen']

        kmi = km_screen.keymap_items.find_from_operator(idname='ed.undo')
        cls.undo_redo_events[cls._pack_event(kmi)] = 'UNDO'

        kmi = km_screen.keymap_items.find_from_operator(idname='ed.redo')
        cls.undo_redo_events[cls._pack_event(kmi)] = 'REDO'

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
                ev = list(cls._pack_event(kmi))
                if ev[0] == 'WHEELINMOUSE':
                    ev[0] = 'WHEELUPMOUSE'
                elif ev[0] == 'WHEELOUTMOUSE':
                    ev[0] = 'WHEELDOWNMOUSE'
                nav_events.append(tuple(ev))
        cls.nav_events = tuple(nav_events)

        cls.is_mouse_pressed = False

        # ____________________________________________________________________ #
        # Initialize variables.

        cls.path_arr.clear()
        cls.mesh_islands = list()
        cls.drag_elem_indices = list()

        cls._active_path_index = 0
        cls._drag_elem = None
        cls._just_closed_path = False

        cls.gpu_handles = list()

        cls.undo_history = collections.deque(maxlen=num_undo_steps)
        cls.redo_history = collections.deque(maxlen=num_undo_steps)

        cls.exec_select_arr = dict()
        cls.exec_markup_arr = dict()
        # ____________________________________________________________________ #
        # Meshes context setup.
        # Evaluate meshes:

        cls.initial_ts_msm = tuple(ts.mesh_select_mode)
        cls.initial_mesh_elements = "edges"
        if cls.initial_ts_msm[2]:
            cls.initial_mesh_elements = "faces"

        cls.prior_ts_msm = (False, True, False)
        cls.prior_mesh_elements = "edges"
        cls.select_ts_msm = (True, False, False)
        cls.select_mesh_elements = "verts"
        if cls.initial_ts_msm[2]:
            cls.prior_ts_msm = (False, False, True)
            cls.prior_mesh_elements = "faces"
            cls.select_ts_msm = (False, False, True)
            cls.select_mesh_elements = "faces"

        cls._eval_meshes(context)
        cls.initial_select = cls._get_selected_elements(cls.initial_mesh_elements)

        # Tweak operator settings in case if all mesh elements are already selected
        num_elements_total = 0
        if cls.prior_mesh_elements == "edges":
            for _, bm in cls.bm_arr:
                num_elements_total += len(bm.edges)
        elif cls.prior_mesh_elements == "faces":
            for _, bm in cls.bm_arr:
                num_elements_total += len(bm.faces)

        if num_elements_total == len(cls.initial_select) and props.mark_select == 'EXTEND':
            props.mark_select = 'NONE'
        elif num_elements_total > len(cls.initial_select) and props.mark_select == 'NONE':
            props.mark_select = 'EXTEND'

        elem, ob = cls._get_element_by_mouse(context, event)
        if not elem:
            cls._cancel_all_instances(context)
            return {'CANCELLED'}

        STATUSBAR_HT_header.prepend(cls._ui_draw_statusbar)

        cls.gpu_handles = [
            SpaceView3D.draw_handler_add(self._gpu_draw_callback, tuple(), 'WINDOW', 'POST_VIEW'),
        ]

        cls.gpu_shaders = bhqab.utils_gpu.shader.eval_shaders_dict(
            dir_path=os.path.join(os.path.dirname(__file__), "data", "shaders")
        )
        cls.gpu_draw_framework = bhqab.utils_gpu.draw_framework.DrawFramework(num_offscreens=1)

        self._interact_control_element(context, elem, ob, InteractEvent.ADD_NEW_PATH)
        wm.modal_handler_add(self)
        return self.modal(context, event)

    @classmethod
    def _cancel_all_instances(cls, context: Context) -> None:
        cls.windows.clear()
        ts = context.tool_settings

        ts.mesh_select_mode = cls.initial_ts_msm
        cls._set_selection_state(cls.initial_select, True)
        cls._update_meshes()
        cls._gpu_remove_handles()
        STATUSBAR_HT_header.remove(cls._ui_draw_statusbar)

    def cancel(self, context: Context):
        cls = self.__class__

        if context.window in cls.windows:
            cls.windows.remove(context.window)

        if not cls.windows:
            cls._cancel_all_instances(context)

    def modal(self, context: Context, event: Event):
        cls = self.__class__

        # Cancel execution of other instances if operator was cancelled
        if not cls.windows:
            return {'CANCELLED'}

        addon_pref = context.preferences.addons[addon_pkg].preferences
        ev = cls._pack_event(event)
        modal_action = cls.modal_events.get(ev, None)
        undo_redo_action = cls.undo_redo_events.get(ev, None)
        interact_event = None

        if (
            modal_action == 'CANCEL'
            or InteractEvent.CANCEL.name in self.context_action
        ):
            self.context_action = set()
            cls._cancel_all_instances(context)
            return {'CANCELLED'}

        elif (
            modal_action == 'APPLY'
            or ev == HARDCODED_APPLY_KMI
            or InteractEvent.APPLY_PATHES.name in self.context_action
        ):
            self.context_action = set()

            cls.windows.clear()
            cls._eval_final_element_indices_arrays()
            cls._gpu_remove_handles()
            STATUSBAR_HT_header.remove(cls._ui_draw_statusbar)
            return self.execute(context)

        elif cls._get_interactive_ui_under_mouse(context, event) is None:
            return {'RUNNING_MODAL'}

        elif ev in cls.nav_events:
            return {'PASS_THROUGH'}

        elif (
            InteractEvent.CLOSE_PATH.name in self.context_action
            or ev == HARDCODED_CLOSE_PATH_KMI
        ):
            self.context_action = set()
            interact_event = InteractEvent.CLOSE_PATH

        elif (
            InteractEvent.CHANGE_DIRECTION.name in self.context_action
            or ev == HARDCODED_CHANGE_DIRECTION_KMI
        ):
            self.context_action = set()
            interact_event = InteractEvent.CHANGE_DIRECTION

        elif (
            InteractEvent.TOPOLOGY_DISTANCE.name in self.context_action
            or ev == HARDCODED_TOPOLOGY_DISTANCE_KMI
        ):
            self.context_action = set()
            interact_event = InteractEvent.TOPOLOGY_DISTANCE

        elif (undo_redo_action == 'UNDO') or (InteractEvent.UNDO.name in self.context_action):
            self.context_action = set()
            return self._undo(context)

        elif (undo_redo_action == 'REDO') or (InteractEvent.REDO.name in self.context_action):
            self.context_action = set()
            self._redo(context)

        elif ev == (cls.pie_mb, 'PRESS', False, False, False):
            cls.is_mouse_pressed = False
            context.window_manager.popup_menu_pie(
                event=event,
                draw_func=self._ui_draw_popup_menu_pie,
                title="Path Tool",
                icon='NONE',
            )
            return {'RUNNING_MODAL'}

        elif ev == (cls.select_mb, 'PRESS', False, False, False):
            cls.is_mouse_pressed = True
            interact_event = InteractEvent.ADD_CP

        elif ev == (cls.select_mb, 'PRESS', False, False, True):
            cls.is_mouse_pressed = True
            interact_event = InteractEvent.ADD_NEW_PATH

        elif ev == (cls.select_mb, 'PRESS', False, True, False):
            cls.is_mouse_pressed = False
            interact_event = InteractEvent.REMOVE_CP

        elif ev in ((cls.select_mb, 'RELEASE', False, False, False),
                    (cls.select_mb, 'RELEASE', False, True, False),
                    (cls.select_mb, 'RELEASE', False, False, True),
                    ):
            cls.is_mouse_pressed = False
            interact_event = InteractEvent.RELEASE_PATH

        elif cls.is_mouse_pressed and ev[0] in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
            interact_event = InteractEvent.DRAG_CP

        if interact_event is not None:
            elem, ob = cls._get_element_by_mouse(context, event)
            self._interact_control_element(context, elem, ob, interact_event)

            cls._set_selection_state(cls.initial_select, True)
            cls._update_meshes()

        if not len(cls.path_arr):
            cls._cancel_all_instances(context)
            return {'CANCELLED'}

        cls.gpu_draw_framework.aa_method = addon_pref.aa_method
        if addon_pref.aa_method == 'FXAA':
            cls.gpu_draw_framework.aa.preset = addon_pref.fxaa_preset
            cls.gpu_draw_framework.aa.value = addon_pref.fxaa_value
        elif addon_pref.aa_method == 'SMAA':
            cls.gpu_draw_framework.aa.preset = addon_pref.smaa_preset
        cls.gpu_draw_framework.modal_eval(format='RGBA8', percentage=100)
        # NOTE: Use this print statement for debugging purposes.
        # print(self.path_arr)

        return {'RUNNING_MODAL'}

    @classmethod
    def _eval_final_element_indices_arrays(cls) -> None:
        cls.exec_select_arr = dict()
        cls.exec_markup_arr = dict()

        for ob, _bm in cls.bm_arr:
            index_select_seq = []
            index_markup_seq = []

            for path in cls.path_arr:
                if path.ob == ob:
                    for fill_seq in path.fill_elements:
                        index_select_seq.extend([_.index for _ in fill_seq])
                    if cls.prior_ts_msm[1]:  # Edges
                        index_markup_seq = index_select_seq
                    if cls.prior_ts_msm[2]:  # Faces
                        # For face selection mode control elements are required too
                        index_select_seq.extend([face.index for face in path.control_elements])
                        tmp = path.fill_elements
                        tmp.append(path.control_elements)
                        for fill_seq in tmp:
                            for face in fill_seq:
                                index_markup_seq.extend([e.index for e in face.edges])
                # Remove duplicates
                cls.exec_select_arr[ob] = list(dict.fromkeys(index_select_seq))
                cls.exec_markup_arr[ob] = list(dict.fromkeys(index_markup_seq))

        cls._update_meshes()

    def execute(self, context: Context):
        cls = self.__class__
        ts = context.tool_settings
        props = context.window_manager.select_path
        ts.mesh_select_mode = cls.prior_ts_msm
        cls._eval_meshes(context)
        cls.initial_select = cls._get_selected_elements(cls.prior_mesh_elements)

        for ob, bm in cls.bm_arr:
            if props.mark_select != 'NONE':
                index_select_seq = cls.exec_select_arr[ob]
                elem_seq = bm.edges
                if cls.prior_ts_msm[2]:
                    elem_seq = bm.faces
                if props.mark_select == 'EXTEND':
                    for i in index_select_seq:
                        elem_seq[i].select_set(True)
                elif props.mark_select == 'SUBTRACT':
                    for i in index_select_seq:
                        elem_seq[i].select_set(False)
                elif props.mark_select == 'INVERT':
                    for i in index_select_seq:
                        elem_seq[i].select_set(not elem_seq[i].select)

            index_markup_seq = cls.exec_markup_arr[ob]
            elem_seq = bm.edges
            if props.mark_seam != 'NONE':
                if props.mark_seam == 'MARK':
                    for i in index_markup_seq:
                        elem_seq[i].seam = True
                elif props.mark_seam == 'CLEAR':
                    for i in index_markup_seq:
                        elem_seq[i].seam = False
                elif props.mark_seam == 'TOGGLE':
                    for i in index_markup_seq:
                        elem_seq[i].seam = not elem_seq[i].seam

            if props.mark_sharp != 'NONE':
                if props.mark_sharp == 'MARK':
                    for i in index_markup_seq:
                        elem_seq[i].smooth = False
                elif props.mark_sharp == 'CLEAR':
                    for i in index_markup_seq:
                        elem_seq[i].smooth = True
                elif props.mark_sharp == 'TOGGLE':
                    for i in index_markup_seq:
                        elem_seq[i].smooth = not elem_seq[i].smooth

        self._update_meshes()
        return {'FINISHED'}