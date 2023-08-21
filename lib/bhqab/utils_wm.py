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
    Ітератор всіх ділянок необхідного типу у всіх вікнах програми.

    .. code-block:: python
        :emphasize-lines: 1

        for area in iter_areas(bpy.context, area_type='VIEW_3D'):
            print(area)
        ...

    :param context: Поточний контекст.
    :type context: `Context`_
    :param area_type: Тип ділянки. Див. `Area.type`_, за замовчуванням 'VIEW_3D'
    :type area_type: str, опційно
    :yield: Ділянка.
    :rtype: Iterator[`Area`_]
    """
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            area: Area
            if area.type == area_type:
                yield area


def iter_regions(context: Context, *, area_type: str = 'VIEW_3D', region_type: str = 'WINDOW') -> Iterator[Region]:
    """
    Ітератор регіонів в усіх ділянках всіх вікон програми необхідного типу.

    .. code-block:: python
        :emphasize-lines: 1

        for region in iter_regions(bpy.context, area_type='VIEW_3D', region_type='WINDOW'):
            print(region)
        ...

    :param context: Поточний контекст.
    :type context: `Context`_
    :param area_type: Тип ділянок які містять регіони. Див. `Area.type`_, за замовчуванням 'VIEW_3D'
    :type area_type: str, опційно
    :param region_type: Тип регіону. Див. `Region.type`_, за замовчуванням 'WINDOW'
    :type region_type: str, опційно
    :yield: Регіон.
    :rtype: Iterator[`Region`_]
    """
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            area: Area

            if area.type == area_type:
                for region in area.regions:
                    if region.type == region_type:
                        yield region


def iter_area_regions(*, area: Area, region_type: str = 'WINDOW') -> None:
    """
    Ітератор регіонів певного типу одного екземпляру ділянки.

    .. code-block:: python
        :emphasize-lines: 2

        area = bpy.context.area
        for region in iter_area_regions(area=area, region_type='WINDOW'):
            print(region)
        ...

    :param area: Ділянка.
    :type area: `Area`_
    :param region_type: Тип регіону. Див. `Region.type`_, за замовчуванням 'WINDOW'
    :type region_type: str, опційно
    :yield: Регіон.
    :rtype: Iterator[`Region`_]
    """
    for region in area.regions:
        region: Region

        if region.type == region_type:
            yield region


def iter_area_spaces(*, area: Area, space_type: str = 'VIEW_3D') -> Iterator[Space]:
    """
    Ітератор просторів певного типу одного екземпляру ділянки.

    .. code-block:: python
        :emphasize-lines: 2

        area = bpy.context.area
        for space in iter_area_spaces(area, space_type='VIEW_3D'):
            print(space)
        ...


    :param area: Ділянка.
    :type area: `Area`_
    :param space_type: Тип простору. Див. `Space.type`_, за замовчуванням 'VIEW_3D'
    :type space_type: str, опційно
    :yield: Простір.
    :rtype: Iterator[`Space`_]
    """
    for space in area.spaces:
        space: Space

        if space.type == space_type:
            yield space


def tag_redraw_all_regions(*, area_type: str = 'VIEW_3D', region_type: str = 'WINDOW'):
    """
    Виклик `Region.tag_redraw()`_ для кожного регіону необхідного типу в ділянках необхідного типу.

    :param area_type: Тип ділянки (`Area.type`_), за замовчуванням 'VIEW_3D'
    :type area_type: str, опційно
    :param region_type: Тип регіону (`Region.type`_), за замовчуванням 'WINDOW'
    :type region_type: str, опційно
    """
    for area in iter_areas(bpy.context, area_type=area_type):
        for region in iter_area_regions(area=area, region_type=region_type):
            region.tag_redraw()
