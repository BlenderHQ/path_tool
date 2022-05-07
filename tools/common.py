from __future__ import annotations
from typing import Union
from enum import auto, IntFlag

from bpy.types import Object
from bmesh.types import BMVert, BMEdge, BMFace
from gpu.types import GPUBatch
import bmesh


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
