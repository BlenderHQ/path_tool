#pragma BHQGLSL_REQUIRE(mask_fragment_stage)

void main() {
  if (frag_depth_greater_biased(u_DepthMap, u_ViewportMetrics.zw)) {
    discard;
  }

  f_Color = u_Params.color_path;
}
