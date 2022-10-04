import bpy

addon_pref = bpy.context.preferences.addons["path_tool"].preferences

addon_pref.color_control_element = (0.8, 0.8, 0.8)
addon_pref.color_active_control_element = (0.039087, 0.331906, 0.940392)
addon_pref.color_path = (0.593397, 0.708376, 0.634955)
addon_pref.color_path_topology = (1.0, 0.952328, 0.652213)
addon_pref.color_active_path = (0.304987, 0.708376, 0.450786)
addon_pref.color_active_path_topology = (1.0, 0.883791, 0.152213)
addon_pref.point_size = 3
addon_pref.line_width = 3
