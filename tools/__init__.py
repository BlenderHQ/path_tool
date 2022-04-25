if "bpy" in locals():
    from importlib import reload

    if "_mesh" in locals():
        reload(_mesh)

    del reload

import bpy

from . import _mesh

MESH_OT_select_path = _mesh._op_mesh.MESH_OT_select_path
PathToolMesh = _mesh.PathToolMesh
