smaa_vert = """


out vec2 pixcoord;

out vec2 uvs;
out vec4 offset[3];


void main()
{
  int v = gl_VertexID % 3;
  float x = -1.0 + float((v & 1) << 2);
  float y = -1.0 + float((v & 2) << 1);
  gl_Position = vec4(x, y, 1.0, 1.0);
  uvs = (gl_Position.xy + 1.0) * 0.5;

#if SMAA_STAGE == 0

  SMAAEdgeDetectionVS(uvs, offset);

#elif SMAA_STAGE == 1
  SMAABlendingWeightCalculationVS(uvs, pixcoord, offset);
#elif SMAA_STAGE == 2
  SMAANeighborhoodBlendingVS(uvs, offset[0]);
#endif
}
"""

smaa_frag = """

in vec2 uvs;
in vec2 pixcoord;
in vec4 offset[3];

uniform sampler2D colorTex;
uniform sampler2D edgesTex;
uniform sampler2D areaTex;
uniform sampler2D searchTex;
uniform sampler2D blendTex;

out vec2 out_edges;
out vec4 out_weights;
out vec4 out_color;

void main()
{
#if SMAA_STAGE == 0
  /* Detect edges in color and revealage buffer. */
  out_edges = SMAALumaEdgeDetectionPS(uvs, offset, colorTex);
  /* Discard if there is no edge. */
  if (dot(out_edges, float2(1.0, 1.0)) == 0.0) {
    discard;
  }

#elif SMAA_STAGE == 1
  out_weights = SMAABlendingWeightCalculationPS(
      uvs, pixcoord, offset, edgesTex, areaTex, searchTex, vec4(0));

#elif SMAA_STAGE == 2
  
  out_color = SMAANeighborhoodBlendingPS(uvs, offset[0], colorTex, blendTex);
#endif
}
"""

lib = """

uniform vec4 viewportMetrics;

"""

import os
smaa_lib = ""
with open(os.path.join(os.path.dirname(__file__), "common_smaa_lib.glsl"), 'r') as file:
    smaa_lib = file.read()

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

defines = """

#define SMAA_GLSL_4
#define SMAA_RT_METRICS viewportMetrics
#define SMAA_PRESET_ULTRA
#define SMAA_LUMA_WEIGHT float4(1.0, 1.0, 1.0, 1.0)
#define SMAA_NO_DISCARD

"""
d = defines + """

#define SMAA_STAGE 0

"""

smaa_stage_0 = gpu.types.GPUShader(
    vertexcode=smaa_vert,
    fragcode=smaa_frag,
    defines=d + lib + smaa_lib,
    name="smaa_stage_0",
)
d = defines + """

#define SMAA_STAGE 1

"""

smaa_stage_1 = gpu.types.GPUShader(
    vertexcode=smaa_vert,
    fragcode=smaa_frag,
    defines=d + lib + smaa_lib,
    name="smaa_stage_1",
)
d = defines + """

#define SMAA_STAGE 2

"""

smaa_stage_2 = gpu.types.GPUShader(
    vertexcode=smaa_vert,
    fragcode=smaa_frag,
    defines=d + lib + smaa_lib,
    name="smaa_stage_2",
)

vfmt = gpu.types.GPUVertFormat()
vfmt.attr_add(id="aPosition", comp_type='I8', len=2, fetch_mode='INT')

vbo = gpu.types.GPUVertBuf(
    len=4,
    format=vfmt)

post_fx_batch = gpu.types.GPUBatch(
    type='TRI_FAN',
    buf=vbo,
)


# batch_for_shader(bhqab.gpu_extras.shader.smaa_edges, 'TRI_FAN',
#                                 dict(aPosition=((-1, -1), (1, -1), (1, 1), (-1, 1))))
