from __future__ import annotations
from typing import Iterable
import random
import string

import bpy
from bpy.types import (
    Context,
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
import blf
import rna_keymap_ui
from bl_ui import space_statusbar


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
    Blender supported image extensions.
    https://docs.blender.org/manual/en/latest/files/media/image_formats.html

    :return: Tuple of lowercase extensions:

        ``.bmp``,
        ``.sgi``, ``.rgb``, ``.bw``,
        ``.png``,
        ``.jpg``, ``.jpeg``,
        ``.jp2``, ``.j2c``,
        ``.tga``,
        ``.cin``, ``.dpx``,
        ``.exr``,
        ``.hdr``,
        ``.tif``, ``.tiff``,
        ``.psd``

    :return: _description_
    :rtype: set[str]
    """
    return _IMAGE_EXTENSIONS


def eval_unique_name(arr: Iterable, prefix: str = "", suffix: str = "") -> str:
    """
    Evaluates a random name that will be unique in this array. It can be used to create a random unique name with the
    specified suffix and prefix for this array. It can be used with ``bpy.data.[...].new (name)`` or to register
    temporary properties of data blocks, etc.

    :param arr: An array of objects for which a unique new name must be generated
    :type arr: Iterable
    :param prefix: Name prefix, defaults to ""
    :type prefix: str, optional
    :param suffix: Name suffix, defaults to ""
    :type suffix: str, optional
    :return: Generated unique name
    :rtype: str
    """

    ret = prefix + str().join(random.sample(string.ascii_letters, k=5)) + suffix

    if hasattr(arr, ret) or (isinstance(arr, Iterable) and ret in arr):
        return eval_unique_name(arr, prefix, suffix)
    return ret


def _string_width(string: str) -> float:
    if len(string) == 1:
        num_single_ch_samples = 100
        return blf.dimensions(0, string * num_single_ch_samples)[0] / num_single_ch_samples
    return blf.dimensions(0, string)[0]


def draw_wrapped_text(context: Context, layout: UILayout, text: str) -> None:
    """
    Draws a block of text in the given layout, dividing it into lines according to the width of the current region of
    the interface.

    :param context: Current context
    :type context: Context
    :param layout: Current layout
    :type layout: UILayout
    :param text: _description_
    :type text: Text to be wrapped and drawn
    """

    col = layout.column(align=True)

    if context.region.type == 'WINDOW':
        win_padding = 25
    elif context.region.type == 'UI':
        win_padding = 52
    else:
        win_padding = 52

    wrap_width = context.region.width - win_padding
    space_width = _string_width(' ')

    for line in text.split('\n'):
        num_characters = len(line)

        if not num_characters:
            continue

        line_words = list((_, _string_width(_)) for _ in line.split(' '))
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
    A method for determining whether a user interface intended for developers should be displayed.

    :param context: Current context
    :type context: Context
    :return: A positive value means that it should
    :rtype: bool
    """
    return context.preferences.view.show_developer_ui


def template_developer_extras_warning(context: Context, layout: UILayout) -> None:
    """
    Output message in the user interface that this section of the interface
    is visible because the active options in the Blender settings. These
    options are also displayed with the ability to disable them.

    :param context: Current context
    :type context: Context
    :param layout: Current UI layout
    :type layout: UILayout
    """
    if developer_extras_poll(context):
        col = layout.column(align=True)
        col.label(text="Warning", icon='INFO')
        text = "This section is intended for developers. You see it because " \
            "you have an active \"Developers Extras\" option in the Blender " \
            "user preferences."
        draw_wrapped_text(context, col, text)
        col.prop(context.preferences.view, "show_developer_ui")


def template_tool_keymap(context: Context, layout: UILayout, km_name: str):
    """
    Template for tool keymap items.

    :param context: Current context
    :type context: Context
    :param layout: Current UI layout
    :type layout: UILayout
    :param km_name: Tool keymap name. For example, "3D View Tool: Edit Mesh, Path Tool"
    :type km_name: str
    """
    kc = context.window_manager.keyconfigs.user
    km = kc.keymaps.get(km_name)
    if km:
        rna_keymap_ui.draw_km([], kc, km, None, layout, 0)
    else:
        layout.label(text=f"Not found keymap: \"{km_name}\"", icon='ERROR')


_KMI_ICONS: dict[str, str] = dict()


def _eval_kmi_icons() -> None:
    kmi_identifiers = [_.identifier for _ in bpy.types.Event.bl_rna.properties["type"].enum_items]
    icons = bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items.keys()

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


def template_input_info_kmi_from_type(layout: UILayout, label: str, event_types: set[str] = set()) -> None:
    """
    Method for displaying icons of possible keys.

    :param layout: Current UI layout
    :type layout: UILayout
    :param label: Label to be displayed with possible keys icons
    :type label: str
    :param event_types: Set of event types (see `bpy.types.Event.type`_), defaults to set()
    :type event_types: set[str], optional
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
    bpy.context.workspace.status_text_set(None)


class _progress_meta(type):
    @property
    def PROGRESS_BAR_UI_UNITS(cls):
        return cls._PROGRESS_BAR_UI_UNITS

    @PROGRESS_BAR_UI_UNITS.setter
    def PROGRESS_BAR_UI_UNITS(cls, value):
        cls._PROGRESS_BAR_UI_UNITS = max(cls._PROGRESS_BAR_UI_UNITS_MIN, min(value, cls._PROGRESS_BAR_UI_UNITS_MAX))


class progress(metaclass=_progress_meta):
    """A class that implements the initialization and completion of progressbars.
    The module provides the ability to display the progressbar (and even several
    progressbars) in the status bar of the Blender. This technique can be used
    mainly with modal operators that run for a relatively long time and require
    the output of the progress of their work.

    Attributes:
        PROGRESS_BAR_UI_UNITS (int): Number of UI units in range [4...12] used
            for progressbar without text label and icon.
    """

    _PROGRESS_BAR_UI_UNITS = 6
    _PROGRESS_BAR_UI_UNITS_MIN = 4
    _PROGRESS_BAR_UI_UNITS_MAX = 12

    _is_drawn = False
    _attrname = ""

    class ProgressPropertyItem(PropertyGroup):
        """Progress bar item that allows you to dynamically change some display parameters.

        Attributes:
            num_steps (int): Number of progress steps.
            step (int): Current progress step.
            value (float): Evaluated progress value (readonly).
            icon (str): Blender icon to be displayed.
            icon_value (int): Icon id to be displayed.
            label (str): Progressbar text label.
            cancellable (bool): Positive value means that progressbar should draw cancel button.
        """

        def _common_value_update(self, _context):
            _update_statusbar()

        valid: BoolProperty(
            default=True,
            update=_common_value_update,
        )

        num_steps: IntProperty(
            min=1,
            default=1,
            subtype='UNSIGNED',
            options={'HIDDEN'},
            update=_common_value_update,
        )

        step: IntProperty(
            min=0,
            subtype='UNSIGNED',
            options={'HIDDEN'},
            update=_common_value_update,
        )

        def _get_progress(self):
            return (self.step / self.num_steps) * 100

        def _set_progress(self, _value):
            pass

        value: FloatProperty(
            min=0.0,
            max=100.0,
            precision=1,
            get=_get_progress,
            # set=_set_progress,
            subtype='PERCENTAGE',
            options={'HIDDEN'},
        )

        icon: StringProperty(
            default='NONE',
            maxlen=64,
            options={'HIDDEN'},
            update=_common_value_update,
        )

        icon_value: IntProperty(
            min=0,
            default=0,
            subtype='UNSIGNED',
            options={'HIDDEN'},
            update=_common_value_update,
        )

        label: StringProperty(
            default="Progress",
            options={'HIDDEN'},
            update=_common_value_update,
        )

        cancellable: BoolProperty(
            default=False,
            options={'HIDDEN'},
            update=_common_value_update,
        )

    def _func_draw_progress(self, context):
        layout = self.layout

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
        return getattr(bpy.context.window_manager, cls._attrname)

    @classmethod
    def valid_progress_items(cls):
        return (_ for _ in cls.progress_items() if _.valid)

    @classmethod
    def invoke(cls) -> ProgressPropertyItem:
        """
        Invoke new progressbar for each call.

        :return: New initialized progress property item
        :rtype: ProgressPropertyItem
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
    def complete(cls, item: ProgressPropertyItem):
        """
        Removes progressbar from UI. If removed progressbar was the last one, would be called
        :py:func:`progress.release_all` class method.

        :param item: Progress item to be removed
        :type item: ProgressPropertyItem
        """
        assert(isinstance(item, progress.ProgressPropertyItem))

        item.valid = False

        for _ in cls.valid_progress_items():
            return
        cls.release_all()

    @classmethod
    def release_all(cls):
        """Removes all progressbars"""
        if not cls._is_drawn:
            return

        from importlib import reload

        assert(cls._attrname)
        delattr(WindowManager, cls._attrname)
        bpy.utils.unregister_class(progress.ProgressPropertyItem)

        reload(space_statusbar)
        STATUSBAR_HT_header.draw = space_statusbar.STATUSBAR_HT_header.draw
        _update_statusbar()

        del reload

        cls._is_drawn = False
