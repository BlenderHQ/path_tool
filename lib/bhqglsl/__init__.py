# BlenderHQ GLSL utility module.
# Copyright (C) 2023 Ivan Perevala (ivpe)

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

__all__ = (
    "ubo",
    "get_libraries_dict",
    "read_shader_files",
    "process_shader_requirements",
)

import os
import re

from typing import Iterable

from . import ubo

library_names = (
    "colorspace",
    "constants",
    "lens_distortion",
    "mask_fragment_stage",
    "mask_vertex_stage",
    "sampler_map",
    "space",
    "tiles",
    "dithering",
    "fxaa_lib",
)

pragma_pattern = r'#pragma BHQGLSL_REQUIRE\((.*?)\)'

_libs: dict[str, str] = dict()


def get_libraries_dict() -> dict[str, str]:
    if not _libs:
        base_dir = os.path.dirname(__file__)

        for name in library_names:
            with open(os.path.join(base_dir, f"{name}.glsl"), 'r', encoding='utf-8') as file:
                _libs[name] = file.read()

        for name in library_names:
            _libs[name] = process_shader_requirements(data=_libs[name])

    return _libs


def read_shader_files(*, directory: str, filenames: Iterable[str], process_requirements: bool = True) -> list[str]:
    ret = list()
    for name in filenames:
        with open(os.path.join(directory, name), 'r', encoding='utf-8') as file:
            data = file.read()
            if process_requirements:
                data = process_shader_requirements(data=data)
            ret.append(data)
    return ret


def process_shader_requirements(*, data: str) -> str:
    libs = get_libraries_dict()

    requirements = {item for match in re.findall(pragma_pattern, data) for item in re.split(r',\s*', match)}
    if requirements:
        data = "\n".join((libs[item] for item in requirements)) + re.sub(pragma_pattern, '', data)

    return data
