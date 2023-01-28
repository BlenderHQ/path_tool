from __future__ import annotations

import os
import logging
from types import FunctionType
from typing import (
    Generator,
    Iterable,
    Literal,
)
import random
import string
import importlib
import atexit

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
    EnumProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
)
import blf
import rna_keymap_ui
from bpy.app.handlers import persistent
from bl_ui import space_statusbar

from . import utils_id

__all__ = (
    "supported_image_extensions",
    "eval_unique_name",
    "draw_wrapped_text",
    "developer_extras_poll",
    "template_developer_extras_warning",
    "template_tool_keymap",
    "template_input_info_kmi_from_type",
    "progress",
    "launch_progress_update_id_previews",
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
    Blender supported image extensions.

    :return: Tuple of lowercase extensions:

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

        The data provided by this function comes from:

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
    :type prefix: str, optional
    :param suffix: Name suffix, defaults to ""
    :type suffix: str, optional
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


def _string_width(string):
    if len(string) == 1:
        num_single_ch_samples = 100
        return blf.dimensions(0, string * num_single_ch_samples)[0] / num_single_ch_samples
    return blf.dimensions(0, string)[0]


def draw_wrapped_text(context: Context, layout: UILayout, *, text: str) -> None:
    """
    Draws a block of ``text`` in the given layout, dividing it into lines according to the width of the current region
    of the interface.

    :param context: Current context
    :type context: `Context`_
    :param layout: Current layout
    :type layout: `UILayout`_
    :param text: Text to be wrapped and drawn
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
    space_width = _string_width(' ')

    for line in text.split('\n'):
        num_characters = len(line)

        if not num_characters:
            col.separator()
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
    :type context: `Context`_
    :return: A positive value means that it should
    :rtype: bool
    """
    return context.preferences.view.show_developer_ui


def template_developer_extras_warning(context: Context, layout: UILayout) -> None:
    """
    Output message in the user interface that this section of the interface is visible because the active options in the
    Blender settings. These options are also displayed with the ability to disable them.

    :param context: Current context
    :type context: `Context`_
    :param layout: Current UI layout
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
    Template for tool keymap items.

    :param context: Current context
    :type context: `Context`_
    :param layout: Current UI layout
    :type layout: `UILayout`_
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
    Method for displaying icons of possible keys.

    :param layout: Current UI layout
    :type layout: `UILayout`_
    :param label: Label to be displayed with possible keys icons
    :type label: str
    :param event_types: Set of event types (see `Event.type`_), defaults to set()
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
    bpy.context.workspace.status_text_set(text=None)


class _progress_meta(type):
    @property
    def PROGRESS_BAR_UI_UNITS(cls):
        return cls._PROGRESS_BAR_UI_UNITS

    @PROGRESS_BAR_UI_UNITS.setter
    def PROGRESS_BAR_UI_UNITS(cls, value):
        cls._PROGRESS_BAR_UI_UNITS = max(cls._PROGRESS_BAR_UI_UNITS_MIN, min(value, cls._PROGRESS_BAR_UI_UNITS_MAX))


class progress(metaclass=_progress_meta):
    """A class that implements the initialization and completion of progressbars. The module provides the ability to
    display the progressbar (and even several progressbars) in the status bar of the Blender. This technique can be used
    mainly with modal operators that run for a relatively long time and require the output of the progress of their
    work.

    :cvar int PROGRESS_BAR_UI_UNITS: Number of UI units in range [4...12] used for progressbar without text label
        and icon. Default to 6 (readonly)
    """

    _PROGRESS_BAR_UI_UNITS = 6
    _PROGRESS_BAR_UI_UNITS_MIN = 4
    _PROGRESS_BAR_UI_UNITS_MAX = 12

    _is_drawn = False
    _attrname = ""

    class ProgressPropertyItem(PropertyGroup):
        """Progress bar item that allows you to dynamically change some display parameters.

        :ivar int num_steps: Number of progress steps.
        :ivar int step: Current progress step.
        :ivar float value: Evaluated progress value (readonly).
        :ivar str icon: Blender icon to be displayed.
        :ivar int icon_value: Icon id to be displayed.
        :ivar str label: Progressbar text label.
        :ivar bool cancellable: Positive value means that progressbar should draw cancel button.
        """

        def _common_value_update(self, _context):
            _update_statusbar()

        valid: BoolProperty(  # Internal valid markup, not for docs
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
            default=0,
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
        :return: All progress property items
        :rtype: Array of :class:`ProgressPropertyItem`
        """
        return getattr(bpy.context.window_manager, cls._attrname)

    @classmethod
    def valid_progress_items(cls) -> Generator[ProgressPropertyItem]:
        """
        Iterate over valid progress property items

        :yield: Valid item
        :rtype: Generator[:class:`ProgressPropertyItem`]
        """
        return (_ for _ in cls.progress_items() if _.valid)

    @classmethod
    def invoke(cls) -> ProgressPropertyItem:
        """
        Invoke new progressbar for each call.

        :return: New initialized progress property item
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
        Removes progressbar from UI. If removed progressbar was the last one, would be called
        :func:`progress.release_all` class method.

        :param item: Progress item to be removed
        :type item: :class:`ProgressPropertyItem`
        """
        assert (isinstance(item, progress.ProgressPropertyItem))

        item.valid = False

        for _ in cls.valid_progress_items():
            return
        cls.release_all()

    @classmethod
    def release_all(cls):
        """Removes all progressbars"""
        if not cls._is_drawn:
            return

        assert (cls._attrname)
        delattr(WindowManager, cls._attrname)
        bpy.utils.unregister_class(progress.ProgressPropertyItem)

        importlib.reload(space_statusbar)
        STATUSBAR_HT_header.draw = space_statusbar.STATUSBAR_HT_header.draw
        _update_statusbar()

        cls._is_drawn = False


class BHQAB_OT_update_previews_internal(Operator):
    # NOTE: `bl_idname` would be evaluated just before registration
    bl_label = "BHQAB Update Previews (Internal)"
    bl_options = {'INTERNAL'}

    type: EnumProperty(
        items=utils_id.prop_prv_id_items(),
        default=utils_id.prop_prv_id_items()[0][0],
    )

    __instances__: set = set()
    __timer__: None | bpy.types.Timer = None

    @classmethod
    def _validate_cls_instances(cls):
        invalid = set()
        for inst in cls.__instances__:
            try:
                getattr(inst, "bl_idname")
            except ReferenceError:
                invalid.add(inst)
        if invalid:
            cls.__instances__.difference_update(invalid)

    __slots__ = (
        "_progress",
        "_coll",
        "_draw_func",
    )
    _initial_show_statusbar: bool = True
    _progress: progress.ProgressPropertyItem
    _coll: bpy.types.bpy_prop_collection
    _draw_func: FunctionType

    def get_draw_func(self):
        def draw_func(item, _context):
            layout: UILayout = item.layout
            row = layout.row(align=True)
            for i in range(self._progress.step, min(self._progress.step + 1, self._progress.num_steps)):
                icon_value = self._coll[i].preview_ensure().icon_id
                row.template_icon(icon_value=icon_value)  # Large preview
                # NOTE: Sometimes for some reason Blender do not render smaller preview
                row.label(icon_value=icon_value)
            # NOTE: There's a trick here: we add progress only when the icon is already shown, not the normal way, in
            # the modal part
            self._progress.step += 1
        return draw_func

    def invoke(self, context, _event):
        cls = self.__class__

        # Check that no instance is running with the same data type
        cls._validate_cls_instances()
        for inst in cls.__instances__:
            if inst.type == self.type:
                return {'CANCELLED'}
        cls.__instances__.add(self)

        # Evaluate which blend data we would process
        prv_id = utils_id.PrvID[self.type]
        self._coll = utils_id.eval_coll_from_type(prv_id)

        # Immediately terminate if there is no data to process
        if not self._coll:
            return {'CANCELLED'}

        # Statusbar must be shown at least while we shoving previews, otherwise preview generation would not be called
        # Also, create a restore point, if statusbar was hidden initially
        screen = context.window.screen
        cls._initial_show_statusbar = screen.show_statusbar
        screen.show_statusbar = True

        # Create UI progressbar
        self._progress = progress.invoke()
        self._progress.label = f"{utils_id.eval_name_from_type(prv_id)} previews"
        self._progress.num_steps = len(self._coll)
        self._progress.step = 0
        self._progress.cancellable = True

        # Add draw function to statusbar
        self._draw_func = self.get_draw_func()

        importlib.reload(space_statusbar)
        STATUSBAR_HT_header.append(self._draw_func)

        # Add modal handler and event timer
        wm = context.window_manager
        if cls.__timer__ is None:
            cls.__timer__ = wm.event_timer_add(1 / 60, window=context.window)
        wm.modal_handler_add(self)

        return {'RUNNING_MODAL'}

    def cancel(self, context):
        cls = self.__class__
        # Clear draw function callback
        importlib.reload(space_statusbar)
        STATUSBAR_HT_header.remove(self._draw_func)
        del self._draw_func

        # Restore screen's statusbar visibility after execution
        screen = context.window.screen
        screen.show_statusbar = cls._initial_show_statusbar

        # Clear progress
        progress.complete(item=self._progress)

        cls._validate_cls_instances()
        # Remove self from class instances
        cls.__instances__.remove(self)

        # Remove class event timer if no instances left
        if cls.__timer__ is not None and not cls.__instances__:
            context.window_manager.event_timer_remove(cls.__timer__)
            cls.__timer__ = None

    def modal(self, context, event: Event):
        if (self._progress.step >= self._progress.num_steps) or (not self._progress.valid):
            self.cancel(context)
            return {'FINISHED'}
        return {'PASS_THROUGH'}


def _reg_ot_update_previews_internal():
    if not hasattr(BHQAB_OT_update_previews_internal, "bl_idname"):
        BHQAB_OT_update_previews_internal.bl_idname = eval_unique_name(
            arr=bpy.ops,
            prefix="bhqab",
            suffix="_update_previews_internal"
        )

    try:
        bpy.utils.register_class(BHQAB_OT_update_previews_internal)
    except ValueError:
        pass


def _unreg_ot_update_previews_internal():
    try:
        bpy.utils.unregister_class(BHQAB_OT_update_previews_internal)
    except ValueError:
        pass


if 0:  # NOTE: For some reasons Blender quits with error if this was called
    atexit.register(_unreg_ot_update_previews_internal)


def launch_progress_update_id_previews(
    *,
    id_type: Literal['OB', 'MA', 'TE', 'WO', 'LA',
                     'IM', 'BR', 'GR', 'SCE', 'SCR', 'AC', 'NT']
):
    """
    Starts showing a preview of the selected type in the status bar. This is more of a gimmicky way, but it allows
    you to trigger a generation preview in the same way that Blender does it by itself, without blocking the main thread
    of the application. It is obvious that this method is not ideal from a user interface point of view, but currently
    Blender has no other way to trigger preview generation via API calls.

    :param id_type: ID name prefix
    :type id_type: Literal['OB', 'MA', 'TE', 'WO', 'LA', 'IM', 'BR', 'GR', 'SCE', 'SCR', 'AC', 'NT']

    .. seealso::

        :class:`bhqab.utils_id.PrvID`
    """
    _reg_ot_update_previews_internal()
    func = eval(f"bpy.ops.{BHQAB_OT_update_previews_internal.bl_idname}")
    func('INVOKE_DEFAULT', type=id_type)


def copy_default_presets_from(*, src_root: str):
    """Copying preset files from the ``src_root`` directory (by design, which is in the addon itself) to the directory
    with Blender presets.

    :param src_root: Source preset files root directory.
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
    Template for drawing presets. Can be used to unify the appearance.

    :param layout: Current layout
    :type layout: `UILayout`_
    :param menu: The menu class that will be used for selection
    :type menu: 'Menu'_
    :param operator: Operator ``bl_idname`` used to add and remove presets
    :type operator: str
    """
    row = layout.row(align=True)
    row.use_property_split = False

    row.menu(menu=menu.__name__, text=menu.bl_label)
    row.operator(operator=operator, text="", icon='ADD')
    row.operator(operator=operator, text="", icon='REMOVE').remove_active = True


def template_disclosure_enum_flag(layout: UILayout, *, item: ID, prop_enum_flag: str, flag: str) -> bool:
    """
    A function for unifying the rendering and management of sections of the user interface without creating additional
    panels.

    :param layout: Current UI layout
    :type layout: UILayout
    :param item: The parent class that stores the ``prop_enum_flag`` property.
    :type item: ID
    :param prop_enum_flag: A property that stores the available sections. It is a class annotation and derives from
        `EnumProperty`_ `(options={'ENUM_FLAG'})`
    :type prop_enum_flag: str
    :param flag: The flag to be checked.
    :type flag: str
    :return: A positive value means that you need to draw this section.
    :rtype: bool
    """
    row = layout.row()
    row.use_property_split = False
    row.emboss = 'NONE_OR_STATUS'
    row.alignment = 'LEFT'
    icon = 'DISCLOSURE_TRI_RIGHT'

    ret = False
    if flag in getattr(item, prop_enum_flag):
        icon = 'DISCLOSURE_TRI_DOWN'
        ret = True
    row.prop_enum(item, prop_enum_flag, flag, icon=icon)

    return ret


class LoggingUtils:
    _LOG_LEVELS = (
        (logging.getLevelName(logging.CRITICAL), "Critical", logging.CRITICAL),
        (logging.getLevelName(logging.ERROR), "Error", logging.ERROR),
        (logging.getLevelName(logging.WARNING), "Warning", logging.WARNING),
        (logging.getLevelName(logging.INFO), "Info", logging.INFO),
        (logging.getLevelName(logging.DEBUG), "Debug", logging.DEBUG),
        (logging.getLevelName(logging.NOTSET), "Not Set", logging.NOTSET),
    )

    def _log_level_update(self, _context: Context):
        level = logging.NOTSET
        for key, name, level in LoggingUtils._LOG_LEVELS:
            if key == self.log_level:
                break
        # logging.basicConfig(level=level)
        logging.root.setLevel(level)

    prop_log_level = EnumProperty(
        items=[(key, name, "") for key, name, _level in _LOG_LEVELS],
        default=logging.getLevelName(logging.NOTSET),
        update=_log_level_update,
        name="Logging Level",
        description="Logging messages which are less severe than level will be ignored",
    )

    def load_post_handler(*, addon_module_name: str) -> FunctionType:

        @persistent
        def wrapper(_=None):
            addon_pref = bpy.context.preferences.addons[addon_module_name].preferences
            addon_pref.log_level = addon_pref.log_level  # Call ``_log_level_update``

        return wrapper
