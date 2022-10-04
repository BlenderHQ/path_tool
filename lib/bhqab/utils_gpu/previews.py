from __future__ import annotations
from typing import Literal

import bpy
from bpy.types import ID

import gpu
from gpu.types import (
    GPUTexture,
)

from .. import utils_id

a: None | GPUTexture


def generate_preview_textures_dict(
        *,
        coll_dict: dict[ID, tuple[a]],
        id_type: Literal['OB', 'MA', 'TE', 'WO', 'LA', 'IM', 'BR', 'GR', 'SCE', 'SCR', 'AC', 'NT'],
        ignore_already_set: bool = False
) -> dict[ID, tuple[a]]:
    """
    A method of creating textures with a preview for different ID types.

    :param coll_dict: Existing or empty dictionary with ID instances as keys, tuples with None or `GPUTexture`_ as
        values
    :type coll_dict: dict[ID, tuple[a]]
    :param id_type: ID type
    :type id_type: Literal['OB', 'MA', 'TE', 'WO', 'LA', 'IM', 'BR', 'GR', 'SCE', 'SCR', 'AC', 'NT']
    :param ignore_already_set: Ignore already set or update existing (more performance-harm), defaults to False
    :type ignore_already_set: bool, optional
    :return: Dictionary with ID instances as keys, tuples with None or `GPUTexture`_ as
        values
    :rtype: dict[ID, tuple[a]]

    .. seealso::

        :class:`bhqab.utils_id.PrvID`
    """
    #
    coll = utils_id.eval_coll_from_type(utils_id.PrvID[id_type])
    r_coll_dict = dict.fromkeys(coll, (None, None))
    r_coll_dict.update(coll_dict)

    for item in coll:
        item: ID

        prv = item.preview

        icon_tex = None
        image_tex = None

        if prv:
            # Icon
            if (not isinstance(r_coll_dict[item][0], GPUTexture)) or ignore_already_set:
                w, h = prv.icon_size
                if w and h:
                    icon_pixels = gpu.types.Buffer('FLOAT', w * h * 4)
                    prv.icon_pixels_float.foreach_get(icon_pixels)
                    icon_tex = GPUTexture(size=(w, h), format='RGBA8', data=icon_pixels)
            # Preview
            if (not isinstance(r_coll_dict[item][1], GPUTexture)) or ignore_already_set:
                w, h = prv.image_size
                if w and h:
                    image_pixels = gpu.types.Buffer('FLOAT', w * h * 4)
                    prv.image_pixels_float.foreach_get(image_pixels)
                    image_tex = GPUTexture(size=(w, h), format='RGBA8', data=image_pixels)
        r_coll_dict[item] = icon_tex, image_tex
    return r_coll_dict
