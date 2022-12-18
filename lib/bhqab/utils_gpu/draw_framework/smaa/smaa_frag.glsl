//! #version 460

// See ./__init__.py/SMAA/_eval_shaders(...):
//
//! #define SMAA_GLSL_4 1
//! #define SMAA_RT_METRICS viewportMetrics
//! #define SMAA_STAGE 0 // Modify in debug purposes
//! #define SMAA_PRESET_ULTRA 1

//! #include "./smaa_lib.glsl"

in vec2 v_pos;
in vec2 v_pixcoord;
in vec4 v_offset[3];

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
    out_edges = SMAAColorEdgeDetectionPS(v_pos, v_offset, colorTex);
#elif SMAA_STAGE == 1
    out_weights = SMAABlendingWeightCalculationPS(v_pos, v_pixcoord, v_offset, edgesTex, areaTex, searchTex, vec4(0.0));
#elif SMAA_STAGE == 2
    out_color = SMAANeighborhoodBlendingPS(v_pos, v_offset[0], colorTex, blendTex);
#endif
}
