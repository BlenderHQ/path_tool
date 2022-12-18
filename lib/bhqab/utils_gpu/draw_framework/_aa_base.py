from __future__ import annotations
from enum import auto, IntEnum
from typing import Literal

from mathutils import Matrix

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
    """
    __slots__ = (
        "_preset",
        "_preset_0",
    )
    _preset: AAPreset
    _preset_0: AAPreset

    def __init__(self):
        self._preset = AAPreset.NONE
        self._preset_0 = AAPreset.NONE

    @classmethod
    @property
    def name(cls):
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

    def draw(self, *, texture: GPUTexture) -> None:
        """
        Draw method. Performs a basic check before calling the main method

        :param texture: Input texture
        :type texture: `GPUTexture`_
        """
        assert (AAPreset.NONE != self._preset)
