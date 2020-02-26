from collections import deque

import bpy
import bmesh

from . import utils

if "_rc" in locals():
    import importlib

    importlib.reload(utils)

_rc = None

InteractEvent = utils.base.InteractEvent


class MESH_OT_select_path(utils.base.PathUtils, bpy.types.Operator):
    """
    Operator class only handle events.
    Methods of path creation and interaction with mesh elements exist inside parent PathUtils class.
    """
    bl_idname = "view3d.select_path"
    bl_label = "Select Path"
    bl_description = "Tool for selecting and marking up mesh object elements"

    bl_options = {'REGISTER', 'UNDO'}

    # Operator properties
    context_action: utils.props.context_action
    context_undo: utils.props.context_undo
    mark_select: utils.props.mark_select
    mark_seam: utils.props.mark_seam
    mark_sharp: utils.props.mark_sharp
    view_center_pick: utils.props.view_center_pick

    # UI draw methods
    draw = utils.ui.operator_draw
    popup_menu_pie_draw = utils.ui.popup_menu_pie_draw

    def invoke(self, context, event):
        wm = context.window_manager

        # Stadard input event keys (type, value, alt, ctrl, shift)
        kc = wm.keyconfigs.user
        self.mouse_buttons = utils.inputs.get_mouse_buttons(wm)
        self.navigation_evkeys = utils.inputs.get_navigation_evkeys(kc)
        self.modal_action_evkeys = utils.inputs.get_modal_action_evkeys(kc)
        self.undo_redo_evkeys = utils.inputs.get_undo_redo_evkeys(kc)

        # Setup mesh select mode
        tool_settings = context.scene.tool_settings
        initial_select_mode = tuple(tool_settings.mesh_select_mode)
        mesh_mode = (False, True, False)
        header_text_mode = "Edge Selection Mode"
        if initial_select_mode[2]:
            mesh_mode = (False, False, True)
            header_text_mode = "Face Selection Mode"
        tool_settings.mesh_select_mode = mesh_mode

        # Bmesh (bpy.types.Object - bmesh.Bmesh) pairs
        self.bm_seq = []
        for ob in context.objects_in_mode:
            self.bm_seq.append((ob, bmesh.from_edit_mesh(ob.data)))

        if initial_select_mode[0]:
            mesh_elements = "verts"
        if initial_select_mode[1]:
            mesh_elements = "edges"
        else:
            mesh_elements = "faces"
        self.initial_select = self.get_selected_elements(mesh_elements)
        self.draw_handle_3d = bpy.types.SpaceView3D.draw_handler_add(
            utils.draw.draw_callback_3d, (self,), 'WINDOW', 'POST_VIEW')
        # Prevent first click empty space
        elem, elem_bm = self.get_element_by_mouse(context, event)
        if not elem:
            tool_settings.mesh_select_mode = initial_select_mode
            self.cancel(context)
            return {'CANCELLED'}
        #
        self.is_mouse_pressed = False
        #
        context.area.header_text_set("Path Tool (%s)" % header_text_mode)
        wm.modal_handler_add(self)

        self.path_seq = []
        self.mesh_islands = []
        self.drag_elem_index = None

        self._active_path_index = None
        self._drag_elem = None
        self._just_closed_path = False

        undo_steps = context.preferences.edit.undo_steps
        self.undo_history = deque(maxlen=undo_steps)
        self.redo_history = deque(maxlen=undo_steps)

        self.modal(context, event)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.draw_handle_3d, 'WINDOW')
        self.set_selection_state(self.initial_select, True)
        self.update_meshes(context)
        context.area.header_text_set(None)
        print("cancelled")

    def modal(self, context, event):
        evkey = utils.inputs.get_evkey(event)
        select_mb, context_mb = self.mouse_buttons
        modal_action = self.modal_action_evkeys.get(evkey, None)
        undo_redo_action = self.undo_redo_evkeys.get(evkey, None)
        interact_event = None

        # Navigation
        if evkey in self.navigation_evkeys:
            return {'PASS_THROUGH'}

        # Cancel
        elif modal_action == 'CANCEL':
            self.cancel(context)
            return {'CANCELLED'}

        # Apply all
        elif (modal_action == 'APPLY') or ('APPLY' in self.context_action):
            self.context_action = set()
            context.area.header_text_set(None)
            bpy.types.SpaceView3D.draw_handler_remove(self.draw_handle_3d, 'WINDOW')
            return {'FINISHED'}

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
            return utils.redo.undo(self, context)

        # Redo
        elif (undo_redo_action == 'REDO') or ('REDO' in self.context_undo):
            self.context_undo = set()
            utils.redo.redo(self, context)

        # Open context pie menu
        elif evkey == (context_mb, 'PRESS', False, False, False):  # Context menu mouse button
            wm = context.window_manager
            wm.popup_menu_pie(event=event, draw_func=self.popup_menu_pie_draw, title='Path Tool', icon='NONE')

        # Select mouse button
        elif evkey == (select_mb, 'PRESS', False, False, False):
            self.is_mouse_pressed = True
            interact_event = InteractEvent.ADD

        # Select mouse button + Shift
        elif evkey == (select_mb, 'PRESS', False, False, True):
            self.is_mouse_pressed = True
            interact_event = InteractEvent.ADD_NEW_PATH

        # Select mouse button + Ctrl
        elif evkey == (select_mb, 'PRESS', False, True, False):
            self.is_mouse_pressed = False
            interact_event = InteractEvent.REMOVE

        # Release select mouse event
        elif evkey in ((select_mb, 'RELEASE', False, False, False),
                       (select_mb, 'RELEASE', False, True, False),
                       (select_mb, 'RELEASE', False, False, True),
                       ):
            self.is_mouse_pressed = False
            interact_event = InteractEvent.RELEASE

        if self.is_mouse_pressed:
            if evkey[0] == 'MOUSEMOVE':
                interact_event = InteractEvent.DRAG

        if interact_event is not None:
            if interact_event in (
                    InteractEvent.ADD,
                    InteractEvent.ADD_NEW_PATH,
                    InteractEvent.DRAG,
                    InteractEvent.REMOVE):
                elem, matrix_world = self.get_element_by_mouse(context, event)
                if elem:
                    self.interact_control_element(context, elem, matrix_world, interact_event)

            elif interact_event in (
                    InteractEvent.RELEASE,
                    InteractEvent.CHDIR,
                    InteractEvent.CLOSE):

                self.interact_control_element(context, None, None, interact_event)
                
                # Register current state after adding new, dragging or removing control elements, pathes
                # or when toggle open/close path or changed path direction
                utils.redo.register_undo_step(self)

        self.set_selection_state(self.initial_select, True)
        self.update_meshes(context)

        # If removed the last control element of the last path
        if not len(self.path_seq):
            self.cancel(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def execute(self, context):
        return {'FINISHED'}
