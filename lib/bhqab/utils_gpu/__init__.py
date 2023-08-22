from __future__ import annotations

if "bpy" in locals():
    from importlib import reload

    reload(draw_framework)
    reload(shaders)
else:
    from . import draw_framework
    from . import shaders

__all__ = (
    "draw_framework",
    "shaders",
)
