import os

import bpy
from gpu.types import GPUShader


def eval_shaders_dict(
    dir_path: str,
        file_ext: str = ".glsl",
        sep: str = '_',
        suffix_vert: str = "vert",
        suffix_frag: str = "frag",
        suffix_geom: str = "geom",
        suffix_def: str = "def",
        suffix_lib: str = "lib",
) -> dict[str, GPUShader]:
    r_dict = dict()

    if not bpy.app.background:
        shader_endings = (
            suffix_vert,
            suffix_frag,
            suffix_geom,
            suffix_def,
            suffix_lib,
        )

        _shader_dict = dict()
        _shader_library = ""
        _defines_library = ""

        for file_name in os.listdir(dir_path):
            fp = os.path.join(dir_path, file_name)

            name, ext = os.path.splitext(file_name)

            if file_ext == ext:
                name_split = name.split(sep)

                if len(name_split) > 1:
                    if len(name_split) == 2:
                        shader_name, shader_type = name_split
                    else:
                        shader_type = name_split[-1]
                        shader_name = sep.join(name_split[:-1])

                    if shader_type in shader_endings[0:3]:
                        if shader_name not in _shader_dict:
                            _shader_dict[shader_name] = [None for _ in range(5)]
                            _shader_dict[shader_name][0] = ""
                            _shader_dict[shader_name][1] = ""
                        shader_index = shader_endings.index(shader_type)
                        with open(fp, 'r') as code:
                            data = code.read()
                            _shader_dict[shader_name][shader_index] = data

                    elif shader_type == suffix_lib:
                        with open(fp, 'r') as code:
                            data = code.read()
                            _shader_library += f"\n\n{data}\n\n"

                    elif shader_type == suffix_def:
                        with open(fp, 'r') as code:
                            data = code.read()
                            _defines_library += f"\n\n{data}\n\n"

        for shader_name in _shader_dict.keys():
            shader_code = _shader_dict[shader_name]
            vertex_code, frag_code, geo_code, lib_code, defines = shader_code
            if _shader_library:
                lib_code = _shader_library
            if _defines_library:
                defines = _defines_library

            kwargs = dict(
                vertexcode=vertex_code,
                fragcode=frag_code,
                geocode=geo_code,
                libcode=lib_code,
                defines=defines
            )

            kwargs = dict(filter(lambda item: item[1] is not None, kwargs.items()))

            r_dict[shader_name] = GPUShader(**kwargs)

    return r_dict
