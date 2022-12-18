from __future__ import annotations

from typing import Literal, Iterator

import bpy
from bpy.types import (
    Area,
    Context,
    Region,
    Space,
)

from mathutils import Vector

import gpu
from gpu.types import (
    GPUBatch,
    GPUOffScreen,
    GPUShader,
    GPUTexture,
)
from gpu_extras.batch import batch_for_shader

__all__ = (
    "byte_size_fmt",
    "get_viewport_metrics",
    "iter_areas",
    "iter_area_regions",
    "iter_area_spaces",
    "get_depth_map",
    "eval_unit_rect_batch",
    "OffscreenFramework",
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


def iter_areas(context: Context, *, area_type: str = 'VIEW_3D') -> Iterator[Area]:
    """
    Iterator for the area in all open program windows.

    .. code-block:: python
        :emphasize-lines: 1

        for area in iter_areas(bpy.context, area_type='VIEW_3D'):
            print(area)
        ...

    :param context: Current context
    :type context: `Context`_
    :param area_type: Area type. See `Area.type`_, defaults to 'VIEW_3D'
    :type area_type: str, optional
    :yield: Areas iterator
    :rtype: Iterator[`Area`_]
    """
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            area: Area
            if area.type == area_type:
                yield area


def iter_area_regions(*, area: Area, region_type: str = 'WINDOW') -> Iterator[Region]:
    """
    Iterator of regions in an area by type.

    .. code-block:: python
        :emphasize-lines: 2

        area = bpy.context.area
        for region in iter_area_regions(area=area, region_type='WINDOW'):
            print(region)
        ...


    :param area: Processing area
    :type area: `Area`_
    :param region_type: Type of region. See `Region.type`_, defaults to 'WINDOW'
    :type region_type: str, optional
    :yield: Regions iterator
    :rtype: Iterator[`Region`_]
    """
    for region in area.regions:
        region: Region

        if region.type == region_type:
            yield region


def iter_area_spaces(*, area: Area, space_type: str = 'VIEW_3D') -> Iterator[Space]:
    """
    Iterator of spaces in an area by type.

    .. code-block:: python
        :emphasize-lines: 2

        area = bpy.context.area
        for space in iter_area_spaces(area, space_type='VIEW_3D'):
            print(space)
        ...


    :param area: Processing area
    :type area: `Area`_
    :param space_type: Type of space. See `Space.type`_, defaults to 'VIEW_3D'
    :type space_type: str, optional
    :yield: Spaces iterator
    :rtype: Iterator[`Space`_]
    """
    for space in area.spaces:
        space: Space

        if space.type == space_type:
            yield space


def get_depth_map() -> GPUTexture:
    """
    Evaluates the depth texture in the current framebuffer.

    :return: ``DEPTH_COMPONENT32F`` texture (``width``, ``height`` = viewport size)
    :rtype: `GPUTexture`_
    """
    fb = gpu.state.active_framebuffer_get()
    return gpu.types.GPUTexture(
        gpu.state.viewport_get()[2:],
        data=fb.read_depth(*fb.viewport_get()), format='DEPTH_COMPONENT32F')


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


class OffscreenFramework:
    """
    A class to control the creation and destruction of offscreen buffers for each viewport.
    """

    __slots__ = (
        "_regions_offs",
    )

    _regions_offs: dict[Region, GPUOffScreen]

    __used_gpu_memory__: int = 0

    @classmethod
    @property
    def used_gpu_memory(cls) -> int:
        """
        The amount of video memory used by the offscreen buffers created by the module.

        :return: Memory in bytes, readonly
        :rtype: int
        """
        return cls.__used_gpu_memory__

    @classmethod
    @property
    def used_gpu_memory_fmt(cls) -> str:
        """
        The amount of video memory used by the offscreen buffers created by the module.

        :return: Formatted string
        :rtype: str
        """
        return byte_size_fmt(cls.__used_gpu_memory__)

    @staticmethod
    def _eval_offscreen_mem(offscreen: GPUOffScreen) -> int:
        width = offscreen.width
        height = offscreen.height
        channels = 0
        bytes = 0

        match offscreen.texture_color.format:
            case 'RGBA8':
                channels, bytes = 4, 4
            case 'RGBA16' | 'RGBA16F':
                channels, bytes = 4, 8
            case 'RGBA32F':
                channels, bytes = 4, 16

        return width * height * channels * bytes

    @classmethod
    def _create_offscreen(
            cls,
            width: int,
            height: int,
            *,
            format: Literal['RGBA8', 'RGBA16', 'RGBA16F', 'RGBA32F'] = 'RGBA8'
    ) -> GPUOffScreen:
        ret = GPUOffScreen(width, height, format=format)
        cls.__used_gpu_memory__ += cls._eval_offscreen_mem(ret)
        return ret

    @classmethod
    def _free_offscreen(cls, offscreen: GPUOffScreen) -> None:
        cls.__used_gpu_memory__ -= cls._eval_offscreen_mem(offscreen)
        offscreen.free()

    def modal_eval(self, *, format: Literal['RGBA8', 'RGBA16', 'RGBA16F', 'RGBA32F'] = 'RGBA8', percentage: int = 100):
        """
        The class and instance data update method should be called in the modal part of the control operator

        :param format: Required format of data buffers, defaults to 'RGBA8'
        :type format: Literal['RGBA8', 'RGBA16', 'RGBA16F', 'RGBA32F'], optional
        :param percentage: Resolution percentage, defaults to 100
        :type percentage: int, optional
        """
        cls = self.__class__

        invalid_regions = set()
        for region in self._regions_offs.keys():
            is_owning_window_exists = False
            for window in bpy.context.window_manager.windows:
                if window.screen == region.id_data:
                    is_owning_window_exists = True
            if not is_owning_window_exists:
                invalid_regions.add(region)

        for region in invalid_regions:
            cls._free_offscreen(self._regions_offs[region])
            del self._regions_offs[region]

        scale = percentage / 100
        # Ensure all regions have respective offscreens
        for area in iter_areas(bpy.context, area_type='VIEW_3D'):
            for region in iter_area_regions(area=area, region_type='WINDOW'):
                do_update = True
                offscreen = None

                width = int(region.width * scale)
                height = int(region.height * scale)

                if region in self._regions_offs:
                    offscreen = self._regions_offs[region]
                    do_update = not (
                        (offscreen.width == width and offscreen.height == height)
                        and (offscreen.texture_color.format == format)
                    )

                if do_update:
                    if isinstance(offscreen, GPUOffScreen):
                        cls._free_offscreen(offscreen)

                    self._regions_offs[region] = cls._create_offscreen(width=width, height=height, format=format)

    def __init__(self):
        self._regions_offs = dict()

    def __del__(self):
        for offscreen in self._regions_offs.values():
            offscreen.free()

        self._regions_offs.clear()

    def get(self) -> GPUOffScreen:
        """
        Returns the offscreen created for the current region

        :return: Region offscreen
        :rtype: `GPUOffScreen`_
        """
        return self._regions_offs[bpy.context.region]
