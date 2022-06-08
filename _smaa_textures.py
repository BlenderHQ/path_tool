import gpu

import numpy as np

from .shaders import _smaa_tex_data

searchTex_float = (np.array(_smaa_tex_data.searchTexBytes, dtype=np.ubyte) / 255).astype(np.float32)


searchTex = gpu.types.GPUTexture(
    size=(_smaa_tex_data.SEARCHTEX_SIZE),
    format='R32F',
    data=gpu.types.Buffer(
        'FLOAT',
        _smaa_tex_data.SEARCHTEX_SIZE,
        searchTex_float,
    )
)

areaTex_float = (np.array(_smaa_tex_data.areaTexBytes, dtype=np.ubyte) / 255).astype(np.float32)
areaTex = gpu.types.GPUTexture(
    size=(_smaa_tex_data.AREATEX_WIDTH, _smaa_tex_data.AREATEX_HEIGHT),
    format='RG32F',
    data=gpu.types.Buffer(
        'FLOAT',
        _smaa_tex_data.AREATEX_SIZE,
        areaTex_float,
    )
)
