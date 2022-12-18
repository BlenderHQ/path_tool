# https://github.com/iryoku/smaa

from __future__ import annotations

from typing import Literal
import numpy as np
import os

from bpy.props import (
    EnumProperty,
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
    "SMAA",
)


class SMAA(_aa_base.AABase):
    """Sub-pixel morphological anti-aliasing"""

    # NOTE: __doc__ may be used also in UI purposes.

    __slots__ = (
        "_off_framework_stage_0",
        "_off_framework_stage_1",
        "_shaders_eval",
        "_batches_eval",
    )

    _off_framework_stage_0: _offscreen_framework.OffscreenFramework
    """
    An offscreen framework for the first stage of processing.
    """
    _off_framework_stage_1: _offscreen_framework.OffscreenFramework
    """
    An offscreen framework for the second stage of processing.
    """
    _shaders_eval: tuple[GPUShader]
    """
    SMAA shaders evaluated according to the current preset (including ``NONE`` - empty tuple in this case)
    """
    _batches_eval: None | tuple[GPUBatch]
    """
    Batches for evaluated shaders. Updated whenever the shaders are updated.
    """
    _cached_shader_code: tuple[str] = tuple()
    """
    Raw shader code: (./smaa_vert.glsl, ./smaa_frag.glsl, ./smaa_lib.glsl)
    Read once at first call of ``modal_eval``
    """
    _cached_smaa_textures: tuple[GPUTexture] = tuple()
    """
    Cached SMAA textures (Search Texture, Area Texture)
    Created once at first call of `modal_eval`
    """

    @classmethod
    @property
    def prop_preset(cls):
        """
        :return: A property that can be used in addon preferences class annotations
        :rtype: `EnumProperty`_
        """
        return EnumProperty(
            items=(
                (
                    _aa_base.AAPreset.NONE.name,
                    "None",
                    "Do not use sub-pixel morphological anti-aliasing",
                ),
                (
                    _aa_base.AAPreset.LOW.name,
                    "Low",
                    "60% of the quality. High threshold, very a few search steps, no detection of corners and diagonals",
                ),
                (
                    _aa_base.AAPreset.MEDIUM.name,
                    "Medium",
                    "80% of the quality. Medium threshold, few search steps, no detection of corners and diagonals",
                ),
                (
                    _aa_base.AAPreset.HIGH.name,
                    "High",
                    "95% of the quality. Medium threshold, more search steps, detection of corners and diagonals",
                ),
                (
                    _aa_base.AAPreset.ULTRA.name,
                    "Ultra",
                    "99% of the quality. A lot of search steps, diagonal and corner search steps, lowest threshold",
                ),
            ),
            default=_aa_base.AAPreset.HIGH.name,
            options={'HIDDEN', 'SKIP_SAVE'},
            name="Preset",
            description="Sub-pixel morphological anti-aliasing quality preset"
        )

    @classmethod
    def _eval_textures(cls) -> None:
        if not cls._cached_smaa_textures:
            _SMAA_SEARCHTEX_WIDTH = 64
            _SMAA_SEARCHTEX_HEIGHT = 16
            _SMAA_SEARCHTEX_PITCH = _SMAA_SEARCHTEX_WIDTH
            _SMAA_SEARCHTEX_SIZE = (_SMAA_SEARCHTEX_HEIGHT * _SMAA_SEARCHTEX_PITCH)

            _SMAA_AREATEX_WIDTH = 160
            _SMAA_AREATEX_HEIGHT = 560
            _SMAA_AREATEX_PITCH = (_SMAA_AREATEX_WIDTH * 2)
            _SMAA_AREATEX_SIZE = (_SMAA_AREATEX_HEIGHT * _SMAA_AREATEX_PITCH)

            def _float32_arr_from_byte_file(name: str):
                return np.fromfile(
                    os.path.join(os.path.dirname(__file__), name),
                    dtype=np.ubyte
                ).astype(dtype=np.float32) / 0xff

            cls._cached_smaa_textures = (
                # Search Texture
                GPUTexture(
                    size=(_SMAA_SEARCHTEX_WIDTH, _SMAA_SEARCHTEX_HEIGHT),
                    format='R8',
                    data=gpu.types.Buffer(
                        'FLOAT',
                        _SMAA_SEARCHTEX_SIZE,
                        _float32_arr_from_byte_file("searchtex.np")
                    )
                ),
                # Area Texture
                GPUTexture(
                    size=(_SMAA_AREATEX_WIDTH, _SMAA_AREATEX_HEIGHT),
                    format='RG8',
                    data=gpu.types.Buffer('FLOAT', _SMAA_AREATEX_SIZE, _float32_arr_from_byte_file("areatex.np"))
                )
            )

    def _eval_shaders(self):
        cls = self.__class__

        if _aa_base.AAPreset.NONE != self._preset:
            _do_update_on_preset_change = self._do_preset_eval()
            if not self._shaders_eval or _do_update_on_preset_change:
                if not cls._cached_shader_code:
                    with (
                        open(file=os.path.join(os.path.dirname(__file__), "smaa_vert.glsl"), mode='r', encoding="utf-8") as smaa_vert_file,
                        open(file=os.path.join(os.path.dirname(__file__), "smaa_frag.glsl"), mode='r', encoding="utf-8") as smaa_frag_file,
                        open(file=os.path.join(os.path.dirname(__file__), "smaa_lib.glsl"), mode='r', encoding="utf-8") as smaa_lib_file
                    ):
                        cls._cached_shader_code = (
                            smaa_vert_file.read(),
                            smaa_frag_file.read(),
                            smaa_lib_file.read(),
                        )
                vertexcode, fragcode, libcode = cls._cached_shader_code

                self._shaders_eval = tuple((
                    GPUShader(
                        vertexcode=vertexcode,
                        fragcode=fragcode,
                        defines=("#define SMAA_GLSL_4 1\n"
                                 "#define SMAA_RT_METRICS viewportMetrics\n"
                                 "uniform vec4 viewportMetrics;\n"
                                 f"\n#define SMAA_STAGE {i}\n"
                                 f"#define SMAA_PRESET_{self._preset.name}\n"
                                 f"{libcode}\n"),
                        name=f"SMAA Stage {i}",
                    ) for i in range(3)
                ))

                self._batches_eval = tuple((_offscreen_framework.eval_unit_rect_batch(shader)
                                           for shader in self._shaders_eval))
        else:
            self._shaders_eval = tuple()
            self._batches_eval = tuple()

    def modal_eval(self, *, format: Literal['RGBA8', 'RGBA16', 'RGBA16F', 'RGBA32F'] = 'RGBA8', percentage: int = 100):
        """
        The class and instance data update method should be called in the modal part of the control operator

        :param format: Required format of data buffers, defaults to 'RGBA8'
        :type format: Literal['RGBA8', 'RGBA16', 'RGBA16F', 'RGBA32F'], optional
        :param percentage: Resolution percentage, defaults to 100
        :type percentage: int, optional
        """
        cls = self.__class__

        cls._eval_textures()
        self._eval_shaders()

        self._off_framework_stage_0.modal_eval(format=format, percentage=percentage)
        self._off_framework_stage_1.modal_eval(format=format, percentage=percentage)

    def __init__(self):
        super().__init__()
        self._shaders_eval = tuple()
        self._batches_eval = tuple()
        self._off_framework_stage_0 = _offscreen_framework.OffscreenFramework()
        self._off_framework_stage_1 = _offscreen_framework.OffscreenFramework()

    def draw(self, *, texture: GPUTexture) -> None:
        """
        Draw method

        :param texture: Input texture
        :type texture: `GPUTexture`_
        """
        super().draw(texture=texture)

        cls = self.__class__
        viewport_metrics = _offscreen_framework.get_viewport_metrics()

        def _setup_gl(clear: bool) -> None:
            if clear:
                fb = gpu.state.active_framebuffer_get()
                fb.clear(color=(0.0, 0.0, 0.0, 0.0))

            gpu.matrix.load_matrix(_aa_base.IDENTITY_M4X4)
            gpu.matrix.load_projection_matrix(_aa_base.IDENTITY_M4X4)
            gpu.state.blend_set('ALPHA_PREMULT')

        offscreen_stage_0 = self._off_framework_stage_0.get()
        with offscreen_stage_0.bind():
            _setup_gl(clear=True)
            shader = self._shaders_eval[0]
            shader.bind()
            shader.uniform_sampler("colorTex", texture)
            shader.uniform_float("viewportMetrics", viewport_metrics)
            self._batches_eval[0].draw(shader)

        offscreen_stage_1 = self._off_framework_stage_1.get()
        with offscreen_stage_1.bind():
            _setup_gl(clear=True)

            shader = self._shaders_eval[1]
            shader.bind()
            shader.uniform_sampler("edgesTex", offscreen_stage_0.texture_color)
            shader.uniform_sampler("searchTex", cls._cached_smaa_textures[0])
            shader.uniform_sampler("areaTex", cls._cached_smaa_textures[1])
            shader.uniform_float("viewportMetrics", viewport_metrics)
            self._batches_eval[1].draw(shader)

        with gpu.matrix.push_pop():
            _setup_gl(clear=False)
            shader = self._shaders_eval[2]
            shader.bind()
            shader.uniform_sampler("colorTex", texture)
            shader.uniform_sampler("blendTex", offscreen_stage_1.texture_color)
            shader.uniform_float("viewportMetrics", viewport_metrics)
            self._batches_eval[2].draw(shader)
