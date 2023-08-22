#pragma BHQGLSL_REQUIRE(mask_fragment_stage)

#ifndef USE_GPU_SHADER_CREATE_INFO

layout(binding = 0, std140) uniform _u_Params { CommonParams u_Params; };
uniform vec4 u_ViewportMetrics;

uniform sampler2D u_DepthMap;

in flat int g_IsActive;
in vec2 g_CenterScreen;

out vec4 f_Color;

#endif

void main() {
  if (frag_depth_greater_biased(u_DepthMap, u_ViewportMetrics.zw)) {
    discard;
  }

  f_Color = ((g_IsActive == 0) ? u_Params.color_cp : u_Params.color_active_cp);
  f_Color.a = distance(g_CenterScreen, gl_FragCoord.xy);
}
