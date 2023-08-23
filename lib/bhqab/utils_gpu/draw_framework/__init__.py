from __future__ import annotations

if "bpy" in locals():
    from importlib import reload

    reload(_common)
    reload(_smaa)
    reload(_fxaa)
else:
    from . import _common

import bpy
from bpy.types import (
    AddonPreferences,
    Context,
    UILayout,
)
from bpy.props import (
    EnumProperty,
)

import gpu
from gpu.types import (
    GPUShader,
    GPUShaderCreateInfo,
    GPUStageInterfaceInfo,
    GPUTexture,
)


__all__ = (
    "BatchPreset",
    "Mode",
    "AAPreset",
    "get_depth_map",
    "get_viewport_metrics",
    "FrameBufferFramework",
    "DrawFramework",
    "AABase",
    "SMAA",
    "FXAA",
)

BatchPreset = _common.BatchPreset

Mode = _common.Mode
AAPreset = _common.AAPreset
AABase = _common.AABase

get_depth_map = _common.get_depth_map
get_viewport_metrics = _common.get_viewport_metrics

FrameBufferFramework = _common.FrameBufferFramework


class DrawFramework:
    """
    Фреймворк для роботи з буферами кадру для спрощення роботи з декількома вікнами програми і усіма наявними в них
    переглядачами. Суть роботи в тому аби створити і оновлювати буфери кадру для кожного переглядача, враховуючи
    необхідні додаткові буфери для згладжування а також самі методи згладжування.

    :ivar str aa_method: Назва необхідного методу згладжування. Використовується для встановлення необхідного методу.
    :aa AABase aa: Екземпляр класу методу згладжування, використовується для встановлення налаштувань поточного методу.
    """

    __slots__ = (
        "_aa_instance",
        "_fb_frameworks",
    )

    __aa_methods_registry__: set[AABase] = set()

    _aa_instance: None | AABase
    _fb_frameworks: tuple[FrameBufferFramework]

    __shader_2d_image__: None | GPUShader = None

    @classmethod
    @property
    def shader_2d_image(cls) -> None | GPUShader:
        if not cls.__shader_2d_image__ and not bpy.app.background:
            info = GPUShaderCreateInfo()
            info.vertex_in(0, 'VEC2', "P")
            info.vertex_in(1, 'VEC2', "UV")

            vs_out = GPUStageInterfaceInfo("image")
            vs_out.smooth('VEC2', "v_UV")
            info.vertex_out(vs_out)
            info.push_constant('MAT4', "ModelViewProjectionMatrix")
            info.sampler(0, 'FLOAT_2D', "u_Image")
            info.fragment_out(0, 'VEC4', "f_Color")
            info.vertex_source(
                """
                void main() {
                    v_UV = UV;
                    gl_Position = ModelViewProjectionMatrix * vec4(P, 0.0, 1.0);
                }
                """
            )
            info.fragment_source("void main() { f_Color = texture(u_Image, v_UV); }")

            cls.__shader_2d_image__ = gpu.shader.create_from_info(info)
        return cls.__shader_2d_image__

    @classmethod
    @property
    def prop_aa_method(cls) -> EnumProperty:
        """
        :return: Властивість для використання в користувацьких налаштуваннях.
        :rtype: `EnumProperty`_
        """
        return EnumProperty(
            items=tuple(((_.name, _.name, _.description) for _ in cls.__aa_methods_registry__)),
            options={'HIDDEN', 'SKIP_SAVE'},
            translation_context='BHQAB_Preferences',
            name="AA Method",
            description="Anti-aliasing method to be used",
        )

    @classmethod
    def register_aa_method(cls, method_class: AABase):
        """
        Метод для реєстрації методу згладжування.

        :param method_class: Клас методу згладжування.
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
        Надає фреймворк за індексом.

        :param index: Індекс необхідного фреймворку, за замовчуванням 0.
        :type index: int, опційно
        :return: Фреймворк.
        :rtype: FrameBufferFramework
        """
        return self._fb_frameworks[index]

    def modal_eval(
            self,
            context: Context,
            *,
            color_format: str = "",
            depth_format: str = "",
            percentage: int = 100):
        """
        Оновлює буфери кадру відповідно до розміру переглядачів і їх наявності. Повинен бути викликаний в модальній
        частині оператора.

        :param context: Поточний контекст виконання.
        :type context: `Context`_
        :param color_format: Формат текстури кольору або пустий рядок, якщо вона не потрібна, за замовчуванням ''.
        :type color_format: str, див. наявні опції `GPUTexture`_, опційно.
        :param depth_format: Формат текстури глибини або пустий рядок, якщо вона не потрібна, за замовчуванням ''.
        :type depth_format: str, див. наявні опції `GPUTexture`_, опційно.
        :param percentage: Відсоток від розміру переглядача, за замовчуванням 100.
        :type percentage: int, опційно
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
            _common.FrameBufferFramework(
                area_type=area_type,
                region_type=region_type
            )
            for _ in range(max(1, num))
        )

        self._aa_instance = None

    def draw(self, *, texture: GPUTexture) -> None:
        """
        Відображення текстури відповідно до поточних налаштувань згладжування. Якщо обрано метод згладжування
        :attr:`AAPreset.NONE` буде викликано просте відображення текстури, інакше - текстуру буде передано до поточного
        методу згладжування і виконано відображення з його допомоги.

        :param texture: Текстура.
        :type texture: `GPUTexture`_
        """
        cls = self.__class__

        mvp_restore = gpu.matrix.get_projection_matrix() @ gpu.matrix.get_model_view_matrix()

        if (self._aa_instance is None) or (self._aa_instance._preset is AAPreset.NONE):
            with gpu.matrix.push_pop():
                AABase._setup_gpu_state(alpha_premult=True)

                shader = cls.shader_2d_image
                shader.uniform_sampler("u_Image", texture)
                BatchPreset.ndc_rectangle_tris_P_UV.draw(shader)
        else:
            self._aa_instance.draw(texture=texture)

        gpu.matrix.load_matrix(mvp_restore)

    @classmethod
    def ui_preferences(cls, layout: UILayout, *, pref: AddonPreferences, **kwargs):
        """
        Метод для відображення налаштувань згладжування в користувацьких налаштуваннях. Можна визначити які анотації
        класу налаштувань зберігають необхідні опції надаючи ключові слова за шаблоном:
        ``attr_[*, aa_method, smaa_preset, fxaa_preset, fxaa_value]``

        :param layout: Поточний інтерфейс користувача.
        :type layout: `UILayout`_
        :param pref: Екземпляр користувацьких налаштувань.
        :type pref: `AddonPreferences`_
        """
        attr_aa_method = kwargs.get("attr_aa_method", "aa_method")

        row = layout.row(align=True)
        row.prop(pref, attr_aa_method, expand=True)

        aa_method = getattr(pref, attr_aa_method)
        for cls in cls.__aa_methods_registry__:
            if aa_method == cls.__name__:
                cls.ui_preferences(layout, pref=pref, **kwargs)

    def update_from_preferences(self, *, pref: AddonPreferences, **kwargs):
        """
        Метод оновлення властивостей з користувацьких налаштувань. Можна визначити які анотації класу налаштувань
        зберігають необхідні опції надаючи ключові слова за шаблоном:
        ``attr_[*, aa_method, smaa_preset, fxaa_preset, fxaa_value]``

        :param pref: Екземпляр користувацьких налаштувань.
        :type pref: `AddonPreferences`_
        """
        cls = self.__class__
        attr_aa_method = kwargs.get("attr_aa_method", "aa_method")
        aa_method = getattr(pref, attr_aa_method)

        self.aa_method = aa_method

        for cls in cls.__aa_methods_registry__:
            if aa_method == cls.__name__:
                self._aa_instance.update_from_preferences(pref=pref, **kwargs)


from . import _smaa
from . import _fxaa

SMAA = _smaa.SMAA
FXAA = _fxaa.FXAA

DrawFramework.register_aa_method(FXAA)
DrawFramework.register_aa_method(SMAA)
