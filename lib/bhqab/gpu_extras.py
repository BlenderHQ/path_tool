from __future__ import annotations

from typing import Iterator, Literal

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

from mathutils import Matrix

import gpu
from gpu.types import (
    GPUBatch,
    GPUOffScreen,
    GPUShader,
    GPUTexture,
    GPUVertBuf,
    GPUVertFormat,
)

from mathutils import Vector

import os
import numpy as np
from enum import (
    auto,
    IntEnum,
)


class shader_meta(type):
    @property
    def SHADER_FILE_EXTENSION(cls):
        return cls._SHADER_FILE_EXTENSION

    @property
    def SEPARATOR_CHAR(cls):
        return cls._SEPARATOR_CHAR

    @property
    def SUFFIX_VERTEX(cls):
        return cls._SUFFIX_VERTEX

    @property
    def SUFFIX_FRAGMENT(cls):
        return cls._SUFFIX_FRAGMENT

    @property
    def SUFFIX_GEOMETRY(cls):
        return cls._SUFFIX_GEOMETRY

    @property
    def SUFFIX_DEFINES(cls):
        return cls._SUFFIX_DEFINES

    @property
    def SUFFIX_LIBRARY(cls) -> str:
        return cls._SUFFIX_LIBRARY


class shader(metaclass=shader_meta):
    """Shader utility class. After calling the :py:func:`bhqab.shaders.shader.generate_shaders` method of the class,
    the shaders will be available as class attributes.

    For example, there are shader files ``my_shader_vert.glsl`` and ``my_shader_frag.glsl``. After generating the
    shaders, the access to the shader will be done through the ``shader.my_shader``.

    Which would return instance of `gpu.types.GPUShader`_.

    Attributes:
        SHADER_FILE_EXTENSION (str): Constant ``".glsl"`` (readonly).
        SEPARATOR_CHAR (str): Constant ``'_'`` (readonly).
        SUFFIX_VERTEX (str): Constant ``"vert"`` (readonly).
        SUFFIX_FRAGMENT (str): Constant ``"frag"`` (readonly).
        SUFFIX_GEOMETRY (str): Constant ``"geom"`` (readonly).
        SUFFIX_DEFINES (str): Constant ``"def"`` (readonly).
        SUFFIX_LIBRARY (str): Constant ``"lib"`` (readonly).
    """

    _SHADER_FILE_EXTENSION = ".glsl"
    _SEPARATOR_CHAR = '_'
    _SUFFIX_VERTEX = "vert"
    _SUFFIX_FRAGMENT = "frag"
    _SUFFIX_GEOMETRY = "geom"
    _SUFFIX_DEFINES = "def"
    _SUFFIX_LIBRARY = "lib"

    @classmethod
    def generate_shaders(cls, dir_path: str) -> bool:
        """
        Generate shaders cache.

        :param dir_path: Directory to read shader files from
        :type dir_path: str
        :raises NameError: If name of shader file is incorrect
        :return: True means that shader cache was generated
        :rtype: bool
        """
        if bpy.app.background:
            return False

        shader_endings = (
            cls.SUFFIX_VERTEX,
            cls.SUFFIX_FRAGMENT,
            cls.SUFFIX_GEOMETRY,
            cls.SUFFIX_DEFINES,
            cls.SUFFIX_LIBRARY
        )

        _shader_dict = {}
        _shader_library = ""
        _defines_library = ""

        for file_name in os.listdir(dir_path):
            file_path = os.path.join(dir_path, file_name)

            if not os.path.isfile(file_path):
                continue

            name, extension = os.path.splitext(file_name)

            if extension != cls.SHADER_FILE_EXTENSION:
                continue

            name_split = name.split(cls.SEPARATOR_CHAR)

            if len(name_split) == 1:
                raise NameError("Shader file name should have [some_name]_[type].glsl pattern")
            if len(name_split) == 2:
                shader_name, shader_type = name_split
            else:
                shader_type = name_split[-1]
                shader_name = '_'.join(name_split[:-1])

            if shader_type in shader_endings[0:3]:
                if shader_name not in _shader_dict:
                    _shader_dict[shader_name] = [None for _ in range(5)]
                    _shader_dict[shader_name][0] = ""
                    _shader_dict[shader_name][1] = ""
                shader_index = shader_endings.index(shader_type)
                with open(file_path, 'r') as code:
                    data = code.read()
                    _shader_dict[shader_name][shader_index] = data

            elif shader_type == cls.SUFFIX_LIBRARY:
                with open(file_path, 'r') as code:
                    data = code.read()
                    _shader_library += f"\n\n{data}\n\n"

            elif shader_type == cls.SUFFIX_DEFINES:
                with open(file_path, 'r') as code:
                    data = code.read()
                    _defines_library += f"\n\n{data}\n\n"

        for shader_name in _shader_dict.keys():
            shader_code = _shader_dict[shader_name]
            vertex_code, frag_code, geo_code, lib_code, defines = shader_code
            if _shader_library:
                lib_code = _shader_library
            if _defines_library:
                defines = _defines_library

            shader_keywords = dict(
                vertexcode=vertex_code,
                fragcode=frag_code,
                geocode=geo_code,
                libcode=lib_code,
                defines=defines
            )

            shader_keywords = dict(filter(lambda item: item[1] is not None, shader_keywords.items()))

            try:
                data = GPUShader(**shader_keywords)
            except Exception:
                # "Formatted glsl error by Blender" after compilation fault and than:
                print(f"caused while compiling shader \"{shader_name}\".")
            else:
                setattr(cls, shader_name, data)

        return True


class _gpu_draw_framework_meta(type):
    @property
    def prop_smaa_preset_enum(cls) -> EnumProperty:
        return cls._prop_smaa_preset_enum

    @property
    def prop_fxaa_preset_enum(cls) -> EnumProperty:
        return cls._prop_fxaa_preset_enum

    @property
    def prop_fxaa_value(cls) -> FloatProperty:
        return cls._prop_fxaa_quality_value

    @property
    def prop_res_mult(cls):
        return cls._prop_res_mult


class _AAPreset(IntEnum):
    NONE = auto()
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    ULTRA = auto()


class GPUDrawFramework(metaclass=_gpu_draw_framework_meta):
    """

    Args:
        num_offscreens (int, optional): Number of offscreen buffers to work with. Defaults to 1.

        smaa_preset (Literal['NONE', 'LOW', 'MEDIUM', 'HIGH', 'ULTRA'], optional): Initial SMAA preset value.
            `'NONE'` means that the textures and post-process shaders necessary for the operation of SMAA will not be
            generated by default - this will save memory. Defaults to 'NONE'.

        fxaa_preset (Literal['NONE', 'LOW', 'MEDIUM', 'HIGH', 'ULTRA'], optional): Initial FXAA preset value.
            `'NONE'` means that post-process shaders necessary for the operation of FXAA will not be
            generated by default - this will save memory. Defaults to 'NONE'.

        fxaa_value (float, optional): Initial FXAA quality value factor within the current preset. Defaults to 1.0.

        res_mult (Literal[1, 2, 4, 8] | Literal['1', '2', '4', '8'], optional): Initial multiplier of the resolution of
            offscreen buffers. Defaults to 1.

    Attributes:
        prop_res_mult (`bpy.props.EnumProperty`_): A multiplier of the resolution of offscreen buffers property that can
            be used in the user preferences of the addon.

            Expands to:

            .. code-block:: python

                EnumProperty(
                    items=(
                        ('1', "1X", "Do not use super-sampling"),
                        ('2', "2X", "2X super-sampling"),
                        ('4', "4X", "2X super-sampling"),
                        ('8', "8X", "8X super-sampling"),
                    ),
                    default='2',
                    options={'HIDDEN', 'SKIP_SAVE'},
                    name="AA Samples",
                    description="Resolution multiplier for super-sampled rendering",
                )

        prop_smaa_preset_enum (`bpy.props.EnumProperty`_): SMAA preset property that can be used in the user preferences
            of the addon.

            Expands to:

            .. code-block:: python

                EnumProperty(
                        items=(
                            ('NONE', "None", "Do not use SMAA post-processing"),
                            ('LOW', "Low", "Low SMAA quality"),
                            ('MEDIUM', "Medium", "Medium SMAA quality"),
                            ('HIGH', "High", "High SMAA quality"),
                            ('ULTRA', "Ultra", "Ultra SMAA quality"),
                        ),
                        default='HIGH',
                        options={'HIDDEN', 'SKIP_SAVE'},
                        name="SMAA Preset",
                        description="Sub-pixel morphological anti-aliasing quality preset"
                    )

        prop_fxaa_preset_enum (`bpy.props.EnumProperty`_): FXAA preset property that can be used in the user preferences
            of the addon.

            Expands to:

            .. code-block:: python

                EnumProperty(
                    items=(
                        ('NONE', "None", "Do not use FXAA post-processing"),
                        ('LOW', "Low", "Low quality (default medium dither)"),
                        ('MEDIUM', "Medium", "Medium quality (less dither, faster)"),
                        ('HIGH', "High", "High quality (less dither, more expensive)"),
                        ('ULTRA', "Ultra", "Ultra quality (no dither, very expensive)"),
                    ),
                    default='HIGH',
                    options={'HIDDEN', 'SKIP_SAVE'},
                    name="FXAA Preset",
                    description="Fast approximate anti-aliasing quality preset"
                )

        prop_fxaa_value (`bpy.props.FloatProperty`_): FXAA preset quality tuning property that can be used in the user
            preferences of the addon.

            Expands to:

            .. code-block:: python

                FloatProperty(
                    options={'HIDDEN', 'SKIP_SAVE'},
                    min=0, max=1, default=1.0, step=0.001,
                    subtype='PERCENTAGE',
                    name="Quality",
                    description="FXAA preset quality tuning"
                )

    """

    def _prop_update(self, _context: Context) -> None:
        GPUDrawFramework._mark_tag_redraw_regions()

    _prop_res_mult = EnumProperty(
        items=(
            ('1', "1X", "Do not use super-sampling"),
            ('2', "2X", "2X super-sampling"),
            ('4', "4X", "2X super-sampling"),
            ('8', "8X", "8X super-sampling"),
        ),
        default='2',
        update=_prop_update,
        options={'HIDDEN', 'SKIP_SAVE'},
        name="AA Samples",
        description="Resolution multiplier for super-sampled rendering",
    )

    _prop_fxaa_quality_value = FloatProperty(
        update=_prop_update,
        options={'HIDDEN', 'SKIP_SAVE'},
        min=0, max=1, default=1.0, step=0.001,
        subtype='PERCENTAGE',
        name="Quality",
        description="FXAA preset quality tuning"
    )

    _prop_smaa_preset_enum = EnumProperty(
        items=(
            (_AAPreset.NONE.name, "None", "Do not use SMAA post-processing"),
            (_AAPreset.LOW.name, "Low", "Low SMAA quality"),
            (_AAPreset.MEDIUM.name, "Medium", "Medium SMAA quality"),
            (_AAPreset.HIGH.name, "High", "High SMAA quality"),
            (_AAPreset.ULTRA.name, "Ultra", "Ultra SMAA quality"),
        ),
        update=_prop_update,
        default=_AAPreset.HIGH.name,
        options={'HIDDEN', 'SKIP_SAVE'},
        name="SMAA Preset",
        description="Sub-pixel morphological anti-aliasing quality preset"
    )

    _prop_fxaa_preset_enum = EnumProperty(
        items=(
            (_AAPreset.NONE.name, "None", "Do not use FXAA post-processing"),
            (_AAPreset.LOW.name, "Low", "Low quality (default medium dither)"),
            (_AAPreset.MEDIUM.name, "Medium", "Medium quality (less dither, faster)"),
            (_AAPreset.HIGH.name, "High", "High quality (less dither, more expensive)"),
            (_AAPreset.ULTRA.name, "Ultra", "Ultra quality (no dither, very expensive)"),
        ),
        update=_prop_update,
        default=_AAPreset.HIGH.name,
        options={'HIDDEN', 'SKIP_SAVE'},
        name="FXAA Preset",
        description="Fast approximate anti-aliasing quality preset"
    )

    _addon_pref: bpy.types.AddonPreferences
    _num_offscreens: int

    _smaa_preset: _AAPreset
    _smaa_preset_0: _AAPreset

    _smaa_shader_arr: list[GPUShader]

    _smaa_cached_code: tuple[str] = ()
    _smaa_tex_arr: tuple[None | GPUTexture] = ()

    _fxaa_preset: _AAPreset
    _fxaa_value: float
    _fxaa_preset_0: _AAPreset
    _fxaa_value_0: float

    _fxaa_shader: None | GPUShader

    # NOTE: number of tuples always must be equal to number of elements in `AAPreset` enumeration
    _fxaa_quality_preset_arr: tuple[tuple[int]] = (
        (10, 11, 12, 13, 14, 15,),  # _AAPreset.LOW
        (20, 21, 22, 23, 24, 25,),  # _AAPreset.MEDIUM
        (26, 27, 28, 29,),  # _AAPreset.HIGH
        (39,)  # _AAPreset.ULTRA
    )
    _fxaa_cached_code: list[str] = []

    _batch: None | GPUBatch = None
    _image_shader: None | GPUShader
    _offscreen_arr: dict[Region, list[GPUOffScreen]]

    _res_mult: Literal[1, 2, 4, 8]

    @property
    def viewport_metrics(self) -> Vector:
        """
        Viewport metrics for current viewport.

        :return: x = ``1.0 / width``, y = ``1.0 / height``, z = ``width``, w = ``height``
        :rtype: Vector
        """
        viewport = gpu.state.viewport_get()
        w, h = viewport[2], viewport[3]
        return Vector((1.0 / w, 1.0 / h, float(w), float(h)))

    @property
    def res_mult(self) -> Literal[1, 2, 4, 8]:
        """
        Multiplier of the resolution of offscreen buffers. The value can be set to either a number or a string from the
        list: [`'1'`, `'2'`, `'3'`, `'4'`].

        :return: Multiplier
        :rtype: Literal[1, 2, 4, 8]
        """
        return self._res_mult

    @res_mult.setter
    def res_mult(self, val: Literal[1, 2, 4, 8] | Literal['1', '2', '4', '8']):
        val = int(val)
        if val in {1, 2, 4, 8}:
            self._res_mult = val
            if val != self._res_mult:
                GPUDrawFramework._mark_tag_redraw_regions()

    @staticmethod
    def _mark_tag_redraw_regions():
        for area in GPUDrawFramework.iter_areas(bpy.context, area_type='VIEW_3D'):
            for region in GPUDrawFramework.iter_area_regions(area, region_type='WINDOW'):
                region.tag_redraw()

    @property
    def smaa_preset(self) -> str:
        """
        SMAA preset.

        * ``NONE`` - Do not use SMAA post-processing.
        * ``LOW`` - Low quality.
        * ``MEDIUM`` - Medium quality.
        * ``HIGH`` - High quality.
        * ``ULTRA`` - Ultra quality.

        :return: _description_
        :rtype: String in [`'NONE'`, `'LOW'`, `'MEDIUM'`, `'HIGH'`, `'ULTRA'`]
        """
        return self._smaa_preset

    @smaa_preset.setter
    def smaa_preset(self, val: Literal['NONE', 'LOW', 'MEDIUM', 'HIGH']) -> None:
        self._smaa_preset = GPUDrawFramework._eval_preset_value(val)
        if self._smaa_preset != self._smaa_preset_0:
            GPUDrawFramework._mark_tag_redraw_regions()

    @property
    def fxaa_preset(self) -> str:
        """
        FXAA preset.

        * ``NONE`` - Do not use FXAA post-processing.
        * ``LOW`` - Low quality (default medium dither).
        * ``MEDIUM`` - Medium quality (less dither, faster).
        * ``HIGH`` - High quality (less dither, more expensive).
        * ``ULTRA`` - Ultra quality (no dither, very expensive).

        :return: String in [`'NONE'`, `'LOW'`, `'MEDIUM'`, `'HIGH'`, `'ULTRA'`]
        :rtype: str
        """
        return self._fxaa_preset

    @fxaa_preset.setter
    def fxaa_preset(self, val: Literal['NONE', 'LOW', 'MEDIUM', 'HIGH', 'ULTRA']) -> None:
        self._fxaa_preset = GPUDrawFramework._eval_preset_value(val)
        if self._fxaa_preset != self._fxaa_preset_0:
            GPUDrawFramework._mark_tag_redraw_regions()

    @property
    def fxaa_value(self) -> float:
        """
        FXAA quality value factor within the current preset.

        :return: Float in range `0.0 ... 1.0`
        :rtype: float
        """
        return self._fxaa_value

    @fxaa_value.setter
    def fxaa_value(self, val: float) -> None:
        self._fxaa_value = max(0.0, min(1.0, float(val)))
        if self._fxaa_value != self._fxaa_value_0:
            GPUDrawFramework._mark_tag_redraw_regions()

    @staticmethod
    def _eval_preset_value(val: str = 'NONE') -> _AAPreset:
        val_eval = _AAPreset.NONE
        try:
            val_eval = _AAPreset[val]
        except KeyError:
            str_possible_values = ', '.join(_AAPreset.__members__.keys())
            raise KeyError(f"Key '{val}' not found in {str_possible_values}")
        return val_eval

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

    def _eval_update(self) -> None:
        cls = GPUDrawFramework

        num_offs_eval = self._num_offscreens
        if self._fxaa_preset != _AAPreset.NONE:
            num_offs_eval += 1
        if self._smaa_preset != _AAPreset.NONE:
            num_offs_eval += 2

        for area in GPUDrawFramework.iter_areas(bpy.context, area_type='VIEW_3D'):
            for region in GPUDrawFramework.iter_area_regions(area, region_type='WINDOW'):
                do_update = False
                if region in self._offscreen_arr:
                    # Clear unnecessary offscreen buffers to free up memory space (if SMAA/FXAA was set to NONE)
                    offs_region = self._offscreen_arr[region]
                    if len(offs_region) > num_offs_eval:
                        self._offscreen_arr[region] = offs_region[:num_offs_eval]

                    elif len(offs_region) < num_offs_eval:
                        self._offscreen_arr[region].extend(list((
                            GPUOffScreen(region.width, region.height, format='RGBA32F')
                            for _ in range(num_offs_eval - self._num_offscreens)
                        )))

                    offscreen_0 = self._offscreen_arr[region][0]
                    if (
                            int(offscreen_0.width / self._res_mult) != region.width
                            or int(offscreen_0.height / self._res_mult) != region.height
                    ):
                        do_update = True

                else:
                    do_update = True

                if do_update:
                    self._offscreen_arr[region] = list((
                        GPUOffScreen(
                            region.width * (self._res_mult if _ < self._num_offscreens else 1),
                            region.height * (self._res_mult if _ < self._num_offscreens else 1),
                            format='RGBA32F')
                        for _ in range(num_offs_eval)
                    ))

        curr_dir = os.path.dirname(__file__)

        if _AAPreset.NONE != self._smaa_preset:
            if not cls._smaa_cached_code:
                smaa_dir = os.path.join(curr_dir, "_smaa")
                with (open(os.path.join(smaa_dir, "smaa_vert.glsl"), 'r') as smaa_vert_file,
                        open(os.path.join(smaa_dir, "smaa_frag.glsl"), 'r') as smaa_frag_file,
                        open(os.path.join(smaa_dir, "smaa_lib.glsl"), 'r') as smaa_lib_file,
                        open(os.path.join(smaa_dir, "smaa_def.glsl"), 'r') as smaa_def_file):
                    cls._smaa_cached_code = (
                        smaa_vert_file.read(),
                        smaa_frag_file.read(),
                        smaa_lib_file.read(),
                        smaa_def_file.read()
                    )

            if not cls._smaa_tex_arr:
                from ._smaa import _smaa_tex_data

                float_data = (np.array(_smaa_tex_data.searchTexBytes, dtype=np.byte)).astype(np.float32) / 255

                search_tex = GPUTexture(
                    size=(_smaa_tex_data.SEARCHTEX_SIZE),
                    format='R32F',
                    data=gpu.types.Buffer('FLOAT', _smaa_tex_data.SEARCHTEX_SIZE, float_data)
                )

                float_data = (np.array(_smaa_tex_data.areaTexBytes, dtype=np.byte)).astype(np.float32) / 255
                area_tex = GPUTexture(
                    size=(_smaa_tex_data.AREATEX_WIDTH, _smaa_tex_data.AREATEX_HEIGHT),
                    format='RG32F',
                    data=gpu.types.Buffer('FLOAT', _smaa_tex_data.AREATEX_SIZE, float_data)
                )

                del _smaa_tex_data

                cls._smaa_tex_arr = (search_tex, area_tex)

            if self._smaa_preset_0 != self._smaa_preset:
                self._smaa_shader_arr.clear()
                for i in range(3):
                    self._smaa_shader_arr.append(
                        GPUShader(
                            vertexcode=cls._smaa_cached_code[0],
                            fragcode=cls._smaa_cached_code[1],
                            defines=(f"\n#define SMAA_STAGE {i}\n"
                                     f"#define SMAA_PRESET_{self._smaa_preset.name}\n"
                                     f"{cls._smaa_cached_code[3]}\n"
                                     f"{cls._smaa_cached_code[2]}\n"),
                            name=f"smaa_stage_{i}",
                        )
                    )
                self._smaa_preset_0 = self._smaa_preset

        if _AAPreset.NONE != self._fxaa_preset:
            if not cls._fxaa_cached_code:
                with (
                        open(os.path.join(curr_dir, "_fxaa", "fxaa_vert.glsl"), 'r') as fxaa_vert_file,
                        open(os.path.join(curr_dir, "_fxaa", "fxaa_frag.glsl"), 'r') as fxaa_frag_file,
                        open(os.path.join(curr_dir, "_fxaa", "fxaa_lib.glsl"), 'r') as fxaa_common_file,
                ):
                    cls._fxaa_cached_code = (fxaa_vert_file.read(), fxaa_frag_file.read(), fxaa_common_file.read())

            if self._fxaa_preset_0 != self._fxaa_preset or self._fxaa_value_0 != self._fxaa_value:
                fxaa_preset_search_arr = cls._fxaa_quality_preset_arr[int(self._fxaa_preset) - 2]
                fxaa_p = fxaa_preset_search_arr[
                    max(
                        0,
                        min(
                            len(fxaa_preset_search_arr) - 1,
                            int(len(fxaa_preset_search_arr) * self._fxaa_value)
                        )
                    )
                ]
                self._fxaa_shader = GPUShader(
                    vertexcode=cls._fxaa_cached_code[0],
                    fragcode=cls._fxaa_cached_code[1],
                    libcode=cls._fxaa_cached_code[2],
                    defines=f"#define FXAA_QUALITY__PRESET {fxaa_p}\n"
                )
                self._fxaa_preset_0 = self._fxaa_preset
                self._fxaa_value_0 = self._fxaa_value

        if cls._batch is None:
            vert_fmt = GPUVertFormat()
            vert_fmt.attr_add(id="pos", comp_type='F32', len=2, fetch_mode='FLOAT')
            vert_fmt.attr_add(id="texCoord", comp_type='F32', len=2, fetch_mode='FLOAT')

            vbo = GPUVertBuf(len=4, format=vert_fmt)
            vbo.attr_fill("pos", ((-1, -1), (-1, 1), (1, 1), (1, -1)))
            vbo.attr_fill("texCoord", ((0, 0), (0, 1), (1, 1), (1, 0)))

            cls._batch = gpu.types.GPUBatch(type='TRI_FAN', buf=vbo)

    def __init__(self,
                 num_offscreens: int = 1,
                 smaa_preset: Literal['NONE', 'LOW', 'MEDIUM', 'HIGH', 'ULTRA'] = 'NONE',
                 fxaa_preset: Literal['NONE', 'LOW', 'MEDIUM', 'HIGH', 'ULTRA'] = 'NONE',
                 fxaa_value: float = 1.0,
                 res_mult: Literal[1, 2, 4, 8] | Literal['1', '2', '4', '8'] = 1,
                 ):
        cls = GPUDrawFramework

        self._num_offscreens = num_offscreens

        self._smaa_preset = cls._eval_preset_value(smaa_preset)
        self._fxaa_preset = cls._eval_preset_value(fxaa_preset)
        self._fxaa_value = fxaa_value

        self._smaa_preset_0 = _AAPreset.NONE
        self._fxaa_preset_0 = _AAPreset.NONE
        self._fxaa_value_0 = 0.0
        self._smaa_shader_arr = list()
        self._smaa_tex_arr = tuple()
        self._fxaa_shader = None
        self._offscreen_arr = dict()

        self.res_mult = res_mult

        self._eval_update()

    def __enter__(self) -> tuple[GPUOffScreen]:
        self._eval_update()
        return tuple(self._offscreen_arr[bpy.context.region][:self._num_offscreens])

    def __exit__(self, type, value, traceback):
        cls = GPUDrawFramework

        def _draw_image(tex: GPUTexture) -> None:
            with gpu.matrix.push_pop():
                gpu.matrix.load_matrix(Matrix.Identity(4))
                gpu.matrix.load_projection_matrix(Matrix.Identity(4))

                gpu.state.blend_set('ALPHA_PREMULT')

                shader = gpu.shader.from_builtin('2D_IMAGE')
                shader.bind()
                shader.uniform_sampler("image", tex)
                cls._batch.draw(shader)

        offscreen = self._offscreen_arr[bpy.context.region]

        original_mvp_mat = gpu.matrix.get_projection_matrix() @ gpu.matrix.get_model_view_matrix()

        if _AAPreset.NONE == self._smaa_preset == self._fxaa_preset:
            _draw_image(offscreen[self._num_offscreens - 1].texture_color)
        else:
            off_color_index = self._num_offscreens - 1

            if _AAPreset.NONE != self._fxaa_preset:
                off_color, off_fxaa = offscreen[off_color_index:off_color_index + 2]

                with off_fxaa.bind():
                    fb = gpu.state.active_framebuffer_get()
                    fb.clear(color=(0.0, 0.0, 0.0, 0.0))

                    shader = self._fxaa_shader
                    shader.bind()
                    gpu.state.blend_set('ALPHA_PREMULT')
                    shader.uniform_sampler("image", off_color.texture_color)
                    shader.uniform_float("viewportMetrics", self.viewport_metrics)
                    self._batch.draw(shader)

                if _AAPreset.NONE == self._smaa_preset:
                    _draw_image(off_fxaa.texture_color)

            if _AAPreset.NONE != self._smaa_preset:
                if _AAPreset.NONE == self._fxaa_preset:
                    off_color, off_edges, off_weights = offscreen[off_color_index:off_color_index + 3]
                else:
                    off_color, off_edges, off_weights = offscreen[off_color_index + 1:off_color_index + 4]

                with off_edges.bind():
                    fb = gpu.state.active_framebuffer_get()
                    fb.clear(color=(0.0, 0.0, 0.0, 0.0))

                    with gpu.matrix.push_pop():
                        gpu.state.blend_set('ALPHA_PREMULT')
                        shader = self._smaa_shader_arr[0]
                        shader.bind()
                        shader.uniform_sampler("colorTex", off_color.texture_color)
                        shader.uniform_float("viewportMetrics", self.viewport_metrics)
                        cls._batch.draw(shader)

                with off_weights.bind():
                    fb = gpu.state.active_framebuffer_get()
                    fb.clear(color=(0.0, 0.0, 0.0, 0.0))

                    with gpu.matrix.push_pop():
                        gpu.state.blend_set('ALPHA_PREMULT')

                        shader = self._smaa_shader_arr[1]
                        shader.bind()
                        shader.uniform_sampler("edgesTex", off_edges.texture_color)
                        shader.uniform_sampler("searchTex", cls._smaa_tex_arr[0])
                        shader.uniform_sampler("areaTex", cls._smaa_tex_arr[1])
                        shader.uniform_float("viewportMetrics", self.viewport_metrics)
                        cls._batch.draw(shader)

                with gpu.matrix.push_pop():
                    gpu.state.blend_set('ALPHA_PREMULT')

                    shader = self._smaa_shader_arr[2]
                    shader.bind()
                    shader.uniform_sampler("colorTex", off_color.texture_color)
                    shader.uniform_sampler("blendTex", off_weights.texture_color)
                    shader.uniform_float("viewportMetrics", self.viewport_metrics)
                    cls._batch.draw(shader)

        gpu.matrix.load_matrix(original_mvp_mat)
