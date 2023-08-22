#pragma BHQGLSL_REQUIRE(mask_fragment_stage)

void main() {
  if (frag_depth_greater_biased(u_DepthMap, u_ViewportMetrics.zw)) {
    discard;
  }

  f_Color = ((gl_PrimitiveID < u_Params.index_active) ? u_Params.color_cp : u_Params.color_active_cp);
}