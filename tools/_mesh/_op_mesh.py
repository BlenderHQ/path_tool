from collections import deque

import bpy
import bgl
from bpy.types import Operator, SpaceView3D, Context
from bpy.props import EnumProperty

from . import _op_mesh_utils
from . import _op_mesh_utils_gpu
from ..common import InteractEvent


class MESH_OT_select_path(Operator,
                          _op_mesh_utils.MeshOperatorUtils,
                          _op_mesh_utils_gpu.MeshOperatorGPUUtils):
    bl_idname = "mesh.path_tool"
    bl_label = "Path Tool"
    bl_options = {'REGISTER', 'UNDO'}

    context_action: EnumProperty(
        items=(
            ('TCLPATH', "Toggle Close Path", "Close the path from the first to the last control point", '', 2),
            ('CHDIR', "Change direction", "Changes the direction of the path", '', 4),
            ('APPLY', "Apply All", "Apply all paths and make changes to the mesh", '', 8),
        ),
        options={'ENUM_FLAG'},
        default=set(),
    )

    context_undo: EnumProperty(
        items=(
            ('UNDO', "Undo", "Undo one step", 'LOOP_BACK', 2),
            ('REDO', "Redo", "Redo one step", 'LOOP_FORWARDS', 4),
        ),
        options={'ENUM_FLAG'},
        default=set(),
        name="Action History",
    )

    mark_select: EnumProperty(
        items=(
            ('EXTEND', "Extend", "Extend existing selection", 'SELECT_EXTEND', 1),
            ('NONE', "Do nothing", "Do nothing", "X", 2),
            ('SUBTRACT', "Subtract", "Subtract existing selection", 'SELECT_SUBTRACT', 3),
            ('INVERT', "Invert", "Inverts existing selection", 'SELECT_DIFFERENCE', 4),
        ),
        default='EXTEND',
        name="Select",
        description="Selection options",
    )

    mark_seam: EnumProperty(
        items=(
            ('MARK', "Mark", "Mark seam path elements", 'RESTRICT_SELECT_OFF', 1),
            ('NONE', "Do nothing", "Do nothing", 'X', 2),
            ('CLEAR', "Clear", "Clear seam path elements", 'RESTRICT_SELECT_ON', 3),
            ('TOGGLE', "Toggle", "Toggle seams on path elements", 'ACTION_TWEAK', 4),
        ),
        default='NONE',
        name="Seams",
        description="Mark seam options",
    )

    mark_sharp: EnumProperty(
        items=(
            ('MARK', "Mark", "Mark sharp path elements", 'RESTRICT_SELECT_OFF', 1),
            ('NONE', "Do nothing", "Do nothing", 'X', 2),
            ('CLEAR', "Clear", "Clear sharp path elements", 'RESTRICT_SELECT_ON', 3),
            ('TOGGLE', "Toggle", "Toggle sharpness on path", 'ACTION_TWEAK', 4),
        ),
        default="NONE",
        name="Sharp",
        description="Mark sharp options",
    )

    def invoke(self, context: bpy.types.Context, event):
        wm = context.window_manager
        ts = context.scene.tool_settings
        num_undo_steps = context.preferences.edit.undo_steps

        # ____________________________________________________________________ #
        # Input keymaps:

        kc = wm.keyconfigs.user
        km_path_tool = kc.keymaps["3D View Tool: Edit Mesh, Path Tool"]
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
        self.is_navigation_active = False

        # ____________________________________________________________________ #
        # Initialize variables.

        self.path_seq = list()
        self.mesh_islands = list()
        self.drag_elem_indices = list()

        self._active_path_index = None
        self._drag_elem = None
        self._just_closed_path = False

        self.undo_history = deque(maxlen=num_undo_steps)
        self.redo_history = deque(maxlen=num_undo_steps)

        self.select_only_seq = dict()
        self.markup_seq = dict()

        # ____________________________________________________________________ #
        # Meshes context setup.
        # Evaluate meshes:
        self.bm_arr = self._eval_meshes(context)

        self.initial_ts_msm = tuple(ts.mesh_select_mode)
        if self.initial_ts_msm[2]:
            self.initial_mesh_elements = "faces"
        if self.initial_ts_msm[0]:
            self.initial_mesh_elements = "verts"
        elif self.initial_ts_msm[1]:
            self.initial_mesh_elements = "edges"

        self.prior_ts_msm = (False, True, False)
        self.prior_mesh_elements = "edges"
        self.select_ts_msm = (True, False, False)
        self.select_mesh_elements = "verts"
        if self.initial_ts_msm[2]:
            self.prior_ts_msm = (False, False, True)
            self.prior_mesh_elements = "faces"
            self.select_ts_msm = (False, False, True)
            self.select_mesh_elements = "faces"

        # Get initial selection state of mesh elements (see description above).
        self.initial_select = self.get_selected_elements(self.initial_mesh_elements)

        # Prevent first click empty space
        elem, _ = self.get_element_by_mouse(context, event)
        if not elem:
            self.cancel(context)
            return {'CANCELLED'}

        self.gpu_handle = SpaceView3D.draw_handler_add(self.draw_callback_3d, (context,), 'WINDOW', 'POST_VIEW')
        wm.modal_handler_add(self)
        self.modal(context, event)
        return {'RUNNING_MODAL'}

    def cancel(self, context: Context):
        ts = context.tool_settings
        ts.mesh_select_mode = self.initial_ts_msm
        self.set_selection_state(self.initial_select, True)
        self.update_meshes()
        self.remove_gpu_handle()

    def modal(self, context, event):
        ev = self._pack_event(event)
        modal_action = self.modal_events.get(ev, None)
        undo_redo_action = self.undo_redo_events.get(ev, None)
        interact_event = None

        if ev in self.nav_events:
            return {'PASS_THROUGH'}

        elif self.is_navigation_active and event.value == 'RELEASE':
            self.is_navigation_active = False
            self.set_selection_state(self.initial_select, True)
            self.update_meshes()
            return {'RUNNING_MODAL'}

        elif modal_action == 'CANCEL':
            self.cancel(context)
            return {'CANCELLED'}

        elif (modal_action == 'APPLY') or ('APPLY' in self.context_action):
            self.context_action = set()

            self.gen_final_elements_seq(context)
            self.remove_gpu_handle()
            return self.execute(context)

        elif 'TCLPATH' in self.context_action:
            self.context_action = set()
            interact_event = InteractEvent.CLOSE

        elif 'CHDIR' in self.context_action:
            self.context_action = set()
            interact_event = InteractEvent.CHDIR

        elif (undo_redo_action == 'UNDO') or ('UNDO' in self.context_undo):
            self.context_undo = set()
            return self.undo(context)

        elif (undo_redo_action == 'REDO') or ('REDO' in self.context_undo):
            self.context_undo = set()
            self.redo(context)

        elif ev == (self.pie_mb, 'PRESS', False, False, False):
            context.window_manager.popup_menu_pie(
                event=event,
                draw_func=self.popup_menu_pie_draw,
                title="Path Tool",
                icon='NONE'
            )

        elif ev == (self.select_mb, 'PRESS', False, False, False):
            self.is_mouse_pressed = True
            interact_event = InteractEvent.ADD

        elif ev == (self.select_mb, 'PRESS', False, False, True):
            self.is_mouse_pressed = True
            interact_event = InteractEvent.ADD_NEW_PATH

        elif ev == (self.select_mb, 'PRESS', False, True, False):
            self.is_mouse_pressed = False
            interact_event = InteractEvent.REMOVE

        elif ev in ((self.select_mb, 'RELEASE', False, False, False),
                    (self.select_mb, 'RELEASE', False, True, False),
                    (self.select_mb, 'RELEASE', False, False, True),
                    ):
            self.is_mouse_pressed = False
            interact_event = InteractEvent.RELEASE

        if self.is_mouse_pressed:
            if ev[0] == 'MOUSEMOVE':
                interact_event = InteractEvent.DRAG

        if interact_event is not None:
            elem, ob = self.get_element_by_mouse(context, event)
            self.interact_control_element(context, elem, ob, interact_event)

            self.set_selection_state(self.initial_select, True)
            self.update_meshes()

        if not len(self.path_seq):
            self.cancel(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def execute(self, context):
        tool_settings = context.scene.tool_settings
        initial_select_mode = tuple(tool_settings.mesh_select_mode)
        if initial_select_mode[0]:
            tool_settings.mesh_select_mode = (False, True, False)

        self._eval_meshes(context)

        for ob, bm in self.bm_arr:
            ptr = ob.as_pointer()

            if self.mark_select != 'NONE':
                if ptr not in self.select_only_seq:
                    print("Not found object %s in self.select_only_seq! This should never happen." % ob.name)
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
                print("Not found object %s in self.markup_seq! This should never happen." % ob.name)
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

        self.update_meshes()
        return {'FINISHED'}
