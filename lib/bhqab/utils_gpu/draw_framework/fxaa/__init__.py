from __future__ import annotations

from typing import Literal
import os

from bpy.props import (
    EnumProperty,
    FloatProperty,
)

import gpu
from gpu.types import (
    GPUBatch,
    GPUShader,
    GPUTexture,
)

from .. import _aa_base
from .. import _offscreen_framework

__all__ = (
    "FXAA",
)


class FXAA(_aa_base.AABase):
    """Fast approximate anti-aliasing"""

    # NOTE: __doc__ may be used also in UI purposes.

    __slots__ = (
        "_value",
        "_value_0",
        "_off_framework",
        "_shader_eval",
        "_batch_eval",
    )

    _off_framework: _offscreen_framework.OffscreenFramework
    """
    An offscreen framework.
    """
    _shader_eval: None | GPUShader
    """
    FXAA shader evaluated according to the current preset (including ``NONE`` - None in this case)
    """
    _batch_eval: None | GPUBatch
    """
    Batch for evaluated shader. Updated whenever the shader are updated.
    """
    _cached_shader_code: tuple[str] = tuple()
    """
    Raw shader code: (./fxaa_vert.glsl, ./fxaa_frag.glsl, ./fxaa_lib.glsl)
    Read once at first call of ``modal_eval``
    """
    _value: float
    """Sub-preset (as far as FXAA shader library offers more that 5 values)"""
    _value_0: float
    """See ``_value``"""

    # NOTE: number of tuples always must be equal to number of elements in `_AAPreset` enumeration
    __quality_lookup__: tuple[tuple, tuple, tuple, tuple] = (
        (10, 11, 12, 13, 14, 15,),  # _AAPreset.LOW
        (20, 21, 22, 23, 24, 25,),  # _AAPreset.MEDIUM
        (26, 27, 28, 29,),  # _AAPreset.HIGH
        (39,)  # _AAPreset.ULTRA
    )

    @classmethod
    @property
    def prop_preset(cls) -> EnumProperty:
        """
        :return: A property that can be used in addon preferences class annotations
        :rtype: `EnumProperty`_
        """
        return EnumProperty(
            items=(
                (_aa_base.AAPreset.NONE.name, "None", "Do not use fast approximate anti-aliasing"),
                (_aa_base.AAPreset.LOW.name, "Low", "Default medium dither"),
                (_aa_base.AAPreset.MEDIUM.name, "Medium", "Less dither, faster"),
                (_aa_base.AAPreset.HIGH.name, "High", "Less dither, more expensive"),
                (_aa_base.AAPreset.ULTRA.name, "Ultra", "No dither, very expensive"),
            ),
            default=_aa_base.AAPreset.HIGH.name,
            options={'HIDDEN', 'SKIP_SAVE'},
            name="Preset",
            description="Fast approximate anti-aliasing quality preset"
        )

    @classmethod
    @property
    def prop_value(cls) -> FloatProperty:
        """
        :return: A property that can be used in addon preferences class annotations
        :rtype: `FloatProperty`_
        """
        return FloatProperty(
            options={'HIDDEN', 'SKIP_SAVE'},
            min=0, max=1, default=1.0, step=0.001,
            subtype='PERCENTAGE',
            name="Quality",
            description="FXAA preset quality tuning"
        )

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, value) -> None:
        self._value = max(0.0, min(1.0, float(value)))

    def _do_value_eval(self):
        if self._value_0 != self._value:
            self._value_0 = self._value
            return True
        return False

    def _eval_shader(self):
        cls = self.__class__
        if _aa_base.AAPreset.NONE != self._preset:
            _do_update_on_preset_change = self._do_preset_eval()
            _do_update_on_value_change = self._do_value_eval()
            if self._shader_eval is None or _do_update_on_preset_change or _do_update_on_value_change:
                if not cls._cached_shader_code:
                    with (open(os.path.join(os.path.dirname(__file__), "fxaa_vert.glsl")) as fxaa_vert_file,
                          open(os.path.join(os.path.dirname(__file__), "fxaa_frag.glsl")) as fxaa_frag_file,
                          open(os.path.join(os.path.dirname(__file__), "fxaa_lib.glsl")) as fxaa_lib_file):
                        cls._cached_shader_code = (fxaa_vert_file.read(), fxaa_frag_file.read(), fxaa_lib_file.read())

                lookup = cls.__quality_lookup__[int(self._preset) - 2]
                preset_value = lookup[max(0, min(len(lookup) - 1, int(len(lookup) * self._value)))]

                defines = f"#define FXAA_QUALITY__PRESET {preset_value}\n"
                vertexcode, fragcode, libcode = cls._cached_shader_code

                self._shader_eval = GPUShader(
                    vertexcode=vertexcode,
                    fragcode=fragcode,
                    libcode=libcode,
                    defines=defines,
                    name="FXAA",
                )
                self._batch_eval = _offscreen_framework.eval_unit_rect_batch(self._shader_eval)
        else:
            self._shader_eval = None
            self._batch_eval = None

    def modal_eval(self, *, format: Literal['RGBA8', 'RGBA16', 'RGBA16F', 'RGBA32F'] = 'RGBA8', percentage: int = 100):
        """
        The class and instance data update method should be called in the modal part of the control operator

        :param format: Required format of data buffers, defaults to 'RGBA8'
        :type format: Literal['RGBA8', 'RGBA16', 'RGBA16F', 'RGBA32F'], optional
        :param percentage: Resolution percentage, defaults to 100
        :type percentage: int, optional
        """
        self._off_framework.modal_eval(format=format, percentage=percentage)
        self._eval_shader()

    def __init__(self):
        super().__init__()
        self._value = 0.0
        self._value_0 = 0.0
        self._shader_eval = None
        self._batch_eval = None
        self._off_framework = _offscreen_framework.OffscreenFramework()

    def draw(self, *, texture: GPUTexture) -> None:
        """
        Draw method

        :param texture: Input texture
        :type texture: `GPUTexture`_
        """
        shader = self._shader_eval

        super().draw(texture=texture)

        viewport_metrics = _offscreen_framework.get_viewport_metrics()

        with gpu.matrix.push_pop():
            gpu.matrix.load_matrix(_aa_base.IDENTITY_M4X4)
            gpu.matrix.load_projection_matrix(_aa_base.IDENTITY_M4X4)
            gpu.state.blend_set('ALPHA_PREMULT')

            shader.bind()
            shader.uniform_sampler("image", texture)
            shader.uniform_float("viewportMetrics", viewport_metrics)
            self._batch_eval.draw(shader)
