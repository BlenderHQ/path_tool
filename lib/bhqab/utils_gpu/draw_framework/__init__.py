from __future__ import annotations

from typing import Literal


from bpy.props import (
    EnumProperty,
)

import gpu
from gpu.types import (
    GPUBatch,
    GPUShader,
    GPUTexture,
)

from . import _aa_base
from . import _offscreen_framework
from . import fxaa
from . import smaa

__all__ = (
    "AAPreset",
    "IDENTITY_M4X4",
    # "byte_size_fmt",
    "iter_areas",
    "iter_area_regions",
    "iter_area_spaces",
    "get_depth_map",
    "get_viewport_metrics",
    "OffscreenFramework",
    "DrawFramework",
    "AABase",
    "SMAA",
    "FXAA",
)

AAPreset = _aa_base.AAPreset
AABase = _aa_base.AABase
IDENTITY_M4X4 = _aa_base.IDENTITY_M4X4
"""Identity matrix 4x4"""

iter_areas = _offscreen_framework.iter_areas
iter_area_regions = _offscreen_framework.iter_area_regions
iter_area_spaces = _offscreen_framework.iter_area_spaces
get_depth_map = _offscreen_framework.get_depth_map
get_viewport_metrics = _offscreen_framework.get_viewport_metrics
OffscreenFramework = _offscreen_framework.OffscreenFramework
SMAA = smaa.SMAA
FXAA = fxaa.FXAA


class DrawFramework:
    """
    A framework for operations with several offscreens in several viewports with anti-aliasing support
    """
    __slots__ = (
        "_aa_instance",
        "_off_frameworks",
    )

    __aa_methods_registry__: set[_aa_base.AABase] = set()

    _aa_instance: None | _aa_base.AABase
    _off_frameworks: tuple[OffscreenFramework]

    __shader_2d_image__: GPUShader = gpu.shader.from_builtin(shader_name='2D_IMAGE')  # type: ignore
    __unit_rect_batch__: GPUBatch = _offscreen_framework.eval_unit_rect_batch(__shader_2d_image__)

    @classmethod
    @property
    def prop_aa_method(cls) -> EnumProperty:  # type: ignore
        return EnumProperty(
            items=tuple(((_.name, _.name, _.description) for _ in cls.__aa_methods_registry__)),
            options={'HIDDEN', 'SKIP_SAVE'},
            name="AA Method",
            description="Anti-aliasing method to be used",
        )

    @classmethod
    def register_aa_method(cls, method_class: _aa_base.AABase):
        cls.__aa_methods_registry__.add(method_class)

    @property
    def aa_method(self) -> str:
        if self._aa_instance is None:
            return 'NONE'
        return self._aa_instance.name

    @aa_method.setter
    def aa_method(self, value: str):
        cls = self.__class__

        if (not self._aa_instance) or (self._aa_instance and self._aa_instance.name != value):
            for item in cls.__aa_methods_registry__:
                if item.name == value:
                    self._aa_instance = item()

    @property
    def aa(self):
        return self._aa_instance

    def get(self, *, index: int):
        return self._off_frameworks[index].get()

    def modal_eval(self, *, format: Literal['RGBA8', 'RGBA16', 'RGBA16F', 'RGBA32F'] = 'RGBA8', percentage: int = 100):
        """
        The class and instance data update method should be called in the modal part of the control operator

        :param format: Required format of data buffers, defaults to 'RGBA8'
        :type format: Literal['RGBA8', 'RGBA16', 'RGBA16F', 'RGBA32F'], optional
        :param percentage: Resolution percentage, defaults to 100
        :type percentage: int, optional
        """
        for item in self._off_frameworks:
            item.modal_eval(format=format, percentage=percentage)
        if self._aa_instance:
            self._aa_instance.modal_eval(format=format, percentage=percentage)

    def __init__(self, *, num_offscreens: int = 1):
        self._aa_instance = None
        self._off_frameworks = tuple((_offscreen_framework.OffscreenFramework() for _ in range(num_offscreens)))

    def draw(self, *, texture: GPUTexture) -> None:
        """
        Draw method

        :param texture: Input texture
        :type texture: `GPUTexture`_
        """
        cls = self.__class__

        mvp_restore = gpu.matrix.get_projection_matrix() @ gpu.matrix.get_model_view_matrix()

        if (self._aa_instance is None) or (self._aa_instance._preset is AAPreset.NONE):
            with gpu.matrix.push_pop():  # type: ignore
                gpu.matrix.load_matrix(IDENTITY_M4X4)
                gpu.matrix.load_projection_matrix(IDENTITY_M4X4)
                gpu.state.blend_set('ALPHA_PREMULT')

                shader = cls.__shader_2d_image__
                shader.uniform_sampler("image", texture)

                cls.__unit_rect_batch__.draw(shader)
        else:
            self._aa_instance.draw(texture=texture)

        gpu.matrix.load_matrix(mvp_restore)


DrawFramework.register_aa_method(FXAA)
DrawFramework.register_aa_method(SMAA)