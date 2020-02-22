from bpy.props import BoolProperty, EnumProperty

context_action = EnumProperty(
    items=[
        ('TCLPATH', "Toggle Close Path", "Close the path from the first to the last control point", '', 2),
        ('CHDIR', "Change direction", "Changes the direction of the path", '', 4),
        ('APPLY', "Apply All", "Apply all paths and make changes to the mesh", '', 8),
    ],
    options={'ENUM_FLAG'},
    default=set(),
)

context_undo = EnumProperty(
    items=[
        ('UNDO', "Undo", "Undo one step", 'LOOP_BACK', 2),
        ('REDO', "Redo", "Redo one step", 'LOOP_FORWARDS', 4),
    ],
    options={'ENUM_FLAG'},
    default=set()
)

mark_select = EnumProperty(
    items=[
        ('EXTEND', "Extend", "Extend existing selection", 'SELECT_EXTEND', 1),
        ('NONE', "Do nothing", "Do nothing", "X", 2),
        ('SUBTRACT', "Subtract", "Subtract existing selection", 'SELECT_SUBTRACT', 3),
        ('INVERT', "Invert", "Inverts existing selection", 'SELECT_DIFFERENCE', 4)
    ],
    name="Select",
    default='EXTEND',
    description="Selection options"
)

mark_seam = EnumProperty(
    items=[
        ('MARK', "Mark", "Mark seam path elements", 'RESTRICT_SELECT_OFF', 1),
        ('NONE', "Do nothing", "Do nothing", 'X', 2),
        ('CLEAR', "Clear", "Clear seam path elements", 'RESTRICT_SELECT_ON', 3),
        ('TOGGLE', "Toggle", "Toggle seams on path elements", 'ACTION_TWEAK', 4)
    ],
    name="Seams",
    default='NONE',
    description="Mark seam options"
)

mark_sharp = EnumProperty(
    items=[
        ('MARK', "Mark", "Mark sharp path elements", 'RESTRICT_SELECT_OFF', 1),
        ('NONE', "Do nothing", "Do nothing", 'X', 2),
        ('CLEAR', "Clear", "Clear sharp path elements", 'RESTRICT_SELECT_ON', 3),
        ('TOGGLE', "Toogle", "Toogle sharpness on path", 'ACTION_TWEAK', 4)
    ],
    name="Sharp",
    default="NONE",
    description="Mark sharp options"
)

view_center_pick = BoolProperty(
    name="Focus Active",
    default=True,
    description="Center the view to the position of the active control point"
)
