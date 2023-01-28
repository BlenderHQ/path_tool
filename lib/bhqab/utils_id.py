from __future__ import annotations
from enum import (
    auto,
    Enum,
)

import bpy

__all__ = (
    "PrvID",
    "prop_prv_id_items",
    "eval_coll_from_type",
    "eval_name_from_type",
)


# TODO: Keep up-to-date with `BKE_previewimg_id_get_p`

class PrvID(Enum):
    """
    Types that can contain a preview

    :cvar Enum OB: `Object`_
    :cvar Enum MA: `Material`_
    :cvar Enum TE: `Texture`_
    :cvar Enum WO: `World`_
    :cvar Enum LA: `Lamp`_
    :cvar Enum IM: `Image`_
    :cvar Enum BR: `Brush`_
    :cvar Enum GR: `GreasePencil`_
    :cvar Enum SCE: `Scene`_
    :cvar Enum SCR: `Screen`_
    :cvar Enum AC: `Action`_
    :cvar Enum NT: `NodeTree`_

    """
    OB = auto()
    MA = auto()
    TE = auto()
    WO = auto()
    LA = auto()
    IM = auto()
    BR = auto()
    GR = auto()
    SCE = auto()
    SCR = auto()
    AC = auto()
    NT = auto()


def prop_prv_id_items() -> tuple[tuple[str, str, str]]:
    """
    Items for an enum property that contains information about IDs that may contain previews.

    :return: Result tuple, for non-UI purposes only
    :rtype: tuple[tuple[str, str, str]]
    """
    return tuple(((_, _, "") for _ in PrvID.__members__))


def eval_coll_from_type(type: PrvID) -> None | bpy.types.bpy_prop_collection:
    """
    Evaluates the required collection from Blender data based on the ID type.

    :param type: Required ID type
    :type type: :class:`PrvID`

    :return: ``None`` if the specified enumerator does not contain a preview
    :rtype: None | `bpy_prop_collection`_
    """
    match type:
        case PrvID.OB:
            return bpy.data.objects
        case PrvID.MA:
            return bpy.data.materials
        case PrvID.TE:
            return bpy.data.textures
        case PrvID.WO:
            return bpy.data.worlds
        case PrvID.LA:
            return bpy.data.lights
        case PrvID.IM:
            return bpy.data.images
        case PrvID.BR:
            return bpy.data.brushes
        case PrvID.GR:
            return bpy.data.grease_pencils
        case PrvID.SCE:
            return bpy.data.scenes
        case PrvID.SCR:
            return bpy.data.screens
        case PrvID.AC:
            return bpy.data.actions
        case PrvID.NT:
            return bpy.data.node_groups
    return None


def eval_name_from_type(type: PrvID) -> str:
    """
    A capital-case string with the human-readable name of the data type.

    :param type: Required ID type
    :type type: :class:`PrvID`

    :return: Name
    :rtype: str
    """
    match type:
        case PrvID.OB:
            return "Object"
        case PrvID.MA:
            return "Material"
        case PrvID.TE:
            return "Texture"
        case PrvID.WO:
            return "World"
        case PrvID.LA:
            return "Light"
        case PrvID.IM:
            return "Image"
        case PrvID.BR:
            return "Brush"
        case PrvID.GR:
            return "Grease pencil"
        case PrvID.SCE:
            return "Scene"
        case PrvID.SCR:
            return "Screen"
        case PrvID.AC:
            return "Action"
        case PrvID.NT:
            return "Node group"

    return ""
