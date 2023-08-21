from __future__ import annotations

import os
from typing import (
    Generator,
    Iterable,
)
import random
import string
import importlib

import bpy
from bpy.types import (
    Context,
    Event,
    ID,
    Menu,
    Operator,
    PropertyGroup,
    STATUSBAR_HT_header,
    UILayout,
    WindowManager,
)

from bpy.props import (
    BoolProperty,
    CollectionProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
)
from mathutils import Vector
import blf
import rna_keymap_ui
from bl_ui import space_statusbar
# ifdef DEBUG
from bpy_extras.io_utils import ExportHelper
# endif // !DEBUG

__all__ = (
    "supported_image_extensions",
    "eval_unique_name",
    "draw_wrapped_text",
    "developer_extras_poll",
    "template_developer_extras_warning",
    "template_tool_keymap",
    "template_input_info_kmi_from_type",
    "progress",
    "copy_default_presets_from",
    "template_preset",
    "template_disclosure_enum_flag",
)

_IMAGE_EXTENSIONS = {
    ".bmp",
    ".sgi", ".rgb", ".bw",
    ".png",
    ".jpg", ".jpeg",
    ".jp2", ".j2c",
    ".tga",
    ".cin", ".dpx",
    ".exr",
    ".hdr",
    ".tif", ".tiff",
    ".psd",
}


def supported_image_extensions() -> set[str]:
    """
    Набір розширень файлів зображень які підтримує Blender.

    :return: Набір розширень нижнього реєстру:

        `.bmp`,
        `.sgi`, `.rgb`, `.bw`,
        `.png`,
        `.jpg`, `.jpeg`,
        `.jp2`, `.j2c`,
        `.tga`,
        `.cin`, `.dpx`,
        `.exr`,
        `.hdr`,
        `.tif`, `.tiff`,
        `.psd`

    :rtype: set[str]

    .. seealso::

        Дані походять з:

        `Supported Image Extensions`_

    """
    return _IMAGE_EXTENSIONS


def eval_unique_name(*, arr: Iterable, prefix: str = "", suffix: str = "") -> str:
    """
    Evaluates a random name that will be unique in this array. It can be used to create a random unique name with the
    specified ``suffix`` and ``prefix`` for this array. It can be used with ``bpy.data.[...].new (name)`` or to register
    temporary properties of data blocks, etc.

    :param arr: An array of objects for which a unique new name must be generated
    :type arr: Iterable
    :param prefix: Name prefix, defaults to "". If the 'bpy.ops' module acts as an array, then the ``prefix`` acts as a
        'bpy.ops.[prefix]' (and the result will be the 'id_name' of the new operator in the format
        [``prefix``].[random_unique_part][``suffix``])
    :type prefix: str, опційно
    :param suffix: Name suffix, defaults to ""
    :type suffix: str, опційно
    :return: Generated unique name
    :rtype: str
    """
    if arr is bpy.ops:
        ret = prefix + '.' + str().join(random.sample(string.ascii_lowercase, k=10)) + suffix
        if isinstance(getattr(getattr(arr, ret, None), "bl_idname", None), str):
            return eval_unique_name(arr=arr, prefix=prefix, suffix=suffix)
        return ret
    else:
        ret = prefix + str().join(random.sample(string.ascii_letters, k=5)) + suffix
        if hasattr(arr, ret) or (isinstance(arr, Iterable) and ret in arr):
            return eval_unique_name(arr=arr, prefix=prefix, suffix=suffix)
        return ret


def eval_text_pixel_dimensions(*, fontid: int = 0, text: str = "") -> Vector:
    """
    Обчислює розмір тексту в пікселях з поточними налаштуваннями модуля ``blf``.

    :param fontid: Ідентифікатор шрифту, за замовчуванням ``0``.
    :type fontid: int, опційно
    :param text: Текст для обробки, за замовчуванням - пустий рядок.
    :type text: str, опційно
    :return: Висота і ширина тексту.
    :rtype: `mathutils.Vector`_
    """
    ret = Vector((0.0, 0.0))
    if not text:
        return ret

    is_single_char = bool(len(text) == 1)
    SINGLE_CHARACTER_SAMPLES = 100
    if is_single_char:
        text *= SINGLE_CHARACTER_SAMPLES

    ret.x, ret.y = blf.dimensions(fontid, text)

    if is_single_char:
        ret.x /= SINGLE_CHARACTER_SAMPLES

    return ret


def draw_wrapped_text(context: Context, layout: UILayout, *, text: str) -> None:
    """
    Відображує текстовий блок, з автоматичний перенесенням рядків відповідно до ширини поточного регіону.

    :param context: Поточний контекст.
    :type context: `Context`_
    :param layout: Поточний користувацький інтерфейс.
    :type layout: `UILayout`_
    :param text: Текст для відображення.
    :type text: str
    """
    col = layout.column(align=True)

    if context.region.type == 'WINDOW':
        win_padding = 25
    elif context.region.type == 'UI':
        win_padding = 52
    else:
        win_padding = 52

    wrap_width = context.region.width - win_padding
    space_width = eval_text_pixel_dimensions(text=' ').x

    for line in text.split('\n'):
        num_characters = len(line)

        if not num_characters:
            col.separator()
            continue

        line_words = list((_, eval_text_pixel_dimensions(text=_).x) for _ in line.split(' '))
        num_line_words = len(line_words)
        line_words_last = num_line_words - 1

        sublines = [""]
        subline_width = 0.0

        for i in range(num_line_words):
            word, word_width = line_words[i]

            sublines[-1] += word
            subline_width += word_width

            next_word_width = 0.0
            if i < line_words_last:
                next_word_width = line_words[i + 1][1]

                sublines[-1] += ' '
                subline_width += space_width

            if subline_width + next_word_width > wrap_width:
                subline_width = 0.0
                if i < line_words_last:
                    sublines.append("")  # Add new subline.

        for subline in sublines:
            col.label(text=subline)


def developer_extras_poll(context: Context) -> bool:
    """
    Чи потрібно відобразити секцію користувацького інтерфейсу, яка призначена для розробки або налагодження.

    :param context: Поточний контекст.
    :type context: `Context`_
    :return: Позитивне значення означає що так, потрібно.
    :rtype: bool
    """
    return context.preferences.view.show_developer_ui


def template_developer_extras_warning(context: Context, layout: UILayout) -> None:
    """
    Шаблон для відображення попередження про те що ця секція користувацького інтерфейсу призначена виключно для розробки
    та налагодження.

    :param context: Поточний контекст.
    :type context: `Context`_
    :param layout: Поточний користувацький інтерфейс.
    :type layout: `UILayout`_
    """
    if developer_extras_poll(context):
        col = layout.column(align=True)
        col.label(text="Warning", icon='INFO')
        text = "This section is intended for developers. You see it because " \
            "you have an active \"Developers Extras\" option in the Blender " \
            "user preferences."
        draw_wrapped_text(context, col, text=text)
        col.prop(context.preferences.view, "show_developer_ui")


def template_tool_keymap(context: Context, layout: UILayout, *, km_name: str):
    """
    Шаблон для відображення набору клавіатурних скорочень інструмента.

    :param context: Поточний контекст.
    :type context: `Context`_
    :param layout: Поточний користувацький інтерфейс.
    :type layout: `UILayout`_
    :param km_name: Назва набору клавіатурних скорочень, наприклад "3D View Tool: Edit Mesh, Path Tool"
    :type km_name: str
    """

    kc = context.window_manager.keyconfigs.user
    km = kc.keymaps.get(km_name)
    if km:
        rna_keymap_ui.draw_km([], kc, km, None, layout, 0)
    else:
        layout.label(text=f"Not found keymap: \"{km_name}\"", icon='ERROR')


_KMI_ICONS: dict[str, str] = dict()


def _eval_kmi_icons():
    kmi_identifiers = [_.identifier for _ in Event.bl_rna.properties["type"].enum_items]
    icons = UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items.keys()

    for kmi_type in kmi_identifiers:
        if f'EVENT_{kmi_type}' in icons:
            _KMI_ICONS[kmi_type] = f'EVENT_{kmi_type}'

    _KMI_ICONS.update(
        {
            'LEFTMOUSE': 'MOUSE_LMB',
            'RIGHTMOUSE': 'MOUSE_RMB',
            'MIDDLEMOUSE': 'MOUSE_MMB',

            'LEFT_CTRL': 'EVENT_CTRL',
            'RIGHT_CTRL': 'EVENT_CTRL',

            'LEFT_SHIFT': 'EVENT_SHIFT',
            'RIGHT_SHIFT': 'EVENT_SHIFT',

            'LEFT_ALT': 'EVENT_ALT',
            'RIGHT_ALT': 'EVENT_ALT',

            'SPACE': 'EVENT_SPACEKEY',

            'RET': 'EVENT_RETURN',

            'PAGE_UP': 'EVENT_PAGEUP',
            'PAGE_DOWN': 'EVENT_PAGEDOWN',

            'OSKEY': 'EVENT_OS',
        }
    )


def template_input_info_kmi_from_type(layout: UILayout, *, label: str, event_types: set[str] = set()) -> None:
    """
    Метод відображення іконок можливих клавіатурних скорочень.

    :param layout: Поточний користувацький інтерфейс.
    :type layout: `UILayout`_
    :param label: Заголовок для відображення.
    :type label: str
    :param event_types: Набір типів подій (see `Event.type`_), за замовчуванням set().
    :type event_types: set[str], опційно
    """
    if not _KMI_ICONS:
        _eval_kmi_icons()

    icons = []
    for ev_type in event_types:
        if ev_type in _KMI_ICONS.keys():
            icons.append(_KMI_ICONS[ev_type])

    if len(icons) == 1:
        layout.label(text=label, icon=icons[0])
    elif len(icons) > 1:
        row = layout.row(align=True)
        for i, icon in enumerate(icons):
            if i < len(icons) - 1:
                row.label(text="", icon=icon)
            else:
                row.label(text=label, icon=icon)


def _update_statusbar():
    bpy.context.workspace.status_text_set(text=None)


class _progress_meta(type):
    @property
    def PROGRESS_BAR_UI_UNITS(cls):
        return cls._PROGRESS_BAR_UI_UNITS

    @PROGRESS_BAR_UI_UNITS.setter
    def PROGRESS_BAR_UI_UNITS(cls, value):
        cls._PROGRESS_BAR_UI_UNITS = max(cls._PROGRESS_BAR_UI_UNITS_MIN, min(value, cls._PROGRESS_BAR_UI_UNITS_MAX))


class progress(metaclass=_progress_meta):
    """
    Клас для відображення індикаторів прогресу в рядку статусу.

    :cvar int PROGRESS_BAR_UI_UNITS: Кількість одиниць користувацького інтерфейсу [4...12] для одного індикатора
        прогресу (ширина заголовку і значка не враховується). За замовчуванням - 6 (тільки для читання).

    .. versionadded:: 3.3
    """

    _PROGRESS_BAR_UI_UNITS = 6
    _PROGRESS_BAR_UI_UNITS_MIN = 4
    _PROGRESS_BAR_UI_UNITS_MAX = 12

    _is_drawn = False
    _attrname = ""

    class ProgressPropertyItem(PropertyGroup):
        """
        Індикатор прогресу.
        """

        def _common_value_update(self, _context):
            _update_statusbar()

        valid: BoolProperty(  # Internal valid markup, not for docs
            default=True,
            update=_common_value_update,
        )

        #: Кількість кроків виконання операції.
        #:
        #: .. versionadded:: 3.3
        num_steps: IntProperty(
            min=1,
            default=1,
            subtype='UNSIGNED',
            options={'HIDDEN'},
            update=_common_value_update,
        )

        #: Поточний крок виконання операції.
        #:
        #: .. versionadded:: 3.3
        step: IntProperty(
            min=0,
            default=0,
            subtype='UNSIGNED',
            options={'HIDDEN'},
            update=_common_value_update,
        )

        def _get_progress(self):
            return (self.step / self.num_steps) * 100

        def _set_progress(self, _value):
            pass

        #: Оцінений прогрес виконання, лише для зчитування.
        #:
        #: .. versionadded:: 3.3
        value: FloatProperty(
            min=0.0,
            max=100.0,
            precision=1,
            get=_get_progress,
            # set=_set_progress,
            subtype='PERCENTAGE',
            options={'HIDDEN'},
        )

        #: Значок для відображення.
        #:
        #: .. versionadded:: 3.3
        icon: StringProperty(
            default='NONE',
            maxlen=64,
            options={'HIDDEN'},
            update=_common_value_update,
        )

        #: Індекс значка попереднього перегляду для відображення.
        #:
        #: .. versionadded:: 3.3
        icon_value: IntProperty(
            min=0,
            default=0,
            subtype='UNSIGNED',
            options={'HIDDEN'},
            update=_common_value_update,
        )

        #: Заголовок.
        #:
        #: .. versionadded:: 3.3
        label: StringProperty(
            default="Progress",
            options={'HIDDEN'},
            update=_common_value_update,
        )

        #: Чи відображувати кнопку скасування операції.
        #:
        #: .. versionadded:: 3.3
        cancellable: BoolProperty(
            default=False,
            options={'HIDDEN'},
            update=_common_value_update,
        )

    def _func_draw_progress(self, context: Context):
        layout: UILayout = self.layout

        layout.use_property_split = True
        layout.use_property_decorate = False

        layout.template_input_status()
        layout.separator_spacer()
        layout.template_reports_banner()

        if hasattr(WindowManager, progress._attrname):
            layout.separator_spacer()
            for item in progress.valid_progress_items():
                row = layout.row(align=True)
                row.label(text=item.label, icon=item.icon, icon_value=item.icon_value)

                srow = row.row(align=True)
                srow.ui_units_x = progress.PROGRESS_BAR_UI_UNITS
                srow.prop(item, "value", text="")

                if item.cancellable:
                    row.prop(item, "valid", text="", icon='X', toggle=True, invert_checkbox=True)

        layout.separator_spacer()

        row = layout.row()
        row.alignment = 'RIGHT'

        row.label(text=context.screen.statusbar_info(), translate=False)

    @classmethod
    def progress_items(cls):
        """
        :return: Всі індикатори прогресу.
        :rtype: Масив з :class:`ProgressPropertyItem`
        """
        return getattr(bpy.context.window_manager, cls._attrname)

    @classmethod
    def valid_progress_items(cls) -> Generator[ProgressPropertyItem]:
        """
        Генератор що містить лише незавершені індикатори прогресу.

        :yield: Незавершений прогрес.
        :rtype: Generator[:class:`ProgressPropertyItem`]
        """
        return (_ for _ in cls.progress_items() if _.valid)

    @classmethod
    def invoke(cls) -> ProgressPropertyItem:
        """
        Створює новий індикатор прогресу.

        :return: Індикатор прогресу.
        :rtype: :class:`ProgressPropertyItem`
        """
        if not cls._is_drawn:
            bpy.utils.register_class(progress.ProgressPropertyItem)
            cls._attrname = eval_unique_name(arr=WindowManager, prefix="bhq_", suffix="_progress")

            setattr(
                WindowManager,
                cls._attrname,
                CollectionProperty(type=progress.ProgressPropertyItem)
            )
            STATUSBAR_HT_header.draw = cls._func_draw_progress
            _update_statusbar()

        cls._is_drawn = True
        return cls.progress_items().add()

    @classmethod
    def complete(cls, *, item: ProgressPropertyItem):
        """
        Позначає індикатор прогресу як завершений. Якщо він був останнім то буде викликано метод класу
        :func:`progress.release_all`.

        :param item: Індикатор прогресу що відображає перебіг виконання операції яку вже завершено.
        :type item: :class:`ProgressPropertyItem`
        """
        assert (isinstance(item, progress.ProgressPropertyItem))

        item.valid = False

        for _ in cls.valid_progress_items():
            return
        cls.release_all()

    @classmethod
    def release_all(cls):
        """
        Видаляє всі індикатори прогресу і відновлює стандартне відображення рядку статусу.
        """
        if not cls._is_drawn:
            return

        assert (cls._attrname)
        delattr(WindowManager, cls._attrname)
        bpy.utils.unregister_class(progress.ProgressPropertyItem)

        importlib.reload(space_statusbar)
        STATUSBAR_HT_header.draw = space_statusbar.STATUSBAR_HT_header.draw
        _update_statusbar()

        cls._is_drawn = False


def copy_default_presets_from(*, src_root: str):
    """
    Створює копії файлів шаблонів з директорії аддону до директорії де Blender зберігає шаблони.

    :param src_root: Директорія що містить файли шаблонів.
    :type src_root: str
    """
    for root, _dir, files in os.walk(src_root):
        for filename in files:
            rel_dir = os.path.relpath(root, src_root)
            src_fp = os.path.join(root, filename)

            tar_dir = bpy.utils.user_resource('SCRIPTS', path=os.path.join("presets", rel_dir), create=True)
            if not tar_dir:
                print("Failed to create presets path")
                return

            tar_fp = os.path.join(tar_dir, filename)

            with open(src_fp, 'r', encoding="utf-8") as src_file, open(tar_fp, 'w', encoding="utf-8") as tar_file:
                tar_file.write(src_file.read())


def template_preset(layout: UILayout, *, menu: Menu, operator: str) -> None:
    """
    Метод відображення шаблонів в користувацькому інтерфейсі.

    :param layout: Поточний користувацький інтерфейс.
    :type layout: `UILayout`_
    :param menu: Клас меню що буде використано для відображення списку шаблонів.
    :type menu: 'Menu'_
    :param operator: ``bl_idname`` оператора для створення і видалення шаблонів.
    :type operator: str
    """
    row = layout.row(align=True)
    row.use_property_split = False

    row.menu(menu=menu.__name__, text=menu.bl_label)
    row.operator(operator=operator, text="", icon='ADD')
    row.operator(operator=operator, text="", icon='REMOVE').remove_active = True


def template_disclosure_enum_flag(layout: UILayout, *, item: ID, prop_enum_flag: str, flag: str) -> bool:
    """
    Відображення секцій користувацького інтерфейсу без створення додаткових панелей. Загалом, для використання в
    вікні користувацьких налаштувань, оскільки інші панелі не є унікальними - секцію буде згорнуто або розгорнуто всюди.

    :param layout: Поточний користувацький інтерфейс.
    :type layout: `UILayout`_
    :param item: екземпляр класу що містить властивість ``prop_enum_flag``.
    :type item: `ID`_
    :param prop_enum_flag: Назва анотації класу що містить набір секцій (`EnumProperty`_ `з (options={'ENUM_FLAG'})`).
    :type prop_enum_flag: str
    :param flag: Прапор необхідної секції.
    :type flag: str
    :return: Позитивне значення означає що секцію треба відображувати.
    :rtype: bool
    """
    row = layout.row(align=True)
    row.use_property_split = False
    row.emboss = 'NONE_OR_STATUS'
    row.alignment = 'LEFT'
    icon = 'DISCLOSURE_TRI_RIGHT'

    ret = False
    if flag in getattr(item, prop_enum_flag):
        icon = 'DISCLOSURE_TRI_DOWN'
        ret = True

    icon_value = UILayout.enum_item_icon(item, prop_enum_flag, flag)
    if icon_value:
        row.label(icon_value=icon_value)
    row.prop_enum(item, prop_enum_flag, flag, icon=icon)

    return ret
