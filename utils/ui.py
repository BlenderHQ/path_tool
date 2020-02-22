
def operator_draw(self, context):
    layout = self.layout

    layout.use_property_split = True
    layout.use_property_decorate = False

    col = layout.column(align=True)

    row = col.row()
    row.prop(self, "mark_select", text="Select", icon_only=True, expand=True)
    row = col.row()
    row.prop(self, "mark_seam", text="Seam", icon_only=True, expand=True)
    row = col.row()
    row.prop(self, "mark_sharp", text="Sharp", icon_only=True, expand=True)


def popup_menu_pie_draw(self, popup, context):
    layout = popup.layout
    pie = layout.menu_pie()

    box = pie.box()

    col = box.column(align=True)

    row = col.row(align=True)
    row.label(text="Select:")
    row.prop(self, "mark_select", icon_only=True, expand=True)

    row = col.row(align=True)
    row.label(text="Seams:")
    row.prop(self, "mark_seam", icon_only=True, expand=True)

    row = col.row(align=True)
    row.label(text="Sharp:")
    row.prop(self, "mark_sharp", icon_only=True, expand=True)

    scol = col.column()
    scol.emboss = 'NONE'
    scol.prop(self, "view_center_pick")
    scol.emboss = 'NORMAL'

    row = scol.row(align=True)
    row.prop(self, "context_undo", expand=True)

    pie.prop_tabs_enum(self, "context_action")
