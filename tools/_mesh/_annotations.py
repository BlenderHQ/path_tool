import collections
from typing import (
    Union,
    Literal
)
from bpy.types import (
    Object,
)
from bmesh.types import (
    BMesh,
    BMVert,
    BMEdge,
    BMFace
)
from ..common import (
    PathFlag,
    Path
)

_PackedEvent_T = tuple[
    Union[int, str], Union[int, str],
    Union[int, bool], Union[int, bool], Union[int, bool]]


class MeshOperatorVariables:

    # ________________________________________________________________________ #
    select_mb: Literal['LEFTMOUSE', 'RIGHTMOUSE']
    pie_mb: Literal['LEFTMOUSE', 'RIGHTMOUSE']
    modal_events: dict[_PackedEvent_T, str]
    undo_redo_events: dict[_PackedEvent_T, str]
    nav_events: tuple[tuple[_PackedEvent_T]]
    is_mouse_pressed: bool
    is_navigation_active: bool

    # ________________________________________________________________________ #
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

    # ________________________________________________________________________ #
    # BMesh elements caches
    bm_arr: tuple[tuple[Object, BMesh]]

    # ________________________________________________________________________ #
    path_seq: list[Path]
    mesh_islands: list[tuple[Union[BMVert, BMEdge, BMFace]]]
    drag_elem_indices: list[Union[None, int]]
    _active_path_index: Union[None, int]
    _drag_elem: Union[None, BMVert, BMFace]
    _just_closed_path: bool
    # ________________________________________________________________________ #
    undo_history: collections.deque[tuple[int, tuple[Path]]]
    redo_history: collections.deque[tuple[int, tuple[Path]]]

    # ________________________________________________________________________ #
    select_only_seq: dict  # TODO
    markup_seq: dict  # TODO
