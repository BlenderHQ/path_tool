import bpy

NAVIGATION_IDNAMES = (
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
    # TODO: Add all navigation operators here
)


def get_evkey(item):
    """Formatted item (event or keymap item) attributes"""
    return item.type, item.value, item.alt, item.ctrl, item.shift


def get_mouse_buttons(wm: bpy.types.WindowManager):
    """Tuple (Select, Open context menu) mouse button"""
    blender_keyconfig_name = "blender"

    # Small fix for Blender 2.93+
    if bpy.app.version[0] == 2 and bpy.app.version[1] >= 93:
        blender_keyconfig_name = "Blender"

    select_mouse = wm.keyconfigs.get(blender_keyconfig_name).preferences.select_mouse
    if select_mouse == 'LEFT':
        return ('LEFTMOUSE', 'RIGHTMOUSE')
    return ('RIGHTMOUSE', 'LEFTMOUSE')


def get_modal_action_evkeys(kc: bpy.types.KeyConfigurations):
    """Dict {evkey: kmi.propvalue} for standard modal operators"""
    km = kc.keymaps["Standard Modal Map"]

    modal_action_evkeys = {}

    for kmi in km.keymap_items:
        evkey = list(get_evkey(kmi))
        evkey[2:5] = False, False, False
        modal_action_evkeys[tuple(evkey)] = kmi.propvalue

    return modal_action_evkeys


def get_undo_redo_evkeys(kc: bpy.types.KeyConfigurations):
    """Dict {evkey: 'UNDO', evkey: 'REDO'}"""
    undo_redo_evkeys = {}
    km = kc.keymaps['Screen']

    kmi = km.keymap_items.find_from_operator(idname='ed.undo')
    undo_redo_evkeys[get_evkey(kmi)] = 'UNDO'

    kmi = km.keymap_items.find_from_operator(idname='ed.redo')
    undo_redo_evkeys[get_evkey(kmi)] = 'REDO'

    return undo_redo_evkeys


def get_navigation_evkeys(kc: bpy.types.KeyConfigurations):
    """List of evkeys currently used for navigation"""
    km = kc.keymaps['3D View']

    navigation_evkeys = []

    for kmi in km.keymap_items:
        # 3D View navigation operators
        if kmi.idname in NAVIGATION_IDNAMES:
            evkey = list(get_evkey(kmi))
            if evkey[0] == 'WHEELINMOUSE':
                evkey[0] = 'WHEELUPMOUSE'
            elif evkey[0] == 'WHEELOUTMOUSE':
                evkey[0] = 'WHEELDOWNMOUSE'
            navigation_evkeys.append(tuple(evkey))

    return navigation_evkeys
