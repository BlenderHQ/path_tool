from collections import deque

import bpy
import bmesh
import gpu
import bgl
from gpu_extras.batch import batch_for_shader

import time

from . import utils


class MESH_OT_select_path1(bpy.types.Operator):
    bl_idname = "view3d.select_path"
    bl_label = "Select Path"
    bl_description = "Tool for selecting and marking up mesh object elements"

    bl_options = {'REGISTER', 'UNDO'}

    # Operator properties
    def context_action_update(self, context):
        print(self.context_action)

    mark_select: bpy.props.EnumProperty(
        items=[
            ('EXTEND', "Extend", "Extend existing selection", 'SELECT_EXTEND', 1),
            ('NONE', "Do nothing", "Do nothing", "X", 2),
            ('SUBTRACT', "Subtract", "Subtract existing selection", 'SELECT_SUBTRACT', 3),
            ('INVERT', "Invert", "Inverts existing selection", 'SELECT_DIFFERENCE', 4)
        ],
        name="Select",
        default='EXTEND',
        description="Selection options"
    )

    mark_seam: bpy.props.EnumProperty(
        items=[
            ('MARK', "Mark", "Mark seam path elements", 'RESTRICT_SELECT_OFF', 1),
            ('NONE', "Do nothing", "Do nothing", 'X', 2),
            ('CLEAR', "Clear", "Clear seam path elements", 'RESTRICT_SELECT_ON', 3),
            ('TOGGLE', "Toggle", "Toggle seams on path elements", 'ACTION_TWEAK', 4)
        ],
        name="Seams",
        default='NONE',
        description="Mark seam options"
    )

    mark_sharp: bpy.props.EnumProperty(
        items=[
            ('MARK', "Mark", "Mark sharp path elements", 'RESTRICT_SELECT_OFF', 1),
            ('NONE', "Do nothing", "Do nothing", 'X', 2),
            ('CLEAR', "Clear", "Clear sharp path elements", 'RESTRICT_SELECT_ON', 3),
            ('TOGGLE', "Toogle", "Toogle sharpness on path", 'ACTION_TWEAK', 4)
        ],
        name="Sharp",
        default="NONE",
        description="Mark sharp options"
    )

    view_center_pick: bpy.props.BoolProperty(
        name="Focus Active",
        default=True,
        description="Center the view to the position of the active control point"
    )

    context_action: bpy.props.EnumProperty(
        items=[
            (
                'CLPATH', "Close Path",
                "Close the path from the first to the last control point",
                '', 2
            ),
            (
                'CHDIR', "Change direction",
                "Changes the direction of the path",
                '', 4
            ),
            (
                'APPLY', "Apply All",
                "Apply all paths and make changes to the mesh",
                '', 8
            ),
        ],
        options={'ENUM_FLAG'},
        default=set(),
        update=context_action_update
    )

    context_undo: bpy.props.EnumProperty(
        items=[
            ('UNDO', "Undo", "Undo one step", 'LOOP_BACK', 2),
            ('REDO', "Redo", "Redo one step", 'LOOP_FORWARDS', 4),
        ],
        options={'ENUM_FLAG'},
        default=set()
    )

    fill_gap: bpy.props.BoolProperty(
        name="Fill Gap",
        description="Fill gap beetween first and last control points",
        default=False)

    mouse_reverse: bpy.props.BoolProperty(
        name="Switch Direction",
        description="Switch path direction",
        default=False)

    popup_menu_pie_draw = utils.ui.popup_menu_pie_draw

    #####################################################

    def create_batch_control_points(self):
        preferences = bpy.context.preferences.addons[__package__].preferences
        color_active = preferences.color_active_control_point
        color_control_point = preferences.color_control_point
        color_face_center = color_control_point

        matrix_world = bpy.context.active_object.matrix_world
        control_vertices = [elem for elem in self.control_elements if type(elem) == bmesh.types.BMVert]
        control_faces = [elem for elem in self.control_elements if type(elem) == bmesh.types.BMFace]

        if control_vertices:
            vert_positions = [matrix_world @ v.co for v in control_vertices]
            vert_colors = []
            for vertex in control_vertices:
                if self.fill_gap is False or len(self.control_elements) <= 2:
                    if vertex == self.control_elements[-1]:
                        vert_colors.append(color_active)
                    else:
                        vert_colors.append(color_control_point)
                else:
                    vert_colors.append(color_control_point)

            self.batch_cp_verts = batch_for_shader(self.shader, 'POINTS', {"pos": vert_positions, "color": vert_colors})

        if control_faces:
            temp_bmesh = bmesh.new()
            for face in control_faces:
                temp_bmesh.faces.new((temp_bmesh.verts.new(v.co, v) for v in face.verts), face)
            temp_bmesh.verts.index_update()
            temp_bmesh.faces.ensure_lookup_table()

            vert_positions = [matrix_world @ v.co for v in temp_bmesh.verts]
            face_indices = [(loop.vert.index for loop in looptris) for looptris
                            in temp_bmesh.calc_loop_triangles()]

            face_centers = [matrix_world @ f.calc_center_median() for f in temp_bmesh.faces]
            face_center_colors = [color_face_center for f in temp_bmesh.faces]

            vert_colors = []
            for vertex in temp_bmesh.verts:
                if self.fill_gap is False or len(self.control_elements) <= 2:
                    if vertex in temp_bmesh.faces[-1].verts:
                        vert_colors.append(color_active)
                    else:
                        vert_colors.append(color_control_point)
                else:
                    vert_colors.append(color_control_point)

            self.batch_cp_faces = batch_for_shader(self.shader, 'TRIS',
                                                   {"pos": vert_positions, "color": vert_colors}, indices=face_indices)

            self.batch_cp_verts = batch_for_shader(self.shader, 'POINTS',
                                                   {"pos": face_centers, "color": face_center_colors})

    def create_batch_path(self, path):

        color_fill = (0.0, 0.7, 1.0, 0.7)

        matrix_world = bpy.context.active_object.matrix_world

        if self.mesh_elements == "faces":
            temp_bmesh = bmesh.new()
            for face in path:
                temp_bmesh.faces.new((temp_bmesh.verts.new(v.co, v) for v in face.verts), face)
            temp_bmesh.verts.index_update()
            temp_bmesh.faces.ensure_lookup_table()

            vert_positions = [matrix_world @ v.co for v in temp_bmesh.verts]
            face_indices = [(loop.vert.index for loop in looptris) for looptris in temp_bmesh.calc_loop_triangles()]
            vert_colors = [color_fill for _ in range(len(temp_bmesh.verts))]

            self.batch_path = batch_for_shader(self.shader, 'TRIS',
                                               {"pos": vert_positions, "color": vert_colors}, indices=face_indices)

        elif self.mesh_elements == "edges":
            vert_positions = []
            vert_colors = []
            for edge in path:
                for vert in edge.verts:
                    vert_positions.append(matrix_world @ vert.co)
                    vert_colors.append(color_fill)
            self.batch_path = batch_for_shader(self.shader, 'LINES',
                                               {"pos": vert_positions, "color": vert_colors})

    def draw_callback_3d(self, context):

        print("self.draw_callback_3d", time.time())

        vertex_size = 2.0
        edge_width = 3.0

        bgl.glPointSize(vertex_size)
        bgl.glLineWidth(edge_width)

        bgl.glEnable(bgl.GL_MULTISAMPLE)
        bgl.glEnable(bgl.GL_LINE_SMOOTH)
        bgl.glHint(bgl.GL_LINE_SMOOTH_HINT, bgl.GL_NICEST)

        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)
        bgl.glEnable(bgl.GL_BLEND)

        bgl.glEnable(bgl.GL_POLYGON_SMOOTH)
        bgl.glHint(bgl.GL_POLYGON_SMOOTH_HINT, bgl.GL_NICEST)

        bgl.glEnable(bgl.GL_DEPTH_TEST)
        bgl.glDepthFunc(bgl.GL_ALWAYS)

        self.shader.bind()

        if self.batch_path:
            self.batch_path.draw(self.shader)

        if self.batch_cp_faces:
            self.batch_cp_faces.draw(self.shader)

        if self.batch_cp_verts:
            self.batch_cp_verts.draw(self.shader)
    #####################################################

    def mesh_select_mode(self, context):
        initial_mesh_select_mode = tuple(context.scene.tool_settings.mesh_select_mode)

        if initial_mesh_select_mode[0] or initial_mesh_select_mode[1]:
            self.select_mode = (True, False, False)
            self.mesh_mode = (False, True, False)
            self.mesh_elements = "edges"
            if initial_mesh_select_mode != self.mesh_mode:
                self.report({'INFO'}, message="Select mode changed to Edges only")

        if initial_mesh_select_mode[2]:
            self.select_mode = (False, False, True)
            self.mesh_mode = (False, False, True)
            self.mesh_elements = "faces"
            if initial_mesh_select_mode != self.mesh_mode:
                self.report({'INFO'}, message="Select mode changed to Faces only")

        context.scene.tool_settings.mesh_select_mode = self.mesh_mode

    def chech_first_click(self, context, event):
        elem = self.get_element_by_mouse(context, event)
        if elem:
            return True
        return False

    def register_handlers(self, context):
        # return
        wm = context.window_manager
        wm.modal_handler_add(self)
        self.draw_handle_3d = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_callback_3d, (context,), 'WINDOW', 'POST_VIEW')

    def unregister_handlers(self, context):
        # return
        bpy.types.SpaceView3D.draw_handler_remove(self.draw_handle_3d, 'WINDOW')

    def create_bmesh(self, context):
        mesh = context.edit_object.data
        self.bm = bmesh.from_edit_mesh(mesh)
        for n in (self.bm.verts, self.bm.edges, self.bm.faces):
            n.ensure_lookup_table()

    def update_mesh(self, context):
        self.bm.select_flush_mode()
        bmesh.update_edit_mesh(context.active_object.data, False, False)
        context.scene.tool_settings.mesh_select_mode = self.mesh_mode

    def get_element_by_mouse(self, context, event):
        context.scene.tool_settings.mesh_select_mode = self.select_mode
        #
        mouse_location = (event.mouse_region_x, event.mouse_region_y)
        ret = bpy.ops.view3d.select(location=mouse_location)
        elem = None
        if 'FINISHED' in ret:
            elem = self.bm.select_history.active

            if len(self.control_elements) == 0:
                bpy.ops.mesh.select_linked_pick(deselect=False, delimit={'NORMAL'}, index=elem.index)

                self.path_on_indices = [n.index for n
                                        in [v for v in self.bm.verts if v.select]]
                self.deselect_all()
            if elem:
                elem.select_set(False)

        context.scene.tool_settings.mesh_select_mode = self.mesh_mode

        if elem:
            if elem.index in self.path_on_indices:
                return elem
            else:
                self.report({'INFO'}, message="Can't make path on another part of mesh")

    def switch_direction(self):
        self.control_elements.reverse()
        self.fill_elements.reverse()
        self.create_batches()

    def drag_element_by_mouse(self, elem):
        if self.drag_element:
            if self.drag_element in self.control_elements:
                if self.drag_element_index is not None:
                    self.control_elements[self.drag_element_index] = elem

        if self.drag_element is None:
            self.drag_element = elem
            if self.drag_element in self.control_elements:
                self.drag_element_index = self.control_elements.index(elem)

        elif self.drag_element != elem:
            self.drag_element = elem

        if self.drag_element_index is not None:
            self.update_by_element(self.drag_element_index)

    def on_click(self, elem, remove=False):
        if remove is False:
            if elem not in self.control_elements:
                if elem in self.get_fill_points():
                    ii = self.get_fillelements_index(elem)
                    self.control_elements.insert(ii + 1, elem)
                    self.fill_elements.insert(ii, [])
                else:
                    self.control_elements.append(elem)
                    if len(self.control_elements) > 1:
                        self.fill_elements.append([])
                    ii = len(self.control_elements) - 1
                self.update_by_element(ii)
        else:
            self.remove_element(elem)

    def remove_element(self, elem):
        if elem in self.control_elements:
            self.control_elements.remove(elem)
            self.full_path_update()

    def full_path_update(self):
        """`Update path from every second control point"""
        self.fill_elements = [[] for n in range(len(self.control_elements) - 1)]
        for ii in list(range(len(self.control_elements)))[::2]:
            self.update_by_element(ii)
        self.set_selection(self.original_select)

    def update_by_element(self, elem_ind):
        """Update path from and to element by given index"""
        ll = len(self.control_elements)
        if ((elem_ind > (ll - 1)) or (ll < 2)):
            self.create_batches()
            return
        elem = self.control_elements[elem_ind]

        if elem_ind == 0:
            pairs = [[elem, self.control_elements[1], 0]]
        elif elem_ind == len(self.control_elements) - 1:
            pairs = [[elem, self.control_elements[elem_ind - 1], elem_ind - 1]]
        else:
            pairs = [[elem,
                      self.control_elements[elem_ind - 1],
                      elem_ind - 1],
                     [elem,
                      self.control_elements[elem_ind + 1],
                      elem_ind]]

        for pair in pairs:
            p1, p2, fii = pair
            if p1 == p2:
                self.fill_elements[fii] = list()
                continue

            fill = self.update_path_beetween_two(p1, p2)
            self.fill_elements[fii] = fill
            bpy.context.scene.tool_settings.mesh_select_mode = self.mesh_mode

        self.update_fill_path()

        self.create_batches()

    def update_path_beetween_two(self, p1, p2):
        bpy.context.scene.tool_settings.mesh_select_mode = self.select_mode
        self.deselect_all()
        self.set_selection((p1, p2), True)
        bpy.ops.mesh.shortest_path_select()
        self.set_selection((p1, p2), False)
        fill = self.get_selected_elements()
        self.deselect_all()
        if self.mesh_elements == "edges":
            if fill == []:  # Exception if control points in one edge
                for edge in p1.link_edges:
                    if edge.other_vert(p1) == p2:
                        fill = list([edge])
        return fill

    def update_fill_path(self):
        if len(self.control_elements) > 2 and self.fill_gap is True:
            p1 = self.control_elements[0]
            p2 = self.control_elements[-1]
            if p1 != p2:
                fill = self.update_path_beetween_two(p1, p2)
                if len(fill) > 0:
                    self.fill_gap_path = fill
            bpy.context.scene.tool_settings.mesh_select_mode = self.mesh_mode
        else:
            self.fill_gap_path = list()

    def deselect_all(self):
        bpy.ops.mesh.select_all(action='DESELECT')

    def set_selection(self, elements, status=True):
        for elem in elements:
            elem.select_set(status)

    def get_fills(self):
        fills = []
        for n in self.fill_elements:
            for elem in n:
                fills.append(elem)
        fills += self.fill_gap_path
        return fills

    def get_fillelements_index(self, elem):
        if self.mesh_elements == "edges":
            for fill in self.fill_elements:
                for edge in fill:
                    if elem in edge.verts:
                        ind = self.fill_elements.index(fill)
                        return ind
        elif self.mesh_elements in ("verts", "faces"):
            for fill in self.fill_elements:
                for n in fill:
                    if elem == n:
                        ind = self.fill_elements.index(fill)
                        return ind

    def get_fill_points(self):
        fills = []
        if self.mesh_elements == "edges":
            for elem in self.fill_elements:
                for edge in elem:
                    for v in edge.verts:
                        fills.append(v)
        elif self.mesh_elements in ("verts", "faces"):
            for n in self.fill_elements:
                for elem in n:
                    fills.append(elem)
        return fills

    def get_selected_elements(self):
        return [n for n in getattr(self.bm, self.mesh_elements) if n.select]

    def prepare_for_execute(self, context):
        self.confirm_path = False
        # final_list = self.control_elements + self.get_fills() + self.fill_gap_path
        path = self.get_path()
        for elem in path:
            ii = elem.index
            if ii not in self.path_indices:
                self.path_indices.append(ii)

        self.set_selection(self.original_select)
        self.update_mesh(context)

    def get_path(self):
        path = []
        pl = self.fill_elements + [self.fill_gap_path]
        if self.mesh_elements == "faces":
            pl.extend([self.control_elements])
        for n in pl:
            for elem in n:
                if elem not in path:
                    path.append(elem)
        return path

    def check_doubles(self, context):
        """Check doubles in control points"""
        for n in range(len(self.control_elements) - 1):
            dou = []
            for ii in range(len(self.control_elements)):
                if self.control_elements[ii] == self.control_elements[n]:
                    dou.append(ii)
            if len(dou) > 1:
                p1, p2 = dou
                ll = len(self.control_elements) - 1

                if (p1 == 0 and p2 == ll) and (self.fill_gap is False) and (ll > 2):
                    self.remove_element(self.control_elements[p2])
                    self.fill_gap = True
                    self.report({'INFO'}, message="Fill cap")

                elif p2 in (p1 + 1, p1 - 1, p1) or (p1 == 0 and p2 == ll):
                    self.remove_element(self.control_elements[p2])
                    self.report({'INFO'}, message="Merged 2 overlapping control points")
                else:
                    self.undo(context)
                    self.report({'INFO'}, message="You should not duplicate control points, undo")

    def create_batches(self):
        path = self.get_path()
        self.create_batch_path(path)
        self.create_batch_control_points()

    def undo(self, context):
        if len(self.undo_history) == 1:
            self.cancel(context)
            return {'CANCELLED'}
        if len(self.undo_history) > 1:
            step = self.undo_history.pop()
            self.redo_history.append(step)
            self.control_elements = self.undo_history[-1].copy()
            self.full_path_update()
        else:
            self.report({'WARNING'}, message="Can't undo anymore")

        return {"RUNNING_MODAL"}

    def redo(self):
        if len(self.redo_history) > 0:
            step = self.redo_history.pop()
            self.undo_history.append(step)
            self.control_elements = self.undo_history[-1].copy()
            self.full_path_update()
        else:
            self.report({'WARNING'}, message="Can't redo anymore")

    def register_undo_step(self):
        step = self.control_elements.copy()
        self.undo_history.append(step)
        self.redo_history.clear()

    # Operator methods

    def invoke(self, context, event):
        print("self.invoke", time.time())
        wm = context.window_manager
        kc = wm.keyconfigs.user

        # Stadard input event keys (type, value, alt, ctrl, shift)
        self.navigation_evkeys = utils.inputs.get_navigation_evkeys(kc)
        self.modal_action_evkeys = utils.inputs.get_modal_action_evkeys(kc)

        self.batch_cp_faces = None
        self.batch_cp_verts = None
        self.batch_path = None
        self.drag_element = None
        self.drag_element_index = None
        self.mouse_press = None
        self.mouse_remove = None
        self.drag = None

        self.control_elements = []
        self.fill_elements = []
        self.path_indices = []
        self.fill_gap_path = []

        self.fill_gap = False

        ###########################################
        self.create_bmesh(context)
        self.mesh_select_mode(context)

        self.original_select = self.get_selected_elements()
        self.shader = gpu.shader.from_builtin('3D_SMOOTH_COLOR')  # TODO: my own shader

        if not self.chech_first_click(context, event):
            return {'CANCELLED'}

        self.undo_max_steps = 10
        self.undo_history = deque(maxlen=self.undo_max_steps)
        self.redo_history = deque(maxlen=self.undo_max_steps)

        self.register_handlers(context)

        self.modal(context, event)

        ###########################################
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        self.deselect_all()
        self.set_selection(self.original_select, True)
        self.update_mesh(context)
        self.unregister_handlers(context)

    def modal(self, context, event):

        if event.type == 'ESC':
            self.cancel(context)
            return {'CANCELLED'}

        if context.area:
            context.area.tag_redraw()

        print("self.modal", time.time())

        wm = context.window_manager

        evkey = utils.inputs.get_evkey(event)

        modal_action = self.modal_action_evkeys.get(evkey, None)

        print(modal_action)

        if modal_action == 'CANCEL':
            self.cancel(context)
            return {'CANCELLED'}

        elif modal_action == 'APPLY':
            # self.prepare_for_execute(context)
            # self.execute(context)
            self.unregister_handlers(context)
            print("""return {'FINISHED'}""")
            return {'FINISHED'}

        elif evkey in self.navigation_evkeys:
            return {'PASS_THROUGH'}

        elif evkey == ('RIGHTMOUSE', 'PRESS', False, False, False):
            wm.popup_menu_pie(event=event, draw_func=self.popup_menu_pie_draw, title='Path Tool', icon='NONE')

        elif evkey == ('LEFTMOUSE', 'PRESS', False, False, False):
            self.mouse_press = True

        elif evkey == ('LEFTMOUSE', 'PRESS', False, True, False):
            self.mouse_remove = True
            self.mouse_press = False

        elif evkey in (
            ('LEFTMOUSE', 'RELEASE', False, True, False),
            ('LEFTMOUSE', 'RELEASE', False, False, False),
        ):
            self.drag = False
            self.mouse_press = False
            self.mouse_remove = False
            self.register_undo_step()
            self.check_doubles(context)
            self.drag_element = None
            self.drag_element_index = None

        elif modal_action in ('SNAP', 'SNAP_OFF'):
            self.fill_gap = (not self.fill_gap)
            self.update_fill_path()

        ##############################
        if self.mouse_reverse:
            self.switch_direction()

        if self.mouse_remove:
            elem = self.get_element_by_mouse(context, event)
            if elem:
                self.on_click(elem, True)

        if self.mouse_press:
            elem = self.get_element_by_mouse(context, event)
            if elem:
                if evkey == ('MOUSEMOVE', 'PRESS', False, False, False):
                    self.drag = True

                if self.drag:
                    self.drag_element_by_mouse(elem)
                else:
                    self.on_click(elem, False)

        self.mouse_reverse = False

        self.should_update = True

        if self.should_update:
            self.should_update = False
            self.update_fill_path()
            self.create_batches()

        self.set_selection(self.original_select)
        self.bm.select_flush_mode()
        ##############################

        return {'RUNNING_MODAL'}

    def execute(self, context):

        if context.area:
            context.area.tag_redraw()

        self.create_bmesh(context)

        elems = getattr(self.bm, self.mesh_elements)
        path = [elem for elem
                in elems if elem.index in self.path_indices]
        for elem in path:
            if self.mark_select == "EXTEND":
                elem.select_set(True)
            elif self.mark_select == "SUBTRACT":
                elem.select_set(False)
            elif self.mark_select == "INVERT":
                elem.select_set((not elem.select))
        if self.mesh_elements == "edges":
            edges = path
        if self.mesh_elements == "faces":
            edges = []
            for elem in path:
                for edge in elem.edges:
                    if edge not in edges:
                        edges.append(edge)
        for elem in edges:
            if self.mark_seam == "MARK":
                elem.seam = True
            elif self.mark_seam == "CLEAR":
                elem.seam = False
            elif self.mark_seam == "TOGGLE":
                elem.seam = (not elem.seam)

            if self.mark_sharp == "MARK":
                elem.smooth = False
            elif self.mark_sharp == "CLEAR":
                elem.smooth = True
            elif self.mark_sharp == "TOGGLE":
                elem.smooth = (not elem.smooth)

        self.update_mesh(context)

        return {'FINISHED'}
