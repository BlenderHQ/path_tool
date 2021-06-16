# <pep8 compliant>

import bpy

from . import operators

km_path_tool_name = "3D View Tool: Edit Mesh, Path Tool"

_keymaps = []


def _generate_empty_keymap():
    return [
        (
            km_path_tool_name,
            {"space_type": 'VIEW_3D', "region_type": 'WINDOW'},
            {"items": []},
        ),
    ]


def _generate_tool_keymap():
    # TODO: find a way to get wm.keyconfigs.get("blender").preferences.select_mouse here
    # For now operator anyway started only by left mouse
    return [
        (
            km_path_tool_name,
            {"space_type": 'VIEW_3D', "region_type": 'WINDOW'},
            {"items": [
                (operators.MESH_OT_select_path.bl_idname, {
                 "type": 'LEFTMOUSE', "value": 'PRESS'}, None),
            ]},
        ),
    ]


def register():
    from bl_keymap_utils.io import keyconfig_init_from_data

    wm = bpy.context.window_manager
    kc = wm.keyconfigs
    kc_default = kc.default
    kc_addon = kc.addon

    keyconfig_init_from_data(kc_default, _generate_empty_keymap())
    keyconfig_init_from_data(kc_addon, _generate_tool_keymap())


def unregister():
    wm = bpy.context.window_manager

    blender_keyconfig_name = "blender"
    blender_addon_keyconfig_name = "blender addon"

    # Small fix for Blender 2.93+
    if bpy.app.version[0] == 2 and bpy.app.version[1] >= 93:
        blender_keyconfig_name = "Blender"
    blender_addon_keyconfig_name = "Blender addon"

    print([_.name for _ in wm.keyconfigs])

    km_default = wm.keyconfigs.get(blender_keyconfig_name).keymaps
    km_addon = wm.keyconfigs.get(blender_addon_keyconfig_name).keymaps

    for keyconfig_data in _generate_tool_keymap():
        km_name, km_args, km_content = keyconfig_data
        km_addon.remove(km_addon.find(km_name, **km_args))

    for keyconfig_data in _generate_empty_keymap():
        km_name, km_args, km_content = keyconfig_data
        km_default.remove(km_default.find(km_name, **km_args))
