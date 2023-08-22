import os
import re

import bpy
from gpu.types import GPUShader

def eval_shaders_dict(
        *,
        dir_path: str,
        file_ext: str | set[str] = ".glsl",
        sep: str = '_',
        suffix_vertexcode: str = "vert",
        suffix_fragcode: str = "frag",
        suffix_geocode: str = "geom",
        suffix_libcode: str = "lib",
        suffix_defines: str = "def",
        suffix_defines_vert: str = "vertdef",
        libcode: str = "",
        defines: str = "",
        vert_defines: str = "",
) -> dict[str, GPUShader]:
    """
    Helper function for generating shaders from files.

    :param dir_path: Directory containing shader files
    :type dir_path: str
    :param file_ext: File extension that will be used during the search, default to ``".glsl"``
    :type file_ext: str | set[str], optional
    :param sep: Delimiter character in file name, default to ``'_'``
    :type sep: str, optional
    :param suffix_vertexcode: Vertex shader file name suffix, default to ``"vert"``
    :type suffix_vertexcode: str, optional
    :param suffix_fragcode: Fragment shader file name suffix, default to ``"frag"``
    :type suffix_fragcode: str, optional
    :param suffix_geocode: Geometry shader file name suffix, default to ``"vert"``
    :type suffix_geocode: str, optional
    :param suffix_libcode: Library file name suffix, default to ``"lib"``
    :type suffix_libcode: str, optional
    :param suffix_defines: Defines file name suffix, default to ``"def"``
    :type suffix_defines: str, optional
    :param suffix_defines_vert: Defines applied for vertex shader only file name suffix, default to ``"vertdef"``
    :type suffix_defines_vert: str, optional
    :param libcode: Library code.
    :type libcode: str, optional
    :param defines: Pre-processor definitions required for operations
    :type defines: str, optional
    :param vert_defines: Vertex stage pre-processor definitions required for operations
    :type vert_defines: str, optional

    :return: Dictionary with shader names as keys and shaders as values
    :rtype: dict[str, `GPUShader`_]:
    """

    r_dict = dict()

    if not bpy.app.background:
        shaders_kwargs_eval: dict[str, dict[str, str]] = dict()
        libcode_eval = f"\n{libcode}\n\n"
        defines_eval = f"\n{defines}\n\n"
        defines_vert_eval = f"\n{vert_defines}\n\n"

        shader_suffix_to_code_kwarg = {
            suffix_vertexcode: "vertexcode",
            suffix_fragcode: "fragcode",
            suffix_geocode: "geocode"
        }

        for file_name in os.listdir(dir_path):
            fp = os.path.join(dir_path, file_name)

            name, ext = os.path.splitext(file_name)

            if (
                (isinstance(file_ext, str) and (ext == file_ext))
                or (isinstance(file_ext, set) and (ext in file_ext))
            ):
                spl_name = name.split(sep)

                if len(spl_name) > 1:
                    if len(spl_name) == 2:
                        shader_name_eval, name_suffix = spl_name
                    else:
                        name_suffix = spl_name[-1]
                        shader_name_eval = sep.join(spl_name[:-1])

                    if name_suffix in shader_suffix_to_code_kwarg:
                        if shader_name_eval not in shaders_kwargs_eval:
                            shaders_kwargs_eval[shader_name_eval] = dict(name=shader_name_eval,)
                        with open(fp, 'r', encoding='utf-8') as file:
                            data = file.read()
                            shaders_kwargs_eval[shader_name_eval][shader_suffix_to_code_kwarg[name_suffix]] = data

                    elif name_suffix == suffix_libcode:
                        with open(fp, 'r', encoding='utf-8') as file:
                            libcode_eval += f"\n\n{file.read()}\n\n"

                    elif name_suffix == suffix_defines:
                        with open(fp, 'r', encoding='utf-8') as file:
                            defines_eval += f"\n\n{file.read()}\n\n"

                    elif name_suffix == suffix_defines_vert:
                        with open(fp, 'r', encoding='utf-8') as file:
                            defines_vert_eval += f"\n\n{file.read()}\n\n"

        for shader_name, kwargs in shaders_kwargs_eval.items():
            if libcode_eval:
                kwargs["libcode"] = libcode_eval
            if defines_eval:
                kwargs["defines"] = defines_eval
            if defines_vert_eval:
                kwargs["vertexcode"] = defines_vert_eval + '\n' + kwargs["vertexcode"]

            r_dict[shader_name] = GPUShader(**kwargs)

    return r_dict