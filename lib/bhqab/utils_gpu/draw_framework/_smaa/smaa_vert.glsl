//! #version 460

// See ./__init__.py/SMAA/_eval_shaders(...):
//
//! #define SMAA_GLSL_4 1
//! #define SMAA_RT_METRICS u_ViewportMetrics
//! #define SMAA_STAGE 0 // Modify in debug purposes
//! #define SMAA_PRESET_ULTRA 1

//! #include "./smaa_lib.glsl"

// in vec2 P;
// in vec2 UV;

// out vec2 v_pos;
// out vec2 v_pixcoord;
// out vec4 v_offset[3];

void main()
{
    v_pos = UV;
    gl_Position = vec4(P, 1.0, 1.0);

#if SMAA_STAGE == 0
    SMAAEdgeDetectionVS(v_pos, v_offset);
#elif SMAA_STAGE == 1
    SMAABlendingWeightCalculationVS(v_pos, v_pixcoord, v_offset);
#elif SMAA_STAGE == 2
    SMAANeighborhoodBlendingVS(v_pos, v_offset[0]);
#endif
}
