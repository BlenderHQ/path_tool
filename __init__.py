bl_info = {
    "name": "Path Tool",
    "author": "Vlad Kuzmin (ssh4), Ivan Perevala (vanyOk)",
    "version": (1, 1, 0),
    "blender": (2, 80, 0),
    "location": "Toolbar",
    "description": "Tool for selecting and marking up mesh object elements",
    "category": "3D View",
    "doc_url": "https://github.com/BlenderHQ/path-tool"
}

import bpy

from . import km
from . import tool
from . import shaders
from . import operators
from . import preferences

if "_rc" in locals():
    import importlib

    _unregister_cls()

    importlib.reload(km)
    importlib.reload(tool)
    importlib.reload(shaders)
    importlib.reload(operators)
    importlib.reload(preferences)

    _register_cls()

_rc = None

_classes = [
    preferences.PathToolPreferences,
    operators.MESH_OT_select_path,
]

_register_cls, _unregister_cls = bpy.utils.register_classes_factory(classes=_classes)


def register():
    _register_cls()

    tool.register()
    km.register()


def unregister():
    km.unregister()
    tool.unregister()

    _unregister_cls()
