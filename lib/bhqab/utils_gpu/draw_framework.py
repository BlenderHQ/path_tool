from __future__ import annotations

from enum import auto, IntEnum
from typing import (
    Iterator,
    Literal,
)
import os
import numpy as np

import bpy
from bpy.types import (
    Area,
    Context,
    Region,
    Space,
)

from bpy.props import (
    EnumProperty,
    FloatProperty,
)

from mathutils import (
    Matrix,
    Vector,
)

import gpu
from gpu.types import (
    GPUBatch,
    GPUOffScreen,
    GPUShader,
    GPUTexture,
)
from gpu_extras.batch import batch_for_shader

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


class AAPreset(IntEnum):
    """
    Enumerator of possible anti-aliasing presets. Contained in this API is mostly for documentation purposes, used
    internally.

    :cvar IntEnum NONE: No anti-aliasing
    :cvar IntEnum LOW: Low anti-aliasing level
    :cvar IntEnum MEDIUM: Medium anti-aliasing level
    :cvar IntEnum HIGH: High anti-aliasing level
    :cvar IntEnum ULTRA: Ultra anti-aliasing level
    """
    NONE = auto()
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    ULTRA = auto()


IDENTITY_M4X4 = Matrix.Identity(4)
"""
Identity matrix 4x4
"""


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


def get_viewport_metrics() -> Vector:
    """
    Viewport metrics for current viewport.

    :return: x = ``1.0 / width``, y = ``1.0 / height``, z = ``width``, w = ``height``
    :rtype: `Vector`_
    """
    viewport = gpu.state.viewport_get()
    w, h = viewport[2], viewport[3]
    return Vector((1.0 / w, 1.0 / h, w, h))


def _eval_unit_rect_batch(shader: GPUShader) -> GPUBatch:
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


class DrawFramework:
    """
    A framework for operations with several offscreens in several viewports with anti-aliasing support
    """
    __aa_methods_registry__: set[AABase] = set()

    _aa_instance: SMAA
    _off_frameworks: tuple[OffscreenFramework]

    __shader_2d_image__: GPUShader = gpu.shader.from_builtin('2D_IMAGE')
    __unit_rect_batch__: GPUBatch = _eval_unit_rect_batch(__shader_2d_image__)

    @classmethod
    @property
    def prop_aa_method(cls) -> EnumProperty:
        return EnumProperty(
            items=tuple((
                (_.name, _.name, _.description) for _ in cls.__aa_methods_registry__
            )),
            # default=cls.__aa_methods_registry__[0].name,
            options={'HIDDEN', 'SKIP_SAVE'},
            name="AA Method",
            description="Anti-aliasing method to be used",
        )

    @classmethod
    def register_aa_method(cls, method_class):
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
        self._off_frameworks = tuple((OffscreenFramework() for _ in range(num_offscreens)))

    def draw(self, *, texture: GPUTexture) -> None:
        """
        Draw method

        :param texture: Input texture
        :type texture: `GPUTexture`_
        """
        cls = self.__class__

        mvp_restore = gpu.matrix.get_projection_matrix() @ gpu.matrix.get_model_view_matrix()

        if (self._aa_instance is None) or (self._aa_instance._preset is AAPreset.NONE):
            with gpu.matrix.push_pop():
                gpu.matrix.load_matrix(IDENTITY_M4X4)
                gpu.matrix.load_projection_matrix(IDENTITY_M4X4)
                gpu.state.blend_set('ALPHA_PREMULT')

                shader = cls.__shader_2d_image__
                shader.uniform_sampler("image", texture)

                cls.__unit_rect_batch__.draw(shader)
        else:
            self._aa_instance.draw(texture=texture)

        gpu.matrix.load_matrix(mvp_restore)


class AABase(object):
    """
    Base class for anti-aliasing methods
    """
    _preset: AAPreset
    _preset_0: AAPreset

    def __init__(self):
        self._preset = AAPreset.NONE
        self._preset_0 = AAPreset.NONE

    @classmethod
    @property
    def name(cls):
        return cls.__name__

    @classmethod
    @property
    def description(cls):
        return cls.__doc__

    @property
    def preset(self) -> Literal['NONE', 'LOW', 'MEDIUM', 'HIGH', 'ULTRA']:
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

    def _do_preset_eval(self) -> bool:
        if self._preset_0 != self._preset:
            self._preset_0 = self._preset
            return True
        return False

    def draw(self, *, texture: GPUTexture) -> None:
        """
        Draw method. Performs a basic check before calling the main method

        :param texture: Input texture
        :type texture: `GPUTexture`_
        """
        assert (AAPreset.NONE != self._preset)


class SMAA(AABase):
    """Sub-pixel morphological anti-aliasing"""

    _off_framework_stage_0: OffscreenFramework
    _off_framework_stage_1: OffscreenFramework

    __shader_code__: None | tuple[str] = None
    __textures__: None | tuple[GPUTexture] = None
    """(searchTex, areaTex)"""

    _shaders: None | tuple[GPUShader]
    _batches: None | tuple[GPUBatch]

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

    @classmethod
    def __eval_textures(cls) -> None:
        if cls.__textures__ is None:
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
                    os.path.join(os.path.dirname(__file__), "_smaa", name),
                    dtype=np.ubyte
                ).astype(dtype=np.float32) / 0xff

            cls.__textures__ = (
                # SearchTex
                GPUTexture(
                    size=(_SMAA_SEARCHTEX_WIDTH, _SMAA_SEARCHTEX_HEIGHT),
                    format='R8',
                    data=gpu.types.Buffer('FLOAT', _SMAA_SEARCHTEX_SIZE,
                                          _float32_arr_from_byte_file("searchtex.np"))
                ),
                # AreaTex
                GPUTexture(
                    size=(_SMAA_AREATEX_WIDTH, _SMAA_AREATEX_HEIGHT),
                    format='RG8',
                    data=gpu.types.Buffer('FLOAT', _SMAA_AREATEX_SIZE, _float32_arr_from_byte_file("areatex.np"))
                )
            )

    def _eval_shaders(self):
        cls = self.__class__

        if AAPreset.NONE != self._preset:
            _do_update_on_preset_change = self._do_preset_eval()
            if self._shaders is None or _do_update_on_preset_change:
                if cls.__shader_code__ is None:
                    with (
                        open(os.path.join(os.path.dirname(__file__), "_smaa", "smaa_vert.glsl"), 'r') as smaa_vert_file,
                        open(os.path.join(os.path.dirname(__file__), "_smaa", "smaa_frag.glsl"), 'r') as smaa_frag_file,
                        open(os.path.join(os.path.dirname(__file__), "_smaa", "smaa_lib.glsl"), 'r') as smaa_lib_file,
                        open(os.path.join(os.path.dirname(__file__), "_smaa", "smaa_def.glsl"), 'r') as smaa_def_file
                    ):
                        cls.__shader_code__ = (
                            smaa_vert_file.read(),
                            smaa_frag_file.read(),
                            smaa_lib_file.read(),
                            smaa_def_file.read()
                        )
                vertexcode, fragcode, libcode, defines = cls.__shader_code__

                self._shaders = tuple((
                    GPUShader(
                        vertexcode=vertexcode,
                        fragcode=fragcode,
                        defines=(f"\n#define SMAA_STAGE {i}\n"
                                 f"#define SMAA_PRESET_{self._preset.name}\n"
                                 f"{defines}\n"
                                 f"{libcode}\n"),
                        name=f"SMAA Stage {i}",
                    ) for i in range(3)
                ))

                self._batches = tuple((_eval_unit_rect_batch(shader) for shader in self._shaders))
        else:
            self._shaders = None
            self._batches = None

    def modal_eval(self, *, format: Literal['RGBA8', 'RGBA16', 'RGBA16F', 'RGBA32F'] = 'RGBA8', percentage: int = 100):
        """
        The class and instance data update method should be called in the modal part of the control operator

        :param format: Required format of data buffers, defaults to 'RGBA8'
        :type format: Literal['RGBA8', 'RGBA16', 'RGBA16F', 'RGBA32F'], optional
        :param percentage: Resolution percentage, defaults to 100
        :type percentage: int, optional
        """
        cls = self.__class__

        cls.__eval_textures()
        self._eval_shaders()

        self._off_framework_stage_0.modal_eval(format=format, percentage=percentage)
        self._off_framework_stage_1.modal_eval(format=format, percentage=percentage)

    def __init__(self):
        super().__init__()
        self._shaders = None
        self._batches = None
        self._off_framework_stage_0 = OffscreenFramework()
        self._off_framework_stage_1 = OffscreenFramework()

    def draw(self, *, texture: GPUTexture) -> None:
        """
        Draw method

        :param texture: Input texture
        :type texture: `GPUTexture`_
        """
        super().draw(texture=texture)

        cls = self.__class__
        viewport_metrics = get_viewport_metrics()

        def _setup_gl(clear: bool) -> None:
            if clear:
                fb = gpu.state.active_framebuffer_get()
                fb.clear(color=(0.0, 0.0, 0.0, 0.0))

            gpu.matrix.load_matrix(IDENTITY_M4X4)
            gpu.matrix.load_projection_matrix(IDENTITY_M4X4)
            gpu.state.blend_set('ALPHA_PREMULT')

        offscreen_stage_0 = self._off_framework_stage_0.get()
        with offscreen_stage_0.bind():
            _setup_gl(clear=True)
            shader = self._shaders[0]
            shader.bind()
            shader.uniform_sampler("colorTex", texture)
            shader.uniform_float("viewportMetrics", viewport_metrics)
            self._batches[0].draw(shader)

        offscreen_stage_1 = self._off_framework_stage_1.get()
        with offscreen_stage_1.bind():
            _setup_gl(clear=True)

            shader = self._shaders[1]
            shader.bind()
            shader.uniform_sampler("edgesTex", offscreen_stage_0.texture_color)
            shader.uniform_sampler("searchTex", cls.__textures__[0])
            shader.uniform_sampler("areaTex", cls.__textures__[1])
            shader.uniform_float("viewportMetrics", viewport_metrics)
            self._batches[1].draw(shader)

        with gpu.matrix.push_pop():
            _setup_gl(clear=False)
            shader = self._shaders[2]
            shader.bind()
            shader.uniform_sampler("colorTex", texture)
            shader.uniform_sampler("blendTex", offscreen_stage_1.texture_color)
            shader.uniform_float("viewportMetrics", viewport_metrics)
            self._batches[2].draw(shader)


DrawFramework.register_aa_method(SMAA)


class FXAA(AABase):
    """Fast approximate anti-aliasing"""

    _value: float
    _value_0: float

    _off_framework: OffscreenFramework
    _shader: None | GPUShader
    _batch: None | GPUBatch

    __shader_code__: None | tuple[str] = None

    # NOTE: number of tuples always must be equal to number of elements in `_AAPreset` enumeration
    __quality_lookup__: tuple[tuple[int]] = (
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
        if AAPreset.NONE != self._preset:
            _do_update_on_preset_change = self._do_preset_eval()
            _do_update_on_value_change = self._do_value_eval()
            if self._shader is None or _do_update_on_preset_change or _do_update_on_value_change:
                if cls.__shader_code__ is None:
                    with (open(os.path.join(os.path.dirname(__file__), "_fxaa", "fxaa_vert.glsl")) as fxaa_vert_file,
                          open(os.path.join(os.path.dirname(__file__), "_fxaa", "fxaa_frag.glsl")) as fxaa_frag_file,
                          open(os.path.join(os.path.dirname(__file__), "_fxaa", "fxaa_lib.glsl")) as fxaa_lib_file):
                        cls.__shader_code__ = (fxaa_vert_file.read(), fxaa_frag_file.read(), fxaa_lib_file.read())

                lookup = cls.__quality_lookup__[int(self._preset) - 2]
                preset_value = lookup[max(0, min(len(lookup) - 1, int(len(lookup) * self._value)))]

                defines = f"#define FXAA_QUALITY__PRESET {preset_value}\n"
                vertexcode, fragcode, libcode = cls.__shader_code__

                self._shader = GPUShader(
                    vertexcode=vertexcode,
                    fragcode=fragcode,
                    libcode=libcode,
                    defines=defines,
                    name="FXAA",
                )
                self._batch = _eval_unit_rect_batch(self._shader)
        else:
            self._shader = None
            self._batch = None

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
        self._shader = None
        self._batch = None
        self._off_framework = OffscreenFramework()

    def draw(self, *, texture: GPUTexture) -> None:
        """
        Draw method

        :param texture: Input texture
        :type texture: `GPUTexture`_
        """
        shader = self._shader

        super().draw(texture=texture)

        viewport_metrics = get_viewport_metrics()

        with gpu.matrix.push_pop():
            gpu.matrix.load_matrix(IDENTITY_M4X4)
            gpu.matrix.load_projection_matrix(IDENTITY_M4X4)
            gpu.state.blend_set('ALPHA_PREMULT')

            shader.bind()
            shader.uniform_sampler("image", texture)
            shader.uniform_float("viewportMetrics", viewport_metrics)
            self._batch.draw(shader)


DrawFramework.register_aa_method(FXAA)
