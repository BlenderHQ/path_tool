#pragma BHQGLSL_REQUIRE(mask_fragment_stage)
void main() {
if (frag_depth_greater_biased(u_DepthMap, u_ViewportMetrics.zw)) {
if (u_Params.show_path_behind) {
f_Color = u_Params.color_path_behind;
} else {
discard;
}
} else {
f_Color = u_Params.color_path;
}
}