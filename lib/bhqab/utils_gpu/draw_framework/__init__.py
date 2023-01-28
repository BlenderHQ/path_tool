from __future__ import annotations

from typing import Literal

from bpy.types import (
    Context,
)

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
from . import _framebuffer_framework
from . import fxaa
from . import smaa

__all__ = (
    "AAPreset",
    "IDENTITY_M4X4",
    "get_depth_map",
    "get_viewport_metrics",
    "FrameBufferFramework",
    "DrawFramework",
    "AABase",
    "SMAA",
    "FXAA",
)

AAPreset = _aa_base.AAPreset
AABase = _aa_base.AABase
IDENTITY_M4X4 = _aa_base.IDENTITY_M4X4
"""Identity matrix 4x4"""

get_depth_map = _framebuffer_framework.get_depth_map
get_viewport_metrics = _framebuffer_framework.get_viewport_metrics

FrameBufferFramework = _framebuffer_framework.FrameBufferFramework
SMAA = smaa.SMAA
FXAA = fxaa.FXAA


class DrawFramework:
    """
    Framework for working with framebuffers. Designed to simplify work in several open windows with all possible
    viewports in them. The essence of working with the framework is to create the required number of framebuffers for
    each viewport, if necessary with the buffers for anti-aliasing (depends on the selected options).

    :ivar str aa_method: Anti-aliasing method
    :aa AABase aa: Anti-aliasing method class instance
    """

    __slots__ = (
        "_aa_instance",
        "_fb_frameworks",
    )

    __aa_methods_registry__: set[AABase] = set()

    _aa_instance: None | AABase
    _fb_frameworks: tuple[FrameBufferFramework]

    __shader_2d_image__: GPUShader = gpu.shader.from_builtin(shader_name='2D_IMAGE')  # type: ignore
    __unit_rect_batch__: GPUBatch = _framebuffer_framework.eval_unit_rect_batch(__shader_2d_image__)

    @classmethod
    @property
    def prop_aa_method(cls) -> EnumProperty:  # type: ignore
        """
        :return: Property for use in user preferences
        :rtype: `EnumProperty`_
        """
        return EnumProperty(
            items=tuple(((_.name, _.name, _.description) for _ in cls.__aa_methods_registry__)),
            options={'HIDDEN', 'SKIP_SAVE'},
            name="AA Method",
            description="Anti-aliasing method to be used",
        )

    @classmethod
    def register_aa_method(cls, method_class: AABase):
        """
        A method for registering an anti-aliasing class

        :param method_class: Anti-aliasing class
        :type method_class: AABase
        """
        cls.__aa_methods_registry__.add(method_class)

    @property
    def aa_method(self) -> str:
        if self._aa_instance is None:
            return 'NONE'
        return self._aa_instance.name

    @aa_method.setter
    def aa_method(self, value: str):
        cls = self.__class__

        area_type = self._fb_frameworks[0]._area_type
        region_type = self._fb_frameworks[0]._region_type

        if (not self._aa_instance) or (self._aa_instance and self._aa_instance.name != value):
            for item in cls.__aa_methods_registry__:
                if item.name == value:
                    self._aa_instance = item(area_type=area_type, region_type=region_type)

    @property
    def aa(self) -> AABase | None:
        return self._aa_instance

    def get(self, *, index: int = 0) -> FrameBufferFramework:
        """
        The method of obtaining a framework by index

        :param index: The index of the required framework, defaults to 0
        :type index: int, optional
        :return: framework
        :rtype: FrameBufferFramework
        """
        return self._fb_frameworks[index]

    def modal_eval(self, context: Context, *, color_format: str = "", depth_format: str = "", percentage: int = 100):
        """
        A method for updating framebuffers data according to the size/availability of viewports. Must be called in
        modal part of the operator

        :param context: Current context
        :type context: `Context`_
        :param color_format: The color texture format or an empty value if no color texture is required, defaults to ''
        :type color_format: str, see `GPUTexture`_ for details, optional
        :param depth_format: The depth texture format or an empty value if no depth texture is required, defaults to ''
        :type depth_format: str, see `GPUTexture`_ for details, optional
        :param percentage: Resolution percentage, defaults to 100
        :type percentage: int, optional
        """
        for fb_framework in self._fb_frameworks:
            fb_framework.modal_eval(
                context,
                color_format=color_format,
                depth_format=depth_format,
                percentage=percentage
            )
        if self._aa_instance:
            self._aa_instance.modal_eval(
                context,
                color_format=color_format,
                percentage=percentage
            )

    def __init__(self, *, num: int = 1, area_type='VIEW_3D', region_type='WINDOW'):
        self._fb_frameworks = tuple(
            _framebuffer_framework.FrameBufferFramework(
                area_type=area_type,
                region_type=region_type
            )
            for _ in range(max(1, num))
        )

        self._aa_instance = None

    def draw(self, *, texture: GPUTexture) -> None:
        """
        Display the texture according to the selected anti-aliasing options

        :param texture: Texture
        :type texture: `GPUTexture`_
        """
        cls = self.__class__

        mvp_restore = gpu.matrix.get_projection_matrix() @ gpu.matrix.get_model_view_matrix()

        if (self._aa_instance is None) or (self._aa_instance._preset is AAPreset.NONE):
            with gpu.matrix.push_pop():  # type: ignore
                AABase._setup_gpu_state()

                shader = cls.__shader_2d_image__
                shader.uniform_sampler("image", texture)

                cls.__unit_rect_batch__.draw(shader)
        else:
            self._aa_instance.draw(texture=texture)

        gpu.matrix.load_matrix(mvp_restore)


DrawFramework.register_aa_method(FXAA)
DrawFramework.register_aa_method(SMAA)
