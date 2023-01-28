from __future__ import annotations

import bpy
from bpy.types import (
    Context,
    Region,
)

from mathutils import Vector

import gpu
from gpu.types import (
    GPUBatch,
    GPUFrameBuffer,
    GPUShader,
    GPUTexture,
)
from gpu_extras.batch import batch_for_shader

from ... import utils_wm

__all__ = (
    "byte_size_fmt",
    "eval_unit_rect_batch",
    "FrameBufferFramework",
    "get_depth_map",
    "get_viewport_metrics",
    "iter_area_regions",
    "iter_area_spaces",
    "iter_areas",
)


def byte_size_fmt(size: int):
    for suf, lim in (
        ('Tb', 1 << 40),
        ('Gb', 1 << 30),
        ('Mb', 1 << 20),
        ('Kb', 1 << 10),
        ('bytes', 1),
    ):
        if size >= lim:
            return f"{str(int(size / lim))} {suf}"


def get_viewport_metrics() -> Vector:
    """
    Viewport metrics for current viewport.

    :return: x = ``1.0 / width``, y = ``1.0 / height``, z = ``width``, w = ``height``
    :rtype: `Vector`_
    """
    viewport = gpu.state.viewport_get()
    w, h = viewport[2], viewport[3]
    return Vector((1.0 / w, 1.0 / h, w, h))


def get_depth_map(*, depth_format: str = 'DEPTH_COMPONENT32F') -> GPUTexture:
    """
    Evaluates the depth texture in the current framebuffer.

    :return: ``DEPTH_COMPONENT32F`` texture (``width``, ``height`` = viewport size)
    :rtype: `GPUTexture`_
    """
    fb = gpu.state.active_framebuffer_get()
    return gpu.types.GPUTexture(
        gpu.state.viewport_get()[2:],
        data=fb.read_depth(*fb.viewport_get()), format=depth_format
    )


def eval_unit_rect_batch(shader: GPUShader) -> GPUBatch:
    return batch_for_shader(
        shader=shader,
        type='TRIS',
        content={
            "pos": ((-1.0, -1.0), (-1.0, 1.0), (1.0, 1.0), (1.0, -1.0)),
            "texCoord": ((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0)),
        },
        indices=((0, 1, 2), (0, 2, 3))
    )


class FrameBufferFramework:
    __slots__ = (
        "_region_framebuffer",
        "_area_type",
        "_region_type",
    )

    _region_framebuffer: dict[Region, tuple[GPUFrameBuffer, None | GPUTexture, None | GPUTexture]]
    _area_type: str
    _region_type: str

    def __init__(self, *, area_type='VIEW_3D', region_type='WINDOW'):
        self._region_framebuffer = dict()
        self._area_type = area_type
        self._region_type = region_type

    def modal_eval(self, context: Context, *, color_format: str = "", depth_format: str = "", percentage: int = 100):
        existing_regions = set(
            region for region
            in utils_wm.iter_regions(context, area_type=self._area_type, region_type=self._region_type)
        )

        invalid_regions = set(self._region_framebuffer.keys())
        invalid_regions.difference_update(existing_regions)
        for region in invalid_regions:
            del self._region_framebuffer[region]

        scale = max(10, min(400, percentage)) / 100

        for region in existing_regions:
            do_update_texture = True
            do_update_depth_texture = True

            width = int(region.width * scale)
            height = int(region.height * scale)

            if region in self._region_framebuffer:
                _framebuffer, texture, depth_texture = self._region_framebuffer[region]

                do_update_texture = not (
                    (
                        color_format and texture and (
                            texture.width == width
                            and texture.height == height
                            and texture.format == color_format
                        )
                    )
                )

                do_update_depth_texture = not (
                    (
                        depth_format and depth_texture and (
                            depth_texture.width == width
                            and depth_texture.height == height
                            and depth_texture.format == color_format
                        )
                    )
                )

            if do_update_texture or do_update_depth_texture:
                if do_update_texture:
                    if color_format:
                        texture = GPUTexture(size=(width, height), format=color_format)
                    else:
                        texture = None

                if do_update_depth_texture:
                    if depth_format:
                        depth_texture = GPUTexture(size=(width, height), format=depth_format)
                    else:
                        depth_texture = None

                framebuffer = GPUFrameBuffer(color_slots=texture, depth_slot=depth_texture)
                self._region_framebuffer[region] = (framebuffer, texture, depth_texture)

    def get(self) -> None | GPUFrameBuffer:
        if bpy.context.region in self._region_framebuffer:
            return self._region_framebuffer[bpy.context.region][0]
        return None

    def get_color_texture(self) -> None | GPUTexture:
        if bpy.context.region in self._region_framebuffer:
            return self._region_framebuffer[bpy.context.region][1]
        return None

    def get_depth_texture(self) -> None | GPUTexture:
        if bpy.context.region in self._region_framebuffer:
            return self._region_framebuffer[bpy.context.region][2]
        return None
