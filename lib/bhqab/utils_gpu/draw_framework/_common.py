from __future__ import annotations

from typing import Literal
from enum import (
    auto,
    Enum,
    IntEnum,
)

if "bpy" in locals():
    from importlib import reload

    reload(utils_wm)
else:
    from ... import utils_wm

import bpy
from bpy.types import (
    AddonPreferences,
    Context,
    Region,
    UILayout,
)

from mathutils import (
    Vector,
    Matrix,
)

import gpu
from gpu.types import (
    GPUBatch,
    GPUBatch,
    GPUFrameBuffer,
    GPUIndexBuf,
    GPUOffScreen,
    GPUTexture,
    GPUVertBuf,
    GPUVertFormat,
)
from gpu_extras.batch import batch_for_shader

__all__ = (
    "FrameBufferFramework",
    "get_depth_map",
    "get_viewport_metrics",
    "iter_area_regions",
    "iter_area_spaces",
    "iter_areas",
)


def get_viewport_metrics() -> Vector:
    """
    Одиниці виміру поточного переглядача у вигляді вектора.

    :return: x = ``1.0 / ширину``, y = ``1.0 / висоту``, z = ``ширина``, w = ``висота``
    :rtype: `Vector`_
    """
    viewport = gpu.state.viewport_get()
    w, h = viewport[2], viewport[3]
    return Vector((1.0 / w, 1.0 / h, w, h))


def get_depth_map(*, depth_format: str = 'DEPTH_COMPONENT32F') -> GPUTexture:
    """
    Текстура глибини в поточному буфері кадру.

    :return: Текстура типу ``DEPTH_COMPONENT32F`` що має розмір переглядача.
    :rtype: `GPUTexture`_
    """
    fb = gpu.state.active_framebuffer_get()
    return gpu.types.GPUTexture(
        gpu.state.viewport_get()[2:],
        data=fb.read_depth(*fb.viewport_get()), format=depth_format
    )


class Mode(Enum):
    """
    Режим роботи фреймворку.
    """

    #: Робота з усіма регіонами переглядачів.
    REGION = auto()
    #: Робота з текстурою.
    TEXTURE = auto()


class FrameBufferFramework:
    __slots__ = (
        "_mode",
        "_region_framebuffer",
        "_area_type",
        "_region_type",
        "_texture_offscreen_data",
    )

    _mode: Mode

    # Mode.REGION
    _region_framebuffer: dict[Region, tuple[GPUFrameBuffer, None | GPUTexture, None | GPUTexture]]
    _area_type: str
    _region_type: str

    # Mode.TEXTURE
    _texture_offscreen_data: None | GPUOffScreen

    def __init__(self, *, mode=Mode.REGION, area_type='VIEW_3D', region_type='WINDOW'):
        self._mode = mode

        match self._mode:
            case Mode.REGION:
                self._region_framebuffer = dict()
                self._area_type = area_type
                self._region_type = region_type

            case Mode.TEXTURE:
                self._texture_offscreen_data = None

    def modal_eval(
            self,
            context: Context,
            *,
            texture_width: int = 0,
            texture_height: int = 0,
            color_format: str = "",
            depth_format: str = "",
            percentage: int = 100
    ):
        scale = max(10, min(400, percentage)) / 100

        match self._mode:
            case Mode.REGION:
                existing_regions = set(
                    region for region
                    in utils_wm.iter_regions(context, area_type=self._area_type, region_type=self._region_type)
                )

                invalid_regions = set(self._region_framebuffer.keys())
                invalid_regions.difference_update(existing_regions)
                for region in invalid_regions:
                    del self._region_framebuffer[region]

                for region in existing_regions:
                    do_update = True
                    do_update_depth_texture = True

                    width = int(region.width * scale)
                    height = int(region.height * scale)

                    if region in self._region_framebuffer:
                        framebuffer, texture, depth_texture = self._region_framebuffer[region]

                        do_update = not (
                            (
                                color_format and texture and (
                                    texture.width == width
                                    and texture.height == height
                                    and texture.format == color_format
                                )
                            )
                        )

                        do_update_depth_texture = not (
                            (
                                depth_format and depth_texture and (
                                    depth_texture.width == width
                                    and depth_texture.height == height
                                    and depth_texture.format == depth_format
                                )
                            )
                        )

                    if do_update or do_update_depth_texture:
                        if do_update:
                            if color_format:
                                texture = GPUTexture(size=(width, height), format=color_format)
                            else:
                                texture = None

                        if do_update_depth_texture:
                            if depth_format:
                                depth_texture = GPUTexture(size=(width, height), format=depth_format)
                            else:
                                depth_texture = None

                        framebuffer = GPUFrameBuffer(color_slots=texture, depth_slot=depth_texture)
                        self._region_framebuffer[region] = (framebuffer, texture, depth_texture)

            case Mode.TEXTURE:
                assert (color_format)

                offscreen = self._texture_offscreen_data

                do_update = True

                required_width = int(texture_width * scale)
                required_height = int(texture_height * scale)

                if offscreen:
                    width = int(offscreen.width * scale)
                    height = int(offscreen.height * scale)

                    do_update = not (
                        width == required_width
                        and height == required_height
                        and offscreen.format == color_format
                    )

                if do_update:
                    self._texture_offscreen_data = GPUOffScreen(
                        width=required_width,
                        height=required_height,
                        format=color_format
                    )

    def get(
        self,
        *,
        region: None | Region = None
    ) -> None | tuple[GPUFrameBuffer, None | GPUTexture, None | GPUTexture] | GPUOffScreen:
        match self._mode:
            case Mode.REGION:
                if not region:
                    region = bpy.context.region
                if region in self._region_framebuffer:
                    return self._region_framebuffer[region][0]
                return None
            case Mode.TEXTURE:
                return self._texture_offscreen_data

    def get_color_texture(self, *, region: None | Region = None) -> None | GPUTexture:
        match self._mode:
            case Mode.REGION:
                if not region:
                    region = bpy.context.region
                if region in self._region_framebuffer:
                    return self._region_framebuffer[region][1]
                return None
            case Mode.TEXTURE:
                return self._texture_offscreen_data.texture_color

    def get_depth_texture(self, *, region: None | Region = None) -> None | GPUTexture:
        match self._mode:
            case Mode.REGION:
                if not region:
                    region = bpy.context.region
                if region in self._region_framebuffer:
                    return self._region_framebuffer[region][2]
                return None
            case Mode.TEXTURE:
                return None


class BatchPreset:
    """
    Заздалегідь заготовлені групи вершин. Всі змінні класу можна використовувати лише для зчитування.
    """

    _unit_rectangle_tris_P_vbo: None | GPUVertBuf = None
    _unit_rectangle_tris_P_ibo: None | GPUIndexBuf = None

    _ndc_rectangle_tris_P_UV_vbo: None | GPUVertBuf = None
    _ndc_rectangle_tris_P_UV_ibo: None | GPUIndexBuf = None

    @classmethod
    @property
    def unit_rectangle_tris_P(cls) -> GPUBatch:
        """
        :return: Квадрат типу 'TRIS' з центром на початку координат і стороною 1 одиницю виміру.
        :rtype: `GPUBatch`_
        """
        if not cls._unit_rectangle_tris_P_vbo or not cls._unit_rectangle_tris_P_ibo:
            cls._update_unit_rectangle_tris_P_buffer_objects()
        # Створюємо новий кожного разу, оскільки:
        # ERROR (gpu.debug):  : GL_INVALID_OPERATION error generated. VAO names must be generated with glGenVertexArrays
        # before they can be bound or used.
        return GPUBatch(type='TRIS', buf=cls._unit_rectangle_tris_P_vbo, elem=cls._unit_rectangle_tris_P_ibo)

    @classmethod
    def _update_unit_rectangle_tris_P_buffer_objects(cls):
        vert_fmt = GPUVertFormat()
        vert_fmt.attr_add(id="P", comp_type='F32', len=2, fetch_mode='FLOAT')

        vbo = GPUVertBuf(format=vert_fmt, len=4)
        vbo.attr_fill(id="P", data=((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0)))

        ibo = GPUIndexBuf(type='TRIS', seq=((0, 1, 2), (0, 2, 3)))

        cls._unit_rectangle_tris_P_vbo = vbo
        cls._unit_rectangle_tris_P_ibo = ibo

    @classmethod
    @property
    def ndc_rectangle_tris_P_UV(cls) -> GPUBatch:
        """
        :return: Квадрат типу 'TRIS' зі стороною 2 одиниці виміру для відображення в нормалізованих координатах.Містить
            атрибути "P" (-1.0 ... 1.0) і "UV" (0.0 ... 1.0).
        :rtype: `GPUBatch`_
        """
        if not cls._ndc_rectangle_tris_P_UV_vbo or not cls._ndc_rectangle_tris_P_UV_ibo:
            cls._update_ndc_rectangle_tris_P_UV_buffer_objects()
        # Створюємо новий кожного разу, оскільки:
        # ERROR (gpu.debug):  : GL_INVALID_OPERATION error generated. VAO names must be generated with glGenVertexArrays
        # before they can be bound or used.
        return GPUBatch(type='TRIS', buf=cls._ndc_rectangle_tris_P_UV_vbo, elem=cls._ndc_rectangle_tris_P_UV_ibo)

    @classmethod
    def _update_ndc_rectangle_tris_P_UV_buffer_objects(cls):
        vert_fmt = GPUVertFormat()
        vert_fmt.attr_add(id="P", comp_type='F32', len=2, fetch_mode='FLOAT')
        vert_fmt.attr_add(id="UV", comp_type='F32', len=2, fetch_mode='FLOAT')

        vbo = GPUVertBuf(format=vert_fmt, len=4)
        vbo.attr_fill(id="P", data=((-1.0, -1.0), (-1.0, 1.0), (1.0, 1.0), (1.0, -1.0))),
        vbo.attr_fill(id="UV", data=((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0))),

        ibo = GPUIndexBuf(type='TRIS', seq=((0, 1, 2), (0, 2, 3)))

        cls._ndc_rectangle_tris_P_UV_vbo = vbo
        cls._ndc_rectangle_tris_P_UV_ibo = ibo


class AAPreset(IntEnum):
    """
    Перелік шаблонів згладжування.
    """

    #: Без згладжування.
    NONE = auto()
    #: Низький.
    LOW = auto()
    #: Середній.
    MEDIUM = auto()
    #: Високий.
    HIGH = auto()
    #: Найвищий.
    ULTRA = auto()


class AABase(object):
    """
    Базовий клас для методів згладжування.

    :cvar str name: Назва методу згладжування, відповідає назві дочірнього класу, лише для зчитування.
    :cvar str description: Опис методу згладжування.

    :ivar str preset: Поточний шаблон налаштувань.
    """
    __slots__ = (
        "_preset",
        "_preset_0",
    )
    _preset: AAPreset
    _preset_0: AAPreset

    description: str = ""

    def __init__(self, *, area_type='VIEW_3D', region_type='WINDOW'):
        self._preset = AAPreset.NONE
        self._preset_0 = AAPreset.NONE

    @classmethod
    @property
    def name(cls) -> str:
        return cls.__name__

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

    @staticmethod
    def _setup_gpu_state(alpha_premult: bool = True):
        gpu.matrix.load_matrix(Matrix.Identity(4))
        gpu.matrix.load_projection_matrix(Matrix.Identity(4))
        gpu.state.blend_set('ALPHA_PREMULT' if alpha_premult else 'ALPHA')
        # Не потрібно встановлювати взагалі, https://github.com/BlenderHQ/path_tool/issues/5
        # gpu.state.front_facing_set(False)
        # FRONT | BACK створює ґлітчі під час рендерингу у фоновому режимі.
        # gpu.state.face_culling_set('NONE')
        gpu.state.depth_mask_set(False)
        gpu.state.depth_test_set('ALWAYS')

    def modal_eval(
            self,
            context: Context,
            *,
            texture_width: int = 0,
            texture_height: int = 0,
            color_format: str = "",
            percentage: int = 100
    ):
        """
        Оновлення відповідно до поточного контексту. Необхідно робити виклик в модальному методі оператора.

        :param context: Поточний контекст виконання.
        :type context: `Context`_
        :param texture_width: Ширина текстури, за замовчуванням 0
        :type texture_width: int, опційно
        :param texture_height: Висота текстури, за замовчуванням 0
        :type texture_height: int, опційно
        :param color_format: Формат текстури кольору, за замовчуванням ""
        :type color_format: str, опційно
        :param percentage: Відсоток від розміру переглядача, за замовчуванням 100.
        :type percentage: int, опційно
        """
        pass

    def draw(self, *, texture: GPUTexture) -> None:
        """
        Метод відображення текстури в переглядачі. Перезаписаний метод дочірнього класу повинен починатися з

        .. code-block:: python

            super().draw(texture=texture)

        Відбудеться перевірка того що метод згладжування не викликано для відображення коли обрано опцію
        :attr:`AAPreset.NONE`

        :param texture: Текстура для відображення.
        :type texture: `GPUTexture`_
        """
        assert (AAPreset.NONE != self._preset)

    @staticmethod
    def ui_preferences(layout: UILayout, *, pref: AddonPreferences, **kwargs):
        """
        Відображення користувацьких налаштувань методу згладжування.

        :param layout: Поточний інтерфейс користувача.
        :type layout: `UILayout`_
        :param pref: Екземпляр користувацьких налаштувань.
        :type pref: `AddonPreferences`_
        """
        pass

    def update_from_preferences(self, *, pref: AddonPreferences, **kwargs):
        """
        Оновлення параметрів згладжування з користувацьких налаштувань.

        :param pref: Екземпляр користувацьких налаштувань.
        :type pref: `AddonPreferences`_
        """
        pass
