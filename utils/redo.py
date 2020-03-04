def get_current_state_copy(self):
    return [self._active_path_index, [n.copy() for n in self.path_seq]]


def undo(self, context):
    if len(self.undo_history) == 1:
        self.cancel(context)
        return {'CANCELLED'}

    elif len(self.undo_history) > 1:
        step = self.undo_history.pop()
        self.redo_history.append(step)
        self._active_path_index, self.path_seq = self.undo_history[-1]
        self._just_closed_path = False

    context.area.tag_redraw()

    return {'RUNNING_MODAL'}


def redo(self, context):
    if len(self.redo_history) > 0:
        step = self.redo_history.pop()
        self.undo_history.append(step)
        self._active_path_index, self.path_seq = self.undo_history[-1]
        context.area.tag_redraw()
    else:
        self.report({'WARNING'}, message="Can not redo anymore")


def register_undo_step(self):
    step = get_current_state_copy(self)
    self.undo_history.append(step)
    self.redo_history.clear()
