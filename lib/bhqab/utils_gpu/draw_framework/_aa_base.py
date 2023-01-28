from __future__ import annotations

from enum import auto, IntEnum
from typing import Literal

from bpy.types import (
    Context,
)

from mathutils import Matrix

import gpu
from gpu.types import (
    GPUTexture,
)

__all__ = (
    "AAPreset",
    "IDENTITY_M4X4",
    "AABase",
)


class AAPreset(IntEnum):
    """
    Enumerator of possible anti-aliasing presets. Contained in this API is mostly for documentation purposes, used
    internally.

    :cvar IntEnum NONE: No anti-aliasing
    :cvar IntEnum LOW: Low anti-aliasing level
    :cvar IntEnum MEDIUM: Medium anti-aliasing level
    :cvar IntEnum HIGH: High anti-aliasing level
    :cvar IntEnum ULTRA: Ultra anti-aliasing level

    """
    NONE = auto()
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    ULTRA = auto()


IDENTITY_M4X4 = Matrix.Identity(4)


class AABase(object):
    """
    Base class for anti-aliasing methods

    :cvar str name: The name of the anti-aliasing method. Corresponds to the name of the class
    :cvar str description: The description of the anti-aliasing method. Corresponds to the documentation string of the
    class

    :ivar str preset: Current preset

    """
    __slots__ = (
        "_preset",
        "_preset_0",
    )
    _preset: AAPreset
    _preset_0: AAPreset

    def __init__(self, *, area_type='VIEW_3D', region_type='WINDOW'):
        self._preset = AAPreset.NONE
        self._preset_0 = AAPreset.NONE

    @classmethod
    @property
    def name(cls) -> str:
        return cls.__name__

    @classmethod
    @property
    def description(cls):
        return cls.__doc__

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
    def _setup_gpu_state():
        gpu.matrix.load_matrix(IDENTITY_M4X4)
        gpu.matrix.load_projection_matrix(IDENTITY_M4X4)
        gpu.state.blend_set('ALPHA_PREMULT')
        gpu.state.front_facing_set(True)
        gpu.state.face_culling_set('BACK')
        gpu.state.depth_mask_set(0)
        gpu.state.depth_test_set('ALWAYS')

    def modal_eval(self, context: Context, color_format: str = "", percentage: int = 100):
        """
        Modal evaluation

        :param context: Current context
        :type context: `Context`_
        :param color_format: Color texture format. See `GPUTexture`_ for details, defaults to ""
        :type color_format: str, optional
        :param percentage: Size percentage, defaults to 100
        :type percentage: int, optional
        """
        pass

    def draw(self, *, texture: GPUTexture) -> None:
        """
        Draw method. Performs a basic check before calling the main method

        :param texture: Input texture
        :type texture: `GPUTexture`_
        """
        assert (AAPreset.NONE != self._preset)
