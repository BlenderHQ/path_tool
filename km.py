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
    km_default = wm.keyconfigs.get("blender").keymaps
    km_addon = wm.keyconfigs.get("blender addon").keymaps

    for keyconfig_data in _generate_tool_keymap():
        km_name, km_args, km_content = keyconfig_data
        km_addon.remove(km_addon.find(km_name, **km_args))

    for keyconfig_data in _generate_empty_keymap():
        km_name, km_args, km_content = keyconfig_data
        km_default.remove(km_default.find(km_name, **km_args))
