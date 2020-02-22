import bmesh


class Path:
    def __init__(self, elem, linked_island_index, matrix_world):
        self.control_elements = [elem]
        # self.fill_elements[-1] reserved for fill seq from first to the last control element(if path.close)
        self.fill_elements = [[]]
        # Index of mesh elements island in operator
        self.island_index = linked_island_index

        # Model matrix of object on which path is
        self.matrix_world = matrix_world
        # One batch for all control elements
        self.batch_control_elements = None
        # And separate batches for each fill seq. self.batch_seq_fills[-1] reserved for
        self.batch_seq_fills = [None]

        self.close = False

    def __repr__(self):
        batch_seq_fills_formatted = []
        for i, batch in enumerate(self.batch_seq_fills):
            if batch:
                batch_seq_fills_formatted.append("fb_%d" % i)
                continue
            batch_seq_fills_formatted.append(batch)

        ["fb_%d" % i for i in range(len(self.batch_seq_fills))]
        return "Path[%d]:\n    ce: %s\n    fe: %s\n    fb: %s" % (
            id(self),
            str([n.index for n in self.control_elements]),
            str([len(n) for n in self.fill_elements]),
            str(batch_seq_fills_formatted)
        )

    def __add__(self, other):
        assert self.island_index == other.island_index

        for control_element in (self.control_elements[0], self.control_elements[-1]):
            if control_element in (other.control_elements[0], other.control_elements[-1]):
                if len(self.control_elements) > len(other.control_elements):
                    self.control_elements.remove(control_element)
                else:
                    other.control_elements.remove(control_element)

        self.control_elements.extend(other.control_elements)

        return self

    def reverse(self):
        self.control_elements.reverse()
        close_path_fill = self.fill_elements.pop(-1)
        self.fill_elements.reverse()
        self.fill_elements.append(close_path_fill)
        return self

    def is_element_in_fill(self, elem):
        """
        Return's tuple
        (index of fill, index of first element that equal or contains given elem(for edges when given vert))
        in self.fill_elements if element in any fill, otherwise None
        """
        for fill_index, fill_seq in enumerate(self.fill_elements):
            if isinstance(elem, bmesh.types.BMVert):
                for i, edge in enumerate(fill_seq):
                    for vert in edge.verts:
                        if elem == vert:
                            return fill_index, i
            elif isinstance(elem, bmesh.types.BMFace):
                for i, face in enumerate(fill_seq):
                    if elem == face:
                        return fill_index, i

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
        self.fill_elements.pop(elem_index - 1)
        self.batch_seq_fills.pop(elem_index - 1)
        return elem

    def get_pairs_items(self, elem):
        """
        Return's pairs_items list in format:
        pairs_items = [[elem_0, elem_1, fill_index_0],
                       (optional)[elem_0, elem_2, fill_index_1]]
        Used to update fill elements from and to given element
        """
        assert elem in self.control_elements
        pairs_items = []
        if len(self.control_elements) < 2:
            return pairs_items
        elem_index = self.control_elements.index(elem)

        if elem_index == 0:
            # First control element
            pairs_items = [[elem, self.control_elements[1], 0]]
        elif elem_index == len(self.control_elements) - 1:
            # Last control element
            pairs_items = [[elem, self.control_elements[elem_index - 1], elem_index - 1]]
        elif len(self.control_elements) > 2:
            # At least 3 control elements
            pairs_items = [[elem, self.control_elements[elem_index - 1], elem_index - 1],
                           [elem, self.control_elements[elem_index + 1], elem_index]]

        return pairs_items
