from __future__ import annotations

import os

import gpu
from gpu.types import (
    GPUShader,
    GPUShaderCreateInfo,
    GPUStageInterfaceInfo,
)

from ..lib import bhqglsl
from ..lib.bhqglsl.ubo import (
    glsl_bool,
    glsl_float,
    glsl_int,
    glsl_mat4,
    glsl_vec2,
    glsl_vec4,
)

__all__ = (
    "INTERN_DIR",
    "get",
    "register",
)

INTERN_DIR = os.path.join(os.path.dirname(__file__), "intern")


class CommonParams(bhqglsl.ubo.StructUBO):
    model_matrix: glsl_mat4
    color_cp: glsl_vec4
    color_active_cp: glsl_vec4
    color_path: glsl_vec4
    color_active_path: glsl_vec4
    index_active: glsl_int
    point_size: glsl_float

    _fields_ = (
        ("model_matrix", glsl_mat4),
        ("color_cp", glsl_vec4),
        ("color_active_cp", glsl_vec4),
        ("color_path", glsl_vec4),
        ("color_active_path", glsl_vec4),
        ("index_active", glsl_int),
        ("point_size", glsl_float),
        ("_pad0", glsl_vec2),
    )


assert (CommonParams.check_alignment())


def _create_shader_cp_vert() -> GPUShader:
    vertexcode, fragcode, geocode = bhqglsl.read_shader_files(
        directory=INTERN_DIR,
        filenames=("common.vert", "cp_vert.frag", "cp_vert.geom"),
    )

    geocode = (
        "layout(points) in;\n"
        "layout(triangle_strip, max_vertices = 12) out;\n"
        f"{geocode}\n"
    )

    defines = CommonParams.as_struct()

    return GPUShader(vertexcode=vertexcode, fragcode=fragcode, geocode=geocode, defines=defines)


def _create_shader_cp_face() -> GPUShader:
    vertexcode, fragcode = bhqglsl.read_shader_files(
        directory=INTERN_DIR,
        filenames=("common.vert", "cp_face.frag"),
    )

    info = GPUShaderCreateInfo()
    info.vertex_in(0, 'VEC3', "P")

    info.push_constant('MAT4', "ModelViewProjectionMatrix")
    info.push_constant('VEC4', "u_ViewportMetrics")
    info.uniform_buf(0, CommonParams.__qualname__, "u_Params")

    info.sampler(0, 'FLOAT_2D', "u_DepthMap")

    info.fragment_out(0, 'VEC4', "f_Color")

    info.typedef_source(CommonParams.as_struct())

    info.vertex_source(vertexcode)
    info.fragment_source(fragcode)

    return gpu.shader.create_from_info(info)


def _create_shader_path() -> GPUShader:
    vertexcode, fragcode = bhqglsl.read_shader_files(
        directory=INTERN_DIR,
        filenames=("common.vert", "path.frag"),
    )

    info = GPUShaderCreateInfo()
    info.vertex_in(0, 'VEC3', "P")

    info.push_constant('MAT4', "ModelViewProjectionMatrix")
    info.push_constant('VEC4', "u_ViewportMetrics")

    info.uniform_buf(0, CommonParams.__qualname__, "u_Params")

    info.sampler(0, 'FLOAT_2D', "u_DepthMap")

    info.fragment_out(0, 'VEC4', "f_Color")

    info.typedef_source(CommonParams.as_struct())

    info.vertex_source(vertexcode)
    info.fragment_source(fragcode)

    return gpu.shader.create_from_info(info)


_SHADERS = dict()


def get(name: str) -> None | GPUShader:
    return _SHADERS.get(name, None)


def register():
    _SHADERS["cp_vert"] = _create_shader_cp_vert()
    _SHADERS["cp_face"] = _create_shader_cp_face()
    _SHADERS["path"] = _create_shader_path()
