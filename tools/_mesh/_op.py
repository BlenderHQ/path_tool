import collections

import bpy
from bpy.types import (
    Context,
    Operator,
    SpaceView3D,
    STATUSBAR_HT_header,
)
from bpy.props import (
    EnumProperty,
    BoolProperty
)

from . import _utils
from . import _utils_gpu
from ..common import InteractEvent


class MESH_OT_select_path(Operator,
                          _utils.MeshOperatorUtils,
                          _utils_gpu.MeshOperatorGPUUtils):
    bl_idname = "mesh.path_tool"
    bl_label = "Select Path"
    bl_options = {'REGISTER', 'UNDO'}

    __slots__ = (
        "select_mb",
        "pie_mb",
        "modal_events",
        "undo_redo_events",
        "nav_events",
        "is_mouse_pressed",
        "is_navigation_active",

        "initial_ts_msm",
        "initial_mesh_elements",
        "prior_ts_msm",
        "prior_mesh_elements",
        "select_ts_msm",
        "select_mesh_elements",
        "initial_select",

        "bm_arr",
        "path_seq",
        "mesh_islands",
        "drag_elem_indices",

        "_active_path_index",
        "_drag_elem",
        "_just_closed_path",

        "undo_history",
        "redo_history",

        "select_only_seq",
        "markup_seq",
    )

    context_action: EnumProperty(
        items=(
            (
                InteractEvent.CHANGE_DIRECTION.name,
                "Change direction",
                "Changes the direction of the path",
                'CON_CHILDOF',
                InteractEvent.CHANGE_DIRECTION.value,
            ),
            (
                InteractEvent.CLOSE_PATH.name,
                "Close Path",
                "Close the path from the first to the last control point",
                'MESH_CIRCLE',
                InteractEvent.CLOSE_PATH.value,
            ),
            (
                InteractEvent.CANCEL.name,
                "Cancel",
                "Cancel editing pathes",
                'EVENT_ESC',
                InteractEvent.CANCEL.value,
            ),
            (
                InteractEvent.APPLY_PATHES.name,
                "Apply All",
                "Apply all paths and make changes to the mesh",
                'EVENT_RETURN',
                InteractEvent.APPLY_PATHES.value,
            ),
            (
                InteractEvent.UNDO.name,
                "Undo",
                "Undo previous interaction",
                'LOOP_BACK',
                InteractEvent.UNDO.value,
            ),
            (
                InteractEvent.REDO.name,
                "Redo",
                "Redo previous undo",
                'LOOP_FORWARDS',
                InteractEvent.REDO.value,
            ),
            (
                InteractEvent.TOPOLOGY_DISTANCE.name,
                "Use Topology Distance",
                "Find the minimum number of steps, ignoring spatial distance",
                'DRIVER_DISTANCE',
                InteractEvent.TOPOLOGY_DISTANCE.value,
            ),
        ),
        default=set(),
        options={'ENUM_FLAG', 'HIDDEN', 'SKIP_SAVE'},
    )

    mark_select: EnumProperty(
        items=(
            ('EXTEND', "Extend", "Extend existing selection", 'SELECT_EXTEND', 1),
            ('NONE', "Do nothing", "Do nothing", "X", 2),
            ('SUBTRACT', "Subtract", "Subtract existing selection", 'SELECT_SUBTRACT', 3),
            ('INVERT', "Invert", "Inverts existing selection", 'SELECT_DIFFERENCE', 4),
        ),
        default='EXTEND',
        options={'HIDDEN', 'SKIP_SAVE'},
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
        options={'HIDDEN', 'SKIP_SAVE'},
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

    use_topology_distance: BoolProperty(
        default=False,
        options={'HIDDEN', 'SKIP_SAVE'},
        name="Topology Distance",
        description="Find the minimum number of steps, ignoring spatial distance",
    )

    def invoke(self, context: bpy.types.Context, event):
        wm = context.window_manager
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
        self.is_navigation_active = False

        # ____________________________________________________________________ #
        # Initialize variables.

        self.path_seq = list()
        self.mesh_islands = list()
        self.drag_elem_indices = list()

        self._active_path_index = None
        self._drag_elem = None
        self._just_closed_path = False

        self.undo_history = collections.deque(maxlen=num_undo_steps)
        self.redo_history = collections.deque(maxlen=num_undo_steps)

        self.select_only_seq = dict()
        self.markup_seq = dict()

        # ____________________________________________________________________ #
        # Meshes context setup.
        # Evaluate meshes:
        self.bm_arr = self._eval_meshes(context)

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

        self.initial_select = self.get_selected_elements(self.initial_mesh_elements)

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
        elem, _ = self.get_element_by_mouse(context, event)
        if not elem:
            self.cancel(context)
            return {'CANCELLED'}

        STATUSBAR_HT_header.prepend(self.draw_statusbar)

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
        STATUSBAR_HT_header.remove(self.draw_statusbar)

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

        elif (
            modal_action == 'CANCEL'
            or InteractEvent.CANCEL.name in self.context_action
        ):
            self.context_action = set()
            self.cancel(context)
            return {'CANCELLED'}

        elif (
            modal_action == 'APPLY'
            or ev == _utils.HARDCODED_APPLY_KMI
            or InteractEvent.APPLY_PATHES.name in self.context_action
        ):
            self.context_action = set()

            self.gen_final_elements_seq(context)
            self.remove_gpu_handle()
            STATUSBAR_HT_header.remove(self.draw_statusbar)
            return self.execute(context)

        elif (
            InteractEvent.CLOSE_PATH.name in self.context_action
            or ev == _utils.HARDCODED_CLOSE_PATH_KMI
        ):
            self.context_action = set()
            interact_event = InteractEvent.CLOSE_PATH

        elif (
            InteractEvent.CHANGE_DIRECTION.name in self.context_action
            or ev == _utils.HARDCODED_CHANGE_DIRECTION_KMI
        ):
            self.context_action = set()
            interact_event = InteractEvent.CHANGE_DIRECTION

        elif (
            InteractEvent.TOPOLOGY_DISTANCE.name in self.context_action
            or ev == _utils.HARDCODED_TOPOLOGY_DISTANCE_KMI
        ):
            self.context_action = set()
            interact_event = InteractEvent.TOPOLOGY_DISTANCE

        elif (undo_redo_action == 'UNDO') or (InteractEvent.UNDO.name in self.context_action):
            self.context_action = set()
            return self.undo(context)

        elif (undo_redo_action == 'REDO') or (InteractEvent.REDO.name in self.context_action):
            self.context_action = set()
            self.redo(context)

        elif ev == (self.pie_mb, 'PRESS', False, False, False):
            context.window_manager.popup_menu_pie(
                event=event,
                draw_func=self.draw_popup_menu_pie,
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