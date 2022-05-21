from __future__ import annotations
from typing import (
    Literal,
    Union,
)
import collections
from enum import auto, IntFlag

import bpy
from bpy.types import (
    Context,
    Event,
    KeyMapItem,
    Object,
    Operator,
    SpaceView3D,
    STATUSBAR_HT_header,
    UILayout,
    UIPieMenu,
    Menu,
)
from bpy.props import (
    EnumProperty,
)

import bmesh
from bmesh.types import (
    BMesh,
    BMVert,
    BMEdge,
    BMFace,
)
import gpu
from gpu.types import GPUBatch
from gpu_extras.batch import batch_for_shader

from . import bhqab
from . import __package__ as addon_pkg

HARDCODED_APPLY_KMI = ('SPACE', 'PRESS', False, False, False)
HARDCODED_CLOSE_PATH_KMI = ('C', 'PRESS', False, False, False)
HARDCODED_CHANGE_DIRECTION_KMI = ('D', 'PRESS', False, False, False)
HARDCODED_TOPOLOGY_DISTANCE_KMI = ('T', 'PRESS', False, False, False)


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
    ob: Object
    batch_control_elements: Union[None, GPUBatch]
    control_elements: list[Union[BMVert, BMFace]]
    fill_elements: list[list[Union[BMEdge, BMFace]]]
    batch_seq_fills: list[GPUBatch]
    flag: PathFlag

    def __init__(self,
                 elem: Union[None, BMVert, BMFace] = None,
                 linked_island_index: int = 0,
                 ob: Union[None, Object] = None) -> None:

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

    def __add__(self, other: Path) -> Path:
        if self.island_index == other.island_index:
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

    def is_in_control_elements(self, elem):
        if elem in self.control_elements:
            return self.control_elements.index(elem)

    def is_in_fill_elements(self, elem):
        if isinstance(elem, bmesh.types.BMVert):
            for i, arr in enumerate(self.fill_elements):
                arr: list[bmesh.types.BMEdge]

                for edge in arr:
                    edge: bmesh.types.BMEdge

                    for vert in edge.verts:
                        vert: bmesh.types.BMVert
                        if elem == vert:
                            return i
                del arr

        # elif isinstance(elem, bmesh.types.BMFace):
        for i, arr in enumerate(self.fill_elements):
            arr: list[bmesh.types.BMFace]

            if elem in arr:
                return i

    def insert_control_element(self, elem_index, elem):
        self.control_elements.insert(elem_index, elem)
        self.fill_elements.insert(elem_index, [])
        self.batch_seq_fills.insert(elem_index, None)

    def remove_control_element(self, elem) -> None:
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


_PackedEvent_T = tuple[
    Union[int, str], Union[int, str],
    Union[int, bool], Union[int, bool], Union[int, bool]]


class MESH_OT_select_path(Operator):
    bl_idname = "mesh.select_path"
    bl_label = "Select Path"
    bl_options = {'REGISTER', 'UNDO'}

    # __slots__ = (
    #     "select_mb",
    #     "pie_mb",
    #     "modal_events",
    #     "undo_redo_events",
    #     "nav_events",
    #     "is_mouse_pressed",
    #     "is_navigation_active",

    #     "initial_ts_msm",
    #     "initial_mesh_elements",
    #     "prior_ts_msm",
    #     "prior_mesh_elements",
    #     "select_ts_msm",
    #     "select_mesh_elements",
    #     "initial_select",

    #     "bm_arr",
    #     "path_seq",
    #     "mesh_islands",
    #     "drag_elem_indices",

    #     "_active_path_index",
    #     "_drag_elem",
    #     "_just_closed_path",

    #     "undo_history",
    #     "redo_history",

    #     "select_only_arr",
    #     "markup_arr",
    # )

    context_action: EnumProperty(
        # NOTE: Keep items display names length for visual symmetry.
        # UI layout of pie-menu is next:
        # |----------------------------------------
        # |                 Apply
        # |        Undo                Redo
        # | Direction                    Close Path
        # |    Topology                Options
        # |                 Cancel
        # |----------------------------------------
        # "Options" is `bl_label` of `MESH_PT_select_path_context`.
        items=(
            (
                InteractEvent.CHANGE_DIRECTION.name,
                "Direction",  # 16 chars
                ("Change the direction of the active path.\n"
                 "The active element of the path will be the final element "
                 "from the opposite end of the path, from it will be formed a section to the next control element that "
                 "you create."),
                'NONE',  # 'CON_CHILDOF',
                InteractEvent.CHANGE_DIRECTION.value,
            ),
            (
                InteractEvent.CLOSE_PATH.name,
                "Close Path",  # 10 chars
                "Connect between the beginning and end of the active path",
                'NONE',  # 'MESH_CIRCLE',
                InteractEvent.CLOSE_PATH.value,
            ),
            (
                InteractEvent.CANCEL.name,
                "Cancel",  # 6 chars
                "Cancel editing pathes",
                'EVENT_ESC',
                InteractEvent.CANCEL.value,
            ),
            (
                InteractEvent.APPLY_PATHES.name,
                "Apply",  # 5 chars
                "Apply the created mesh paths according to the selected options",
                'EVENT_RETURN',
                InteractEvent.APPLY_PATHES.value,
            ),
            (
                InteractEvent.UNDO.name,
                "Undo",  # 4 chars
                "Take a step back",
                'LOOP_BACK',
                InteractEvent.UNDO.value,
            ),
            (
                InteractEvent.REDO.name,
                "Redo",  # 4 chars
                "Redo previous undo",
                'LOOP_FORWARDS',
                InteractEvent.REDO.value,
            ),
            (
                InteractEvent.TOPOLOGY_DISTANCE.name,
                "Topology",  # 8 chars
                ("Algorithm for calculating the path: simple or using a mesh topology"
                 "(Find the minimum number of steps, ignoring spatial distance)"),
                'NONE',  # 'DRIVER_DISTANCE',
                InteractEvent.TOPOLOGY_DISTANCE.value,
            ),
        ),
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
    initial_ts_msm: tuple[Union[int, bool], Union[int, bool], Union[int, bool]]
    """Initial tool settings mesh select mode with which operator was
    initialized"""
    initial_mesh_elements: Literal['edges', 'faces']
    """Mesh elements attribute with which operator retrieves initially selected
    mesh elements. If operator would run in faces mode, it would be ``"faces"``,
    and ``"edges"`` otherwise"""

    prior_ts_msm: tuple[Union[int, bool], Union[int, bool], Union[int, bool]]
    """If operator was initialized with verts or edges tool settings mesh
    selection mode flag enabled and faces flag disabled this attribute would be
    set to ``(False, True, False)`` (edges selection only). If faces flag was
    enabled (in any set of flags), it would be ``(False, False, True)``
    (faces only)
    """
    prior_mesh_elements: Literal['edges', 'faces']
    """If operator was initialized with verts or edges tool settings mesh
    selection mode flag enabled and faces flag disabled this attribute would be
    set to ``"edges"`` (edge selection only). If faces flag was
    enabled (in any set of flags), it would be ``"faces"`` (faces only)
    """

    select_ts_msm: tuple[Union[int, bool], Union[int, bool], Union[int, bool]]
    """If operator was initialized with verts or edges tool settings mesh
    selection mode flag enabled and faces flag disabled this attribute would be
    set to ``(True, False, False)`` (vertices selection only). If faces flag was
    enabled (in any set of flags), it would be ``(False, False, True)``
    (faces only)
    """
    select_mesh_elements: Literal['verts', 'faces']
    """If operator was initialized with verts or edges tool settings mesh
    selection mode flag enabled and faces flag disabled this attribute would be
    set to ``"verts"`` (verts selection only). If faces flag was
    enabled (in any set of flags), it would be ``"faces"`` (faces only)
    """

    # Initial selected mesh elements
    initial_select: tuple[Union[BMVert, BMEdge, BMFace]]

    # BMesh elements caches
    bm_arr: tuple[tuple[Object, BMesh]]

    path_seq: list[Path]
    mesh_islands: list[tuple[Union[BMVert, BMEdge, BMFace]]]
    drag_elem_indices: list[Union[None, int]]
    _active_path_index: int
    _drag_elem: Union[None, BMVert, BMFace]
    _just_closed_path: bool

    undo_history: collections.deque[tuple[int, tuple[Path]]]
    redo_history: collections.deque[tuple[int, tuple[Path]]]

    select_only_arr: dict[Object, tuple[int]]
    markup_arr: dict[Object, tuple[int]]

    @staticmethod
    def _pack_event(item: Union[KeyMapItem, Event]) -> _PackedEvent_T:
        return item.type, item.value, item.alt, item.ctrl, item.shift

    def _eval_meshes(self, context: Context) -> None:
        ret: list[tuple[Object, BMesh]] = list()

        props = context.window_manager.select_path

        for ob in context.objects_in_mode:
            ob: Object

            bm = bmesh.from_edit_mesh(ob.data)
            if self.prior_ts_msm[1]:
                bm.edges.ensure_lookup_table()
            elif self.prior_ts_msm[2]:
                bm.faces.ensure_lookup_table()
                if props.mark_seam != 'NONE' or props.mark_sharp != 'NONE':
                    bm.edges.ensure_lookup_table()
            ret.append((ob, bm))
        self.bm_arr = tuple(ret)

    @property
    def active_path(self) -> Path:
        if self._active_path_index <= len(self.path_seq) - 1:
            return self.path_seq[self._active_path_index]
        return self.path_seq[-1]

    @active_path.setter
    def active_path(self, value: Path) -> None:
        self._active_path_index = self.path_seq.index(value)

    @staticmethod
    def _set_selection_state(elem_seq: tuple[Union[BMVert, BMEdge, BMFace]], state: bool = True) -> None:
        for elem in elem_seq:
            elem.select = state

    def _get_element_by_mouse(self, context: Context, event: Event) -> tuple[
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

    def _get_current_state_copy(self) -> tuple[int, tuple[Path]]:
        return tuple((self._active_path_index, tuple(n.copy() for n in self.path_seq)))

    def _undo(self, context: Context) -> set[Literal['CANCELLED', 'RUNNING_MODAL']]:
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

    def _redo(self, context: Context) -> None:
        if len(self.redo_history) > 0:
            step = self.redo_history.pop()
            self.undo_history.append(step)
            undo_step_active_path_index, undo_step_path_seq = self.undo_history[-1]
            self._active_path_index = undo_step_active_path_index
            self.path_seq = undo_step_path_seq
            context.area.tag_redraw()
        else:
            self.report({'WARNING'}, message="Can not redo anymore")

    def _register_undo_step(self) -> None:
        step = self._get_current_state_copy()
        self.undo_history.append(step)
        self.redo_history.clear()

    def _get_linked_island_index(self, context: Context, elem: Union[BMVert, BMFace]) -> int:
        ts = context.tool_settings

        for i, linked_island in enumerate(self.mesh_islands):
            if elem in linked_island:
                return i

        ts.mesh_select_mode = self.select_ts_msm

        bpy.ops.mesh.select_all(action='DESELECT')
        elem.select_set(True)
        bpy.ops.mesh.select_linked(delimit={'NORMAL'})

        linked_island = self._get_selected_elements(self.select_mesh_elements)

        ts.mesh_select_mode = self.prior_ts_msm

        bpy.ops.mesh.select_all(action='DESELECT')
        self.mesh_islands.append(linked_island)
        return len(self.mesh_islands) - 1

    def _update_meshes(self) -> None:
        for ob, bm in self.bm_arr:
            bm.select_flush_mode()
            bmesh.update_edit_mesh(mesh=ob.data, loop_triangles=False, destructive=False)

    def _update_fills_by_element_index(self, context: Context, path: Path, elem_index: int) -> None:
        ts = context.tool_settings

        pairs_items = path.get_pairs_items(elem_index)
        for item in pairs_items:
            elem_0, elem_1, fill_index = item

            ts.mesh_select_mode = self.select_ts_msm

            bpy.ops.mesh.select_all(action='DESELECT')
            self._set_selection_state((elem_0, elem_1), True)
            bpy.ops.mesh.shortest_path_select(use_topology_distance=bool(path.flag & PathFlag.TOPOLOGY))
            self._set_selection_state((elem_0, elem_1), False)
            fill_seq = self._get_selected_elements(self.prior_mesh_elements)
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
                batch, _ = self._gpu_gen_batch_faces_seq(fill_seq, False, shader)

            path.batch_seq_fills[fill_index] = batch

    def _remove_path_doubles(self, context: Context, path: Path) -> None:
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
                                self._update_fills_by_element_index(context, path, 0)

                                message = "Closed path"
                                if path == self.active_path:
                                    self._just_closed_path = True
                                    message = "Closed active path"
                                self.report(type={'INFO'}, message=message)
                            else:
                                self._update_fills_by_element_index(context, path, 0)
                        # Adjacent control elements
                        elif i in (j - 1, j + 1):
                            path.pop_control_element(j)
                            batch, _ = self._gpu_gen_batch_control_elements(path == self.active_path, path)
                            path.batch_control_elements = batch
                            self.report(type={'INFO'}, message="Merged adjacent control elements")
                        else:
                            # Maybe, undo here?
                            pass

    def _join_adjacent_to_active_path(self) -> None:
        for i, path in enumerate(self.path_seq):
            if (((i != self._active_path_index)  # Skip active path itself
                # Closed pathes can not be merged
                 and (self.active_path.flag ^ PathFlag.CLOSED and path.flag ^ PathFlag.CLOSED))
                and (
                    (self.active_path.control_elements[0] == path.control_elements[0])  # Start to start
                    or (self.active_path.control_elements[-1] == path.control_elements[-1])  # End to end
                    or (self.active_path.control_elements[-1] == path.control_elements[0])  # End to start
                    or (self.active_path.control_elements[0] == path.control_elements[-1])  # Start to end
            )):
                self.active_path += self.path_seq.pop(i)

                batch, _ = self._gpu_gen_batch_control_elements(True, self.active_path)
                self.active_path.batch_control_elements = batch
                self.report(type={'INFO'}, message="Joined two paths")
                break

    def _get_selected_elements(self, mesh_elements: str) -> tuple[Union[BMVert, BMEdge, BMFace]]:
        ret = tuple()

        for _, bm in self.bm_arr:
            elem_arr = getattr(bm, mesh_elements)
            ret += tuple((n for n in elem_arr if n.select))
        return ret

    def _eval_final_element_indices_arrays(self) -> None:
        self.select_only_arr = dict()
        self.markup_arr = dict()

        for ob, bm in self.bm_arr:
            index_select_seq: tuple[int] = tuple()
            index_markup_seq: tuple[int] = tuple()

            print(bm.select_history.active)

            for path in self.path_seq:
                if path.ob == ob:
                    for fill_seq in path.fill_elements:
                        index_select_seq += tuple((n.index for n in fill_seq))
                    if self.prior_ts_msm[1]:
                        index_markup_seq = index_select_seq
                    if self.prior_ts_msm[2]:
                        index_select_seq += tuple((face.index for face in path.control_elements))
                        tmp = path.fill_elements[:]
                        tmp.append(path.control_elements)
                        for fill_seq in tmp:
                            for face in fill_seq:
                                index_markup_seq += tuple((e.index for e in face.edges))
            # Remove duplicates
            self.select_only_arr[ob] = tuple(set(index_select_seq))
            self.markup_arr[ob] = tuple(set(index_markup_seq))

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

    def _gpu_gen_batch_control_elements(self, is_active, path):
        shader = bhqab.gpu_extras.shader.vert_uniform_color

        r_batch = None
        r_active_elem_start_index = None

        if self.prior_ts_msm[1]:
            r_batch = batch_for_shader(shader, 'POINTS', {"pos": tuple((v.co for v in path.control_elements))})
            if is_active:
                r_active_elem_start_index = len(path.control_elements) - 1
        elif self.prior_ts_msm[2]:
            r_batch, r_active_elem_start_index = self._gpu_gen_batch_faces_seq(
                path.control_elements,
                is_active,
                shader
            )

        return r_batch, r_active_elem_start_index

    def _gpu_remove_handle(self) -> None:
        dh = getattr(self, "gpu_handle", None)
        if dh:
            SpaceView3D.draw_handler_remove(dh, 'WINDOW')

    def _gpu_draw_callback(self, context):
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
                shader_ce.uniform_float("colorActive", color_active)
                shader_ce.uniform_int("activeIndex", (active_index,))

                path.batch_control_elements.draw(shader_ce)

    def _interact_control_element(self,
                                  context: Context,
                                  elem: Union[None, BMVert, BMFace],
                                  ob: Object,
                                  interact_event: InteractEvent) -> None:
        props = context.window_manager.select_path

        if elem and interact_event is InteractEvent.ADD_CP:
            if not self.path_seq:
                return self._interact_control_element(context, elem, ob, InteractEvent.ADD_NEW_PATH)

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
                            self._interact_control_element(context, elem, ob, InteractEvent.ADD_CP)
                            return
                else:
                    new_elem_index = fill_index + 1
                    self._just_closed_path = False

            elif len(self.active_path.control_elements) == 1:
                batch, self.active_index = self._gpu_gen_batch_control_elements(True, self.active_path)
                self.active_path.batch_control_elements = batch

            if elem_index is not None:
                self.drag_elem_indices = [path.is_in_control_elements(elem) for path in self.path_seq]
                self._just_closed_path = False
            self._drag_elem = elem

            if self._just_closed_path:
                return self._interact_control_element(context, elem, ob, InteractEvent.ADD_NEW_PATH)

            if new_elem_index is not None:
                linked_island_index = self._get_linked_island_index(context, elem)
                if self.active_path.island_index != linked_island_index:
                    return self._interact_control_element(context, elem, ob, InteractEvent.ADD_NEW_PATH)

                self.active_path.insert_control_element(new_elem_index, elem)
                self._update_fills_by_element_index(context, self.active_path, new_elem_index)

                batch, self.active_index = self._gpu_gen_batch_control_elements(True, self.active_path)
                self.active_path.batch_control_elements = batch

                self.drag_elem_indices = [path.is_in_control_elements(elem) for path in self.path_seq]

        elif elem and interact_event is InteractEvent.ADD_NEW_PATH:
            linked_island_index = self._get_linked_island_index(context, elem)
            new_path = Path(elem, linked_island_index, ob)

            if props.use_topology_distance:
                new_path.flag |= PathFlag.TOPOLOGY

            self.path_seq.append(new_path)
            self.active_path = new_path
            self._just_closed_path = False
            self._interact_control_element(context, elem, ob, InteractEvent.ADD_CP)
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
                        self._interact_control_element(context, elem, ob, InteractEvent.REMOVE_CP)
                        return
            else:
                self.active_path.pop_control_element(elem_index)

                if not len(self.active_path.control_elements):
                    self.path_seq.remove(self.active_path)
                    if len(self.path_seq):
                        self.active_path = self.path_seq[-1]
                else:
                    self._update_fills_by_element_index(context, self.active_path, elem_index)
                    batch, self.active_index = self._gpu_gen_batch_control_elements(True, self.active_path)
                    self.active_path.batch_control_elements = batch

        elif elem and interact_event is InteractEvent.DRAG_CP:
            if (not self._drag_elem) or (len(self.drag_elem_indices) != len(self.path_seq)):
                return
            self._just_closed_path = False

            linked_island_index = self._get_linked_island_index(context, elem)
            if self.active_path.island_index == linked_island_index:
                self._drag_elem = elem

                for i, path in enumerate(self.path_seq):
                    j = self.drag_elem_indices[i]
                    if j is not None:
                        path.control_elements[j] = elem

                        self._update_fills_by_element_index(context, path, j)
                        path.batch_control_elements, self.active_index = self._gpu_gen_batch_control_elements(
                            path == self.active_path,
                            path
                        )

        elif interact_event is InteractEvent.CHANGE_DIRECTION:
            self.active_path.reverse()
            batch, self.active_index = self._gpu_gen_batch_control_elements(True, self.active_path)
            self.active_path.batch_control_elements = batch
            self._just_closed_path = False

        elif interact_event is InteractEvent.CLOSE_PATH:
            self.active_path.flag ^= PathFlag.CLOSED

            if self.active_path.flag & PathFlag.CLOSED:
                self._update_fills_by_element_index(context, self.active_path, 0)
                if len(self.active_path.control_elements) > 2:
                    self._just_closed_path = True
            else:
                self.active_path.fill_elements[-1] = []
                self.active_path.batch_seq_fills[-1] = None
                self._just_closed_path = False
                self._join_adjacent_to_active_path()

        elif interact_event is InteractEvent.TOPOLOGY_DISTANCE:
            self.active_path.flag ^= PathFlag.TOPOLOGY
            for j in range(0, len(self.active_path.control_elements), 2):
                self._update_fills_by_element_index(context, self.active_path, j)

        elif interact_event is InteractEvent.RELEASE_PATH:
            self.drag_elem_indices = []
            self._drag_elem = None

            for path in self.path_seq:
                self._remove_path_doubles(context, path)
            self._join_adjacent_to_active_path()

            self._register_undo_step()

    def draw(self, context: Context) -> None:
        layout = self.layout
        layout.use_property_split = True
        props = context.window_manager.select_path
        props.ui_draw_func(layout)

    def invoke(self, context: bpy.types.Context, event):
        wm = context.window_manager
        props = wm.select_path
        ts = context.scene.tool_settings
        num_undo_steps = context.preferences.edit.undo_steps

        # ____________________________________________________________________ #
        # Input keymaps:

        kc = wm.keyconfigs.user
        km_path_tool = kc.keymaps["3D View Tool: Edit Mesh, Select Path"]
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

        # ____________________________________________________________________ #
        # Initialize variables.

        self.path_seq = list()
        self.mesh_islands = list()
        self.drag_elem_indices = list()

        self._active_path_index = 0
        self._drag_elem = None
        self._just_closed_path = False

        self.undo_history = collections.deque(maxlen=num_undo_steps)
        self.redo_history = collections.deque(maxlen=num_undo_steps)

        self.select_only_arr = dict()
        self.markup_arr = dict()

        # ____________________________________________________________________ #
        # Meshes context setup.
        # Evaluate meshes:

        self.initial_ts_msm = tuple(ts.mesh_select_mode)
        self.initial_mesh_elements = "edges"
        if self.initial_ts_msm[2]:
            self.initial_mesh_elements = "faces"

        self.prior_ts_msm = (False, True, False)
        self.prior_mesh_elements = "edges"
        self.select_ts_msm = (True, False, False)
        self.select_mesh_elements = "verts"
        if self.initial_ts_msm[2]:
            self.prior_ts_msm = (False, False, True)
            self.prior_mesh_elements = "faces"
            self.select_ts_msm = (False, False, True)
            self.select_mesh_elements = "faces"

        self._eval_meshes(context)
        self.initial_select = self._get_selected_elements(self.initial_mesh_elements)

        # Tweak operator settings in case if all mesh elements are already selected
        num_elements_total = 0
        if self.prior_mesh_elements == "edges":
            for _, bm in self.bm_arr:
                num_elements_total += len(bm.edges)
        elif self.prior_mesh_elements == "faces":
            for _, bm in self.bm_arr:
                num_elements_total += len(bm.faces)

        if num_elements_total == len(self.initial_select) and self.mark_select == 'EXTEND':
            self.mark_select = 'NONE'

        # Prevent first click empty space
        elem, _ = self._get_element_by_mouse(context, event)
        if not elem:
            self.cancel(context)
            return {'CANCELLED'}

        STATUSBAR_HT_header.prepend(self._ui_draw_statusbar)

        self.gpu_handle = SpaceView3D.draw_handler_add(self._gpu_draw_callback, (context,), 'WINDOW', 'POST_VIEW')
        wm.modal_handler_add(self)
        self.modal(context, event)
        return {'RUNNING_MODAL'}

    def cancel(self, context: Context):
        ts = context.tool_settings
        ts.mesh_select_mode = self.initial_ts_msm
        self._set_selection_state(self.initial_select, True)
        self._update_meshes()
        self._gpu_remove_handle()
        STATUSBAR_HT_header.remove(self._ui_draw_statusbar)

    def modal(self, context: Context, event: Event):
        ev = self._pack_event(event)
        modal_action = self.modal_events.get(ev, None)
        undo_redo_action = self.undo_redo_events.get(ev, None)
        interact_event = None

        if ev in self.nav_events:
            return {'PASS_THROUGH'}

        elif (
            modal_action == 'CANCEL'
            or InteractEvent.CANCEL.name in self.context_action
        ):
            self.context_action = set()
            self.cancel(context)
            return {'CANCELLED'}

        elif (
            modal_action == 'APPLY'
            or ev == HARDCODED_APPLY_KMI
            or InteractEvent.APPLY_PATHES.name in self.context_action
        ):
            self.context_action = set()

            self._eval_final_element_indices_arrays()
            self._gpu_remove_handle()
            STATUSBAR_HT_header.remove(self._ui_draw_statusbar)
            return self.execute(context)

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

        elif ev == (self.pie_mb, 'PRESS', False, False, False):
            self.is_mouse_pressed = False
            context.window_manager.popup_menu_pie(
                event=event,
                draw_func=self._ui_draw_popup_menu_pie,
                title="Path Tool",
                icon='NONE',
            )

        elif ev == (self.select_mb, 'PRESS', False, False, False):
            self.is_mouse_pressed = True
            interact_event = InteractEvent.ADD_CP

        elif ev == (self.select_mb, 'PRESS', False, False, True):
            self.is_mouse_pressed = True
            interact_event = InteractEvent.ADD_NEW_PATH

        elif ev == (self.select_mb, 'PRESS', False, True, False):
            self.is_mouse_pressed = False
            interact_event = InteractEvent.REMOVE_CP

        elif ev in ((self.select_mb, 'RELEASE', False, False, False),
                    (self.select_mb, 'RELEASE', False, True, False),
                    (self.select_mb, 'RELEASE', False, False, True),
                    ):
            self.is_mouse_pressed = False
            interact_event = InteractEvent.RELEASE_PATH

        if self.is_mouse_pressed:
            if ev[0] == 'MOUSEMOVE':
                interact_event = InteractEvent.DRAG_CP

        if interact_event is not None:
            elem, ob = self._get_element_by_mouse(context, event)
            self._interact_control_element(context, elem, ob, interact_event)

            self._set_selection_state(self.initial_select, True)
            self._update_meshes()

        if not len(self.path_seq):
            self.cancel(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def execute(self, context: Context):
        ts = context.tool_settings
        props = context.window_manager.select_path

        ts.mesh_select_mode = self.prior_ts_msm
        self._eval_meshes(context)
        self.initial_select = self._get_selected_elements(self.prior_mesh_elements)

        for ob, bm in self.bm_arr:
            if ob in self.select_only_arr:
                index_select_seq = self.select_only_arr[ob]
                index_markup_seq = self.markup_arr[ob]
                elem_seq = getattr(bm, self.prior_mesh_elements)

                if (props.skip
                    and (props.mark_select != 'NONE'
                         or props.mark_seam != 'NONE'
                         or props.mark_sharp != 'NONE')):
                    bpy.ops.mesh.select_all(action='DESELECT')

                    for i in index_select_seq:
                        elem_seq[i].select_set(True)

                    # Required for `bpy.ops.mesh.select_nth` call:
                    bm.select_history.clear()
                    bm.select_history.add(elem_seq[i])
                    bpy.ops.mesh.select_nth('EXEC_DEFAULT', skip=props.skip, nth=props.nth, offset=props.offset)

                    index_select_seq = tuple(
                        (n.index for n in self._get_selected_elements(self.prior_mesh_elements))
                    )
                    index_markup_seq = index_select_seq
                    if self.prior_ts_msm[2]:
                        index_markup_seq = tuple(
                            (n.index for n in self._get_selected_elements("edges"))
                        )

                    bpy.ops.mesh.select_all(action='DESELECT')
                    self._set_selection_state(self.initial_select, True)

                if props.mark_select == 'EXTEND':
                    for i in index_select_seq:
                        elem_seq[i].select_set(True)
                elif props.mark_select == 'SUBTRACT':
                    for i in index_select_seq:
                        elem_seq[i].select_set(False)
                elif props.mark_select == 'INVERT':
                    for i in index_select_seq:
                        elem_seq[i].select_set(not elem_seq[i].select)

                if ob in self.markup_arr:
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


class MESH_PT_select_path_context(bpy.types.Panel):
    bl_label = "Options"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'

    def draw(self, context: Context) -> None:
        layout = self.layout
        layout.use_property_split = True
        props = context.window_manager.select_path
        props.ui_draw_func_runtime(layout)
