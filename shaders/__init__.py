import os

import gpu

SEPARATOR = "_"

SHADER_EXTENSION = ".glsl"
SHADER_VERTEX = "vert"
SHADER_FRAGMENT = "frag"
SHADER_GEOMETRY = "geom"
SHADER_DEFINES = "def"
SHADER_LIBRARY = "lib"


def _generate_shaders():
    """
    Returns a dictionary consisting where the key is the name of the shader and the value is the GPUShader object
    @return: dict - {str shader_name: GPUShader}
    """
    shader_endings = (
        SHADER_VERTEX,
        SHADER_FRAGMENT,
        SHADER_GEOMETRY,
        SHADER_DEFINES,
        SHADER_LIBRARY
    )

    _shader_dict = {}
    _shader_library = ""
    _defines_library = ""  # Currently not used

    directory_path = os.path.dirname(__file__)

    for filename in os.listdir(directory_path):
        filepath = os.path.join(directory_path, filename)

        if not os.path.isfile(filepath):
            continue

        name, extension = os.path.splitext(filename)

        if extension != SHADER_EXTENSION:
            continue

        # The name of the shader is determined by the names of the shader files that make it up.
        name_split = name.split(SEPARATOR)

        if len(name_split) == 1:
            raise NameError("Shader name must be name_type.glsl pattern")
        if len(name_split) == 2:
            shader_name, shader_type = name_split
        else:
            # Shader files can have names by pattern "shader_name_separated_vert.glsl"
            shader_type = name_split[-1]
            shader_name = SEPARATOR.join(name_split[:-1])

        if shader_type in shader_endings[0:2]:  # Vertex and fragment ("_vert", "_frag")
            if shader_name not in _shader_dict:
                _shader_dict[shader_name] = [None for _ in range(5)]

            shader_index = shader_endings.index(shader_type)
            with open(filepath, 'r') as code:
                data = code.read()
                _shader_dict[shader_name][shader_index] = data

        elif shader_type == SHADER_LIBRARY:  # Code containing common functions for all shaders used ("_lib")
            with open(filepath, 'r') as code:
                data = code.read()
                _shader_library += "\n\n%s" % data

        elif shader_type == SHADER_DEFINES:  # Preprocessor directives
            # TODO: Usage of defines
            with open(filepath, 'r') as code:
                data = code.read()
                _defines_library += "\n\n%s" % data
    _res = {}
    for shader_name in _shader_dict.keys():
        shader_code = _shader_dict[shader_name]
        vertex_code, frag_code, geo_code, lib_code, defines = shader_code
        if _shader_library:
            lib_code = _shader_library
        if _defines_library:
            defines = _defines_library
        kwargs = {"vertexcode": vertex_code,
                  "fragcode": frag_code,
                  "geocode": geo_code,
                  "libcode": lib_code,
                  "defines": defines}

        kwargs = dict(filter(lambda item: item[1] is not None, kwargs.items()))

        data = gpu.types.GPUShader(**kwargs)
        _res[shader_name] = data

    assert len(_res)

    return _res


class ShaderStorage(object):
    def __init__(self):
        for shader_name, data in _generate_shaders().items():
            object.__setattr__(self, shader_name, data)


shader = ShaderStorage()  # The main instance container containing all the shaders
