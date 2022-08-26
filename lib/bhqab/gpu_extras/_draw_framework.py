from __future__ import annotations
from enum import auto, IntEnum
from typing import Iterator, Literal
import os
import numpy as np

import bpy
from bpy.types import (
    Region,
    Area,
    Context,
    Space,
)

from bpy.props import (
    EnumProperty,
    FloatProperty
)

from mathutils import Vector, Matrix

import gpu
from gpu.types import (
    GPUOffScreen,
    GPUBatch,
    GPUVertBuf,
    GPUIndexBuf,
    GPUVertFormat,
    GPUShader,
    GPUTexture,
)


class AAPreset(IntEnum):
    NONE = auto()
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    ULTRA = auto()


IDENTITY_M4X4 = Matrix.Identity(4)


class AABase(object):
    """
    Base class for shader based AA implementations.
    Derived classes should be looks like:

    .. code-block:: python
        :emphasize-lines: 1

        class FXAA(AABase):
            # This class members would be used for evaluation of available AA implementations property
            _name = "FXAA"
            _description = "Fast approximate anti-aliasing"


            @classmethod
            @property
            def prop_preset(cls) -> EnumProperty:
                # Return enum property which contains AAPreset item names as keys


            def __init__(self, is_final: bool = True):
                AABase.__init__(self, is_final)

            def draw(self, texture: GPUTexture) -> None | GPUTexture:
                if self.is_final:
                    # Draw to viewport
                else:
                    # Return processed texture object

        # Register this class for draw framework makes it available via DrawFramework.prop_aa_method
        DrawFramework.register_shader_based_aa_impl(FXAA)
    """
    _preset: AAPreset
    _preset_0: AAPreset

    _is_final: bool
    _gpu_draw_framework: None | DrawFramework

    @classmethod
    @property
    def name(cls) -> str:
        """The name of the anti-aliasing method that can be used in the user interface

        Returns:
            str: Name
        """
        return cls._name

    @classmethod
    @property
    def description(cls) -> str:
        """Description of the anti-aliasing method that may be used for display in the user interface

        Returns:
            str: Description
        """
        return cls._description

    @property
    def preset(self) -> Literal['NONE', 'LOW', 'MEDIUM', 'HIGH', 'ULTRA']:
        """The current anti-aliasing preset as a string enumerator in
        [``NONE``, ``LOW``, ``MEDIUM``, ``HIGH``, ``ULTRA``]
        """
        return self._preset.name

    @preset.setter
    def preset(self, value: Literal['NONE', 'LOW', 'MEDIUM', 'HIGH', 'ULTRA']):
        val_eval = AAPreset.NONE
        try:
            val_eval = AAPreset[value]
        except KeyError:
            str_possible_values = ', '.join(AAPreset.__members__.keys())
            raise KeyError(f"Key '{value}' not found in {str_possible_values}")
        else:
            self._preset = val_eval

    @property
    def is_final(self) -> bool:
        """_summary_

        Returns:
            bool: _description_
        """
        return self._is_final

    def _do_eval_preset(self) -> bool:
        if self._preset_0 == self._preset:
            return False
        self._preset_0 = self._preset
        return True

    def _do_eval_gpu_framework(self) -> bool:
        return (not self.is_final) and (self._gpu_draw_framework is None)

    def __init__(self, is_final: bool):
        self._gpu_draw_framework = None
        self._preset = AAPreset.NONE
        self._preset_0 = AAPreset.NONE
        self._is_final = is_final


class DrawFramework:
    _num_offscreens: int
    _format: str
    _offscreen_types: tuple[str]
    _offscreen_arr: dict[Region, tuple(GPUOffScreen)]
    _batch: None | GPUBatch = None
    _aa: None | AABase
    aa_index: int
    _SHADER_BASED_AA_IMPL_REGISTRY = []

    @classmethod
    def register_shader_based_aa_impl(cls, item: AABase) -> None:
        """Registers the anti-aliasing implementation. Once registered, `prop_aa_method` will contain the registered
        method

        Args:
            item (AABase): Subclass representing AA implementation
        """
        cls._SHADER_BASED_AA_IMPL_REGISTRY.append(item)

    @classmethod
    @property
    def prop_aa_method(cls) -> EnumProperty:
        """
        Returns a property that can be used for addon preferences and contains registered anti-aliasing methods

        Returns:
            EnumProperty: Property
        """
        return EnumProperty(
            items=tuple((
                (_.name, _.name, _.description) for _ in DrawFramework._SHADER_BASED_AA_IMPL_REGISTRY
            )),
            default=DrawFramework._SHADER_BASED_AA_IMPL_REGISTRY[0].name,
            options={'HIDDEN', 'SKIP_SAVE'},
            name="AA Method",
            description="Anti-aliasing method to be used",
        )

    @property
    def aa(self) -> AABase:
        """
        Current anti-aliasing method, may be None.
        """
        return self._aa

    @aa.setter
    def aa(self, value: str) -> None:
        for item in DrawFramework._SHADER_BASED_AA_IMPL_REGISTRY:
            if item.name == value:
                if not isinstance(self._aa, item):
                    self._aa = item()

    @classmethod
    @property
    def viewport_metrics(self) -> Vector:
        """
        Viewport metrics for current viewport.

        :return: x = ``1.0 / width``, y = ``1.0 / height``, z = ``width``, w = ``height``
        :rtype: Vector
        """
        viewport = gpu.state.viewport_get()
        w, h = viewport[2], viewport[3]
        return Vector((1.0 / w, 1.0 / h, w, h))

    @classmethod
    @property
    def unit_rect_batch(cls) -> GPUBatch:
        """Unit size square batch

        Returns:
            GPUBatch: Batch
        """
        cls._eval_batch()
        return cls._batch

    @staticmethod
    def iter_areas(context: Context, area_type: str = 'VIEW_3D') -> Iterator[Area]:
        """
        Iterator for the area in all open program windows.

        .. code-block:: python
            :emphasize-lines: 1

            for area in GPUDrawFramework.iter_areas(bpy.context, area_type='VIEW_3D'):
                print(area)
            ...

        :param context: Current context
        :type context: Context
        :param area_type: Area type. See `bpy.types.Area.type`_, defaults to 'VIEW_3D'
        :type area_type: str, optional
        :yield: Areas iterator
        :rtype: Iterator[Area]
        """
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area: Area
                if area.type == area_type:
                    yield area

    @staticmethod
    def iter_area_regions(area: Area, region_type: str = 'WINDOW') -> Iterator[Region]:
        """
        Iterator of regions in an area by type.

        .. code-block:: python
            :emphasize-lines: 2

            area = bpy.context.area
            for region in GPUDrawFramework.iter_area_regions(area, region_type='WINDOW'):
                print(region)
            ...


        :param area: Processing area
        :type area: Area
        :param region_type: Type of region. See `bpy.types.Region.type`_, defaults to 'WINDOW'
        :type region_type: str, optional
        :yield: Regions iterator
        :rtype: Iterator[Region]
        """
        for region in area.regions:
            region: Region

            if region.type == region_type:
                yield region

    @staticmethod
    def iter_area_spaces(area: Area, space_type: str = 'VIEW_3D') -> Iterator[Space]:
        """
        Iterator of spaces in an area by type.

        .. code-block:: python
            :emphasize-lines: 2

            area = bpy.context.area
            for space in GPUDrawFramework.iter_area_spaces(area, space_type='VIEW_3D'):
                print(space)
            ...


        :param area: Processing area
        :type area: Area
        :param space_type: Type of space. See `bpy.types.Space.type`_, defaults to 'VIEW_3D'
        :type space_type: str, optional
        :yield: Spaces iterator
        :rtype: Iterator[Space]
        """
        for space in area.spaces:
            space: Space

            if space.type == space_type:
                yield space

    def _eval_offscreens(self):
        for area in DrawFramework.iter_areas(bpy.context, 'VIEW_3D'):
            for region in DrawFramework.iter_area_regions(area, 'WINDOW'):
                do_update = True
                if region in self._offscreen_arr:
                    offscreen_0 = self._offscreen_arr[region][0]
                    if offscreen_0.width == region.width and offscreen_0.height == region.height:
                        do_update = False

                if do_update:
                    self._offscreen_arr[region] = tuple((
                        GPUOffScreen(region.width, region.height, format=self._format)
                        for _ in range(self._num_offscreens)
                    ))

    @classmethod
    def _eval_batch(cls):
        if cls._batch is None:
            vert_fmt = GPUVertFormat()
            vert_fmt.attr_add(id="pos", comp_type='F32', len=2, fetch_mode='FLOAT')
            vert_fmt.attr_add(id="texCoord", comp_type='F32', len=2, fetch_mode='FLOAT')

            vbo = GPUVertBuf(len=4, format=vert_fmt)
            vbo.attr_fill("pos", ((-1, -1), (-1, 1), (1, 1), (1, -1)))
            vbo.attr_fill("texCoord", ((0, 0), (0, 1), (1, 1), (1, 0)))

            ibo = GPUIndexBuf(type='TRIS', seq=((0, 1, 2), (0, 2, 3)))

            cls._batch = GPUBatch(type='TRIS', buf=vbo, elem=ibo)

    def _eval_update(self):
        self._eval_offscreens()
        self._eval_batch()

    def __init__(
        self,
        num_offscreens: int = 1,
        # TODO: Watch https://docs.blender.org/api/current/gpu.types.html#gpu.types.GPUOffScreen for changes.
        format: Literal['RGBA8', 'RGBA16', 'RGBA16F', 'RGBA32F'] = 'RGBA8'
    ) -> None:
        self._num_offscreens = max(1, num_offscreens)
        self._format = format
        self._offscreen_arr = dict()
        self._aa = None
        self.aa_index = -1

    def __del__(self):
        for offscreens in self._offscreen_arr.values():
            for offscreen in offscreens:
                offscreen.free()
        self._offscreen_arr.clear()

    def __enter__(self) -> tuple[GPUOffScreen]:
        self._eval_update()
        self._original_mvp_mat = gpu.matrix.get_projection_matrix() @ gpu.matrix.get_model_view_matrix()

        return self._offscreen_arr[bpy.context.region]

    def __exit__(self, type, value, traceback) -> None:
        if isinstance(self._aa, AABase):
            self._aa.draw(self._offscreen_arr[bpy.context.region][self.aa_index].texture_color)
        gpu.matrix.load_matrix(self._original_mvp_mat)


_SMAA_SEARCHTEX_WIDTH = 64
_SMAA_SEARCHTEX_HEIGHT = 16
_SMAA_SEARCHTEX_PITCH = _SMAA_SEARCHTEX_WIDTH
_SMAA_SEARCHTEX_SIZE = (_SMAA_SEARCHTEX_HEIGHT * _SMAA_SEARCHTEX_PITCH)

_SMAA_AREATEX_WIDTH = 160
_SMAA_AREATEX_HEIGHT = 560
_SMAA_AREATEX_PITCH = (_SMAA_AREATEX_WIDTH * 2)
_SMAA_AREATEX_SIZE = (_SMAA_AREATEX_HEIGHT * _SMAA_AREATEX_PITCH)


class SMAA(AABase):
    _name: str = "SMAA"
    _description: str = "Sub-pixel morphological anti-aliasing"

    _cached_shader_code: None | tuple[str] = None
    _shaders: None | tuple[GPUShader]
    _textures: None | tuple[GPUTexture] = None

    @classmethod
    @property
    def prop_preset(cls):
        return EnumProperty(
            items=(
                (AAPreset.NONE.name, "None", "Do not use SMAA post-processing"),
                (AAPreset.LOW.name, "Low", "Low SMAA quality"),
                (AAPreset.MEDIUM.name, "Medium", "Medium SMAA quality"),
                (AAPreset.HIGH.name, "High", "High SMAA quality"),
                (AAPreset.ULTRA.name, "Ultra", "Ultra SMAA quality"),
            ),
            default=AAPreset.HIGH.name,
            options={'HIDDEN', 'SKIP_SAVE'},
            name="Preset",
            description="Sub-pixel morphological anti-aliasing quality preset"
        )

    def __init__(self, is_final: bool = True):
        AABase.__init__(self, is_final)
        self._shaders = None

    def _eval_framework(self) -> None:
        if self._preset == AAPreset.NONE:
            self._gpu_draw_framework = None
        elif self._gpu_draw_framework is None:
            self._gpu_draw_framework = DrawFramework(num_offscreens=2 if self.is_final else 3)

    @classmethod
    def _eval_textures(cls) -> None:
        if cls._textures is None:
            def _float32_arr_from_byte_file(name: str):
                return np.fromfile(
                    os.path.join(os.path.dirname(__file__), "_smaa", name),
                    dtype=np.ubyte
                ).astype(dtype=np.float32) / 0xff

            cls._textures = (
                # SearchTex
                GPUTexture(
                    size=(_SMAA_SEARCHTEX_WIDTH, _SMAA_SEARCHTEX_HEIGHT),
                    format='R8',
                    data=gpu.types.Buffer('FLOAT', _SMAA_SEARCHTEX_SIZE, _float32_arr_from_byte_file("searchtex.np"))
                ),
                # AreaTex
                GPUTexture(
                    size=(_SMAA_AREATEX_WIDTH, _SMAA_AREATEX_HEIGHT),
                    format='RG8',
                    data=gpu.types.Buffer('FLOAT', _SMAA_AREATEX_SIZE, _float32_arr_from_byte_file("areatex.np"))
                )
            )

    def _eval_shaders(self) -> None:
        if self._preset != AAPreset.NONE:
            if self._shaders is None or self._do_eval_preset():
                if SMAA._cached_shader_code is None:
                    with (
                        open(os.path.join(os.path.dirname(__file__), "_smaa", "smaa_vert.glsl"), 'r') as smaa_vert_file,
                        open(os.path.join(os.path.dirname(__file__), "_smaa", "smaa_frag.glsl"), 'r') as smaa_frag_file,
                        open(os.path.join(os.path.dirname(__file__), "_smaa", "smaa_lib.glsl"), 'r') as smaa_lib_file,
                        open(os.path.join(os.path.dirname(__file__), "_smaa", "smaa_def.glsl"), 'r') as smaa_def_file
                    ):
                        SMAA._cached_shader_code = (
                            smaa_vert_file.read(),
                            smaa_frag_file.read(),
                            smaa_lib_file.read(),
                            smaa_def_file.read()
                        )
                if self._shaders is None or self._do_eval_preset:
                    vert_code, frag_code, lib_code, def_code = SMAA._cached_shader_code
                    self._shaders = tuple((
                        GPUShader(
                            vertexcode=vert_code,
                            fragcode=frag_code,
                            defines=(f"\n#define SMAA_STAGE {i}\n"
                                     f"#define SMAA_PRESET_{self._preset.name}\n"
                                     f"{def_code}\n"
                                     f"{lib_code}\n"),
                            name=f"smaa_stage_{i}",
                        )
                    ) for i in range(3))
        else:
            self._shaders = None
            if SMAA.do_reset_on_none_preset:
                self._cached_shader_code = None

    def _eval_update(self) -> None:
        self._eval_framework()
        self._eval_textures()
        self._eval_shaders()

    def draw(self, texture: GPUTexture) -> None | GPUTexture:
        self._eval_update()

        if self._preset != AAPreset.NONE:
            viewport_metrics = DrawFramework.viewport_metrics

            def _setup_gl(clear: bool) -> None:
                if clear:
                    fb = gpu.state.active_framebuffer_get()
                    fb.clear(color=(0.0, 0.0, 0.0, 0.0))

                gpu.matrix.load_matrix(IDENTITY_M4X4)
                gpu.matrix.load_projection_matrix(IDENTITY_M4X4)
                gpu.state.blend_set('ALPHA_PREMULT')

            with self._gpu_draw_framework as offscreens:
                with offscreens[0].bind():
                    _setup_gl(clear=True)
                    shader = self._shaders[0]
                    shader.bind()
                    shader.uniform_sampler("colorTex", texture)
                    shader.uniform_float("viewportMetrics", viewport_metrics)
                    DrawFramework.unit_rect_batch.draw(shader)

                with offscreens[1].bind():
                    _setup_gl(clear=True)

                    shader = self._shaders[1]
                    shader.bind()
                    shader.uniform_sampler("edgesTex", offscreens[0].texture_color)
                    shader.uniform_sampler("searchTex", SMAA._textures[0])
                    shader.uniform_sampler("areaTex", SMAA._textures[1])
                    shader.uniform_float("viewportMetrics", viewport_metrics)
                    DrawFramework.unit_rect_batch.draw(shader)

                def _smaa_stage_2() -> None:
                    shader = self._shaders[2]
                    shader.bind()
                    shader.uniform_sampler("colorTex", texture)
                    shader.uniform_sampler("blendTex", offscreens[1].texture_color)
                    shader.uniform_float("viewportMetrics", viewport_metrics)
                    DrawFramework.unit_rect_batch.draw(shader)

                if self.is_final:
                    with gpu.matrix.push_pop():
                        _setup_gl(clear=False)
                        _smaa_stage_2()
                else:
                    with offscreens[2].bind():
                        _setup_gl(clear=True)
                        _smaa_stage_2()

                    return offscreens[2].texture_color
                # return None

        elif self.is_final:
            with gpu.matrix.push_pop():
                gpu.state.blend_set('ALPHA_PREMULT')
                gpu.matrix.load_matrix(IDENTITY_M4X4)
                gpu.matrix.load_projection_matrix(IDENTITY_M4X4)

                shader = gpu.shader.from_builtin('2D_IMAGE')
                shader.bind()
                shader.uniform_sampler("image", texture)

                DrawFramework.unit_rect_batch.draw(shader)
                # return None
        else:
            return texture


DrawFramework._SHADER_BASED_AA_IMPL_REGISTRY.append(SMAA)


class FXAA(AABase):
    _name = "FXAA"
    _description = "Fast approximate anti-aliasing"

    _cached_shader_code: None | tuple[str] = None
    _shader: GPUShader
    _value: float
    _value_0: float

    # NOTE: number of tuples always must be equal to number of elements in `_AAPreset` enumeration
    _quality_lookup: tuple[tuple[int]] = (
        (10, 11, 12, 13, 14, 15,),  # _AAPreset.LOW
        (20, 21, 22, 23, 24, 25,),  # _AAPreset.MEDIUM
        (26, 27, 28, 29,),  # _AAPreset.HIGH
        (39,)  # _AAPreset.ULTRA
    )

    @classmethod
    @property
    def prop_preset(cls) -> EnumProperty:
        return EnumProperty(
            items=(
                (AAPreset.NONE.name, "None", "Do not use FXAA post-processing"),
                (AAPreset.LOW.name, "Low", "Low quality (default medium dither)"),
                (AAPreset.MEDIUM.name, "Medium", "Medium quality (less dither, faster)"),
                (AAPreset.HIGH.name, "High", "High quality (less dither, more expensive)"),
                (AAPreset.ULTRA.name, "Ultra", "Ultra quality (no dither, very expensive)"),
            ),
            default=AAPreset.HIGH.name,
            options={'HIDDEN', 'SKIP_SAVE'},
            name="Preset",
            description="Fast approximate anti-aliasing quality preset"
        )

    @classmethod
    @property
    def prop_value(cls) -> FloatProperty:
        return FloatProperty(
            options={'HIDDEN', 'SKIP_SAVE'},
            min=0, max=1, default=1.0, step=0.001,
            subtype='PERCENTAGE',
            name="Quality",
            description="FXAA preset quality tuning"
        )

    @property
    def value(self) -> float:
        """
        FXAA quality value factor within the current preset.

        :return: Float in range `0.0 ... 1.0`
        :rtype: float
        """
        return self._value

    @value.setter
    def value(self, val: float) -> None:
        self._value = max(0.0, min(1.0, float(val)))

    def _do_eval_value(self) -> bool:
        if self._value_0 == self._value:
            return False
        self._value_0 = self._value
        return True

    def __init__(self, is_final: bool = True):
        AABase.__init__(self, is_final)

        self._value = 0.0
        self._value_0 = 0.0
        self._shader = None

    def _eval_update(self) -> None:
        if self._do_eval_gpu_framework():
            self._gpu_draw_framework = DrawFramework(num_offscreens=1)

        if self._preset != AAPreset.NONE:
            if self._shader is None or self._do_eval_preset() or self._do_eval_value():
                if FXAA._cached_shader_code is None:
                    with (open(os.path.join(os.path.dirname(__file__), "_fxaa", "fxaa_vert.glsl")) as fxaa_vert_file,
                          open(os.path.join(os.path.dirname(__file__), "_fxaa", "fxaa_frag.glsl")) as fxaa_frag_file,
                          open(os.path.join(os.path.dirname(__file__), "_fxaa", "fxaa_lib.glsl")) as fxaa_lib_file):
                        FXAA._cached_shader_code = (fxaa_vert_file.read(), fxaa_frag_file.read(), fxaa_lib_file.read())

                lookup = FXAA._quality_lookup[int(self._preset) - 2]
                preset_value = lookup[max(0, min(len(lookup) - 1, int(len(lookup) * self._value)))]
                arg_defines = f"#define FXAA_QUALITY__PRESET {preset_value}\n"
                # print(f"{self} shader quality preset define: {arg_defines}")
                vert_code, frag_code, lib_code = FXAA._cached_shader_code
                self._shader = GPUShader(
                    vertexcode=vert_code,
                    fragcode=frag_code,
                    libcode=lib_code,
                    defines=arg_defines,
                    name="fxaa"
                )
        else:
            self._shader = None
            if FXAA.do_reset_on_none_preset:
                FXAA._cached_shader_code = None

    def draw(self, texture: GPUTexture) -> None | GPUTexture:
        self._eval_update()

        def _draw_intern(texture: GPUTexture) -> None:
            gpu.matrix.load_matrix(IDENTITY_M4X4)
            gpu.matrix.load_projection_matrix(IDENTITY_M4X4)

            gpu.state.blend_set('ALPHA_PREMULT')

            if self._preset != AAPreset.NONE:
                shader = self._shader
                shader.bind()
                shader.uniform_sampler("image", texture)
                shader.uniform_float("viewportMetrics", DrawFramework.viewport_metrics)
            else:
                shader = gpu.shader.from_builtin('2D_IMAGE')
                shader.uniform_sampler("image", texture)

            DrawFramework.unit_rect_batch.draw(shader)

        if self.is_final:
            assert (self._gpu_draw_framework is None)

            with gpu.matrix.push_pop():
                _draw_intern(texture)

                # return None
        else:
            assert (isinstance(self._gpu_draw_framework, DrawFramework))

            with self._gpu_draw_framework as offscreens:
                with offscreens[0].bind():
                    fb = gpu.state.active_framebuffer_get()
                    fb.clear(color=(0.0, 0.0, 0.0, 0.0))
                    _draw_intern(texture)

                return offscreens[0].texture_color

        return texture


DrawFramework.register_shader_based_aa_impl(FXAA)
