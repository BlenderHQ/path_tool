# Path Tool addon.
# Copyright (C) 2020-2023  Vlad Kuzmin (ssh4), Ivan Perevala (ivpe)

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

bl_info = {
    "name": "Path Tool",
    "author": "Vlad Kuzmin (ssh4), Ivan Perevala (ivpe)",
    "version": (3, 6, 2),
    "blender": (3, 6, 2),
    "location": "Toolbar",
    "description": "Tool for selecting and marking up mesh object elements",
    "category": "Mesh",
    "support": 'COMMUNITY',
    "doc_url": "https://github.com/BlenderHQ/path-tool",
}

import os

ADDON_PKG = __package__
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
INFO_DIR = os.path.join(DATA_DIR, "info")

if "bpy" in locals():
    from importlib import reload

    reload(bhqab)
    reload(bhqglsl)
    reload(pref)
    reload(main)
    reload(props)
    reload(localization)
else:
    from .lib import bhqab
    from .lib import bhqglsl
    from . import pref
    from . import main
    from . import props
    from . import localization


import bpy
from bpy.types import (
    Context,
    UILayout,
    WindowManager,
    WorkSpaceTool,
)
from bpy.props import (
    PointerProperty,
)
from bpy.app.handlers import persistent


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from . props import WMProps


class PathToolMesh(WorkSpaceTool):
    bl_idname = "mesh.path_tool"
    bl_label = "Select Path"
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'
    bl_options = {}
    bl_description = "Select items using editable paths"
    bl_icon = os.path.join(DATA_DIR, "ops.mesh.path_tool")
    bl_keymap = (
        (
            main.MESH_OT_select_path.bl_idname,
            dict(
                type='LEFTMOUSE',
                value='PRESS',
                shift=True,
            ),
            dict(
                properties=[("action", main.InteractEvent.ADD_NEW_PATH.name), ]
            )
        ),
        (
            main.MESH_OT_select_path.bl_idname,
            dict(
                type='LEFTMOUSE',
                value='PRESS',
                ctrl=True,
            ),
            dict(
                properties=[("action", main.InteractEvent.REMOVE_CP.name), ]
            )
        ),
        (
            main.MESH_OT_select_path.bl_idname,
            dict(
                type='T',
                value='PRESS',
            ),
            dict(
                properties=[("action", main.InteractEvent.TOPOLOGY_DISTANCE.name), ]
            )
        ),
        (
            main.MESH_OT_select_path.bl_idname,
            dict(
                type='D',
                value='PRESS',
            ),
            dict(
                properties=[("action", main.InteractEvent.CHANGE_DIRECTION.name), ]
            )
        ),
        (
            main.MESH_OT_select_path.bl_idname,
            dict(
                type='C',
                value='PRESS',
            ),
            dict(
                properties=[("action", main.InteractEvent.CLOSE_PATH.name), ]
            )
        ),
        (
            main.MESH_OT_select_path.bl_idname,
            dict(
                type='Z',
                value='PRESS',
                shift=True,
                ctrl=True,
            ),
            dict(
                properties=[("action", main.InteractEvent.REDO.name), ]
            )
        ),
        (
            main.MESH_OT_select_path.bl_idname,
            dict(
                type='Z',
                value='PRESS',
                ctrl=True,
            ),
            dict(
                properties=[("action", main.InteractEvent.UNDO.name), ]
            )
        ),
        (
            main.MESH_OT_select_path.bl_idname,
            dict(
                type='ESC',
                value='PRESS',
            ),
            dict(
                properties=[("action", main.InteractEvent.CANCEL.name), ]
            )
        ),
        (
            main.MESH_OT_select_path.bl_idname,
            dict(
                type='SPACE',
                value='PRESS',
            ),
            dict(
                properties=[("action", main.InteractEvent.APPLY_PATHS.name), ]
            )
        ),
        (
            main.MESH_OT_select_path.bl_idname,
            dict(
                type='RET',
                value='PRESS',
            ),
            dict(
                properties=[("action", main.InteractEvent.APPLY_PATHS.name), ]
            )
        ),
        (
            main.MESH_OT_select_path.bl_idname,
            dict(
                type='RIGHTMOUSE',
                value='PRESS',
            ),
            dict(
                properties=[("action", main.InteractEvent.PIE.name), ]
            )
        ),
        (
            main.MESH_OT_select_path.bl_idname,
            dict(
                type='LEFTMOUSE',
                value='PRESS',
            ),
            dict(
                properties=[("action", main.InteractEvent.NONE.name), ]
            )
        ),
        (
            main.MESH_OT_select_path.bl_idname,
            dict(
                type='LEFTMOUSE',
                value='PRESS',
            ),
            dict(
                properties=[("action", main.InteractEvent.ADD_CP.name), ]
            )
        ),
    )

    @staticmethod
    def draw_settings(context: Context, layout: UILayout, tool: WorkSpaceTool):
        wm_props: WMProps = context.window_manager.select_path
        layout.enabled = not wm_props.is_runtime
        wm_props.ui_draw_func_runtime(layout)


@persistent
def load_post(_unused):
    bhqab.utils_ui.copy_default_presets_from(
        src_root=os.path.join(DATA_DIR, "presets")
    )


_classes = (
    pref.Preferences,
    pref.PREFERENCES_MT_path_tool_appearance_preset,
    pref.PREFERENCES_OT_path_tool_appearance_preset,

    props.WMProps,
    props.MESH_MT_select_path_presets,
    props.MESH_OT_select_path_preset_add,

    main.MESH_OT_select_path,
    main.MESH_PT_select_path_context,
)

_cls_register, _cls_unregister = bpy.utils.register_classes_factory(classes=_classes)

_handlers = (
    (bpy.app.handlers.load_post, load_post),
)


def register():
    _cls_register()
    WindowManager.select_path = PointerProperty(type=props.WMProps)
    bpy.utils.register_tool(PathToolMesh, after={"builtin.select_lasso"}, separator=False, group=False)

    bpy.app.translations.register(ADDON_PKG, localization.LANGS)

    for handler, func in _handlers:
        if func not in handler:
            handler.append(func)


def unregister():
    for handler, func in _handlers:
        if func not in handler:
            handler.remove(func)

    bpy.app.translations.unregister(ADDON_PKG)

    bpy.utils.unregister_tool(PathToolMesh)
    del WindowManager.select_path
    _cls_unregister()
