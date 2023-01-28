from __future__ import annotations

from typing import Iterator

import bpy
from bpy.types import (
    Area,
    Context,
    Region,
    Space,
)

__all__ = (
    "iter_areas",
    "iter_area_regions",
    "iter_area_spaces",
    "tag_redraw_all_regions",
)


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


def iter_regions(context: Context, *, area_type: str = 'VIEW_3D', region_type: str = 'WINDOW') -> Iterator[Region]:
    """
    Iterator of regions of type in areas of type

    .. code-block:: python
        :emphasize-lines: 1

        for region in iter_regions(bpy.context, area_type='VIEW_3D', region_type='WINDOW'):
            print(region)
        ...

    :param context: Current context
    :type context: `Context`_
    :param area_type: Area type. See `Area.type`_, defaults to 'VIEW_3D'
    :type area_type: str, optional
    :param region_type: Type of region. See `Region.type`_, defaults to 'WINDOW'
    :type region_type: str, optional
    :yield: Regions iterator
    :rtype: Iterator[`Region`_]
    """
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            area: Area

            if area.type == area_type:
                for region in area.regions:
                    if region.type == region_type:
                        yield region


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


def tag_redraw_all_regions(*, area_type: str = 'VIEW_3D', region_type: str = 'WINDOW'):
    """
    Call `Region.tag_redraw()`_ for each region of required type in all areas of required type

    :param area_type: `Area.type`_, defaults to 'VIEW_3D'
    :type area_type: str, optional
    :param region_type: `Region.type`_, defaults to 'WINDOW'
    :type region_type: str, optional
    """
    for area in iter_areas(bpy.context, area_type=area_type):
        for region in iter_area_regions(area=area, region_type=region_type):
            region.tag_redraw()
