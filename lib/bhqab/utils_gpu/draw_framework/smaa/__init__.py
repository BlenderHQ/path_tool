# https://github.com/iryoku/smaa

from __future__ import annotations

from typing import Literal
import numpy as np
import os

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

from .. import _aa_base
from .. import _framebuffer_framework

__all__ = (
    "SMAA",
)


class SMAA(_aa_base.AABase):
    """Sub-pixel morphological anti-aliasing"""

    # NOTE: __doc__ may be used also in UI purposes.

    __slots__ = (
        "_fb_framework_stage_0",
        "_fb_framework_stage_1",
        "_shaders_eval",
        "_batches_eval",
    )

    _fb_framework_stage_0: _framebuffer_framework.FrameBufferFramework
    """
    An offscreen framework for the first stage of processing.
    """
    _fb_framework_stage_1: _framebuffer_framework.FrameBufferFramework
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
                    r"Do not use sub-pixel morphological anti-aliasing",
                ),
                (
                    _aa_base.AAPreset.LOW.name,
                    "Low",
                    (r"60% of the quality. High threshold, very a few search steps, no detection of corners and "
                     r"diagonals"),
                ),
                (
                    _aa_base.AAPreset.MEDIUM.name,
                    "Medium",
                    r"80% of the quality. Medium threshold, few search steps, no detection of corners and diagonals",
                ),
                (
                    _aa_base.AAPreset.HIGH.name,
                    "High",
                    r"95% of the quality. Medium threshold, more search steps, detection of corners and diagonals",
                ),
                (
                    _aa_base.AAPreset.ULTRA.name,
                    "Ultra",
                    r"99% of the quality. A lot of search steps, diagonal and corner search steps, lowest threshold",
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
                    directory = os.path.dirname(__file__)
                    with (
                        open(file=os.path.join(directory, "smaa_vert.glsl"), mode='r', encoding="utf-8") as vert_file,
                        open(file=os.path.join(directory, "smaa_frag.glsl"), mode='r', encoding="utf-8") as frag_file,
                        open(file=os.path.join(directory, "smaa_lib.glsl"), mode='r', encoding="utf-8") as lib_file
                    ):
                        cls._cached_shader_code = (
                            vert_file.read(),
                            frag_file.read(),
                            lib_file.read(),
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

                self._batches_eval = tuple((_framebuffer_framework.eval_unit_rect_batch(shader)
                                           for shader in self._shaders_eval))
        else:
            self._shaders_eval = tuple()
            self._batches_eval = tuple()

    def modal_eval(self, context: Context, *, color_format: str = "", percentage: int = 100):
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

        self._fb_framework_stage_0.modal_eval(
            context,
            color_format=color_format,
            depth_format="",  # Current shader implementation does not need depth texture
            percentage=percentage
        )
        self._fb_framework_stage_1.modal_eval(
            context,
            color_format=color_format,
            depth_format="",  # Current shader implementation does not need depth texture
            percentage=percentage
        )

    def __init__(self, *, area_type='VIEW_3D', region_type='WINDOW'):
        super().__init__(area_type=area_type, region_type=region_type)
        self._shaders_eval = tuple()
        self._batches_eval = tuple()
        self._fb_framework_stage_0 = _framebuffer_framework.FrameBufferFramework(
            area_type=area_type,
            region_type=region_type
        )
        self._fb_framework_stage_1 = _framebuffer_framework.FrameBufferFramework(
            area_type=area_type,
            region_type=region_type
        )

    def draw(self, *, texture: GPUTexture) -> None:
        """
        Draw method

        :param texture: Input texture
        :type texture: `GPUTexture`_
        """
        super().draw(texture=texture)

        cls = self.__class__
        viewport_metrics = _framebuffer_framework.get_viewport_metrics()

        fb_framework_0 = self._fb_framework_stage_0
        fb = fb_framework_0.get()
        with fb.bind():
            fb.clear(color=(0.0, 0.0, 0.0, 0.0))
            self._setup_gpu_state()

            shader = self._shaders_eval[0]
            shader.bind()
            shader.uniform_sampler("colorTex", texture)
            shader.uniform_float("viewportMetrics", viewport_metrics)
            self._batches_eval[0].draw(shader)

        fb_framework_1 = self._fb_framework_stage_1
        fb = fb_framework_1.get()
        with fb.bind():
            fb.clear(color=(0.0, 0.0, 0.0, 0.0))
            self._setup_gpu_state()

            shader = self._shaders_eval[1]
            shader.bind()
            shader.uniform_sampler("edgesTex", fb_framework_0.get_color_texture())
            shader.uniform_sampler("searchTex", cls._cached_smaa_textures[0])
            shader.uniform_sampler("areaTex", cls._cached_smaa_textures[1])
            shader.uniform_float("viewportMetrics", viewport_metrics)
            self._batches_eval[1].draw(shader)

        with gpu.matrix.push_pop():
            self._setup_gpu_state()

            shader = self._shaders_eval[2]
            shader.bind()
            shader.uniform_sampler("colorTex", texture)
            shader.uniform_sampler("blendTex", fb_framework_1.get_color_texture())
            shader.uniform_float("viewportMetrics", viewport_metrics)
            self._batches_eval[2].draw(shader)
