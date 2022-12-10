bool frag_depth_greater_biased(vec4 _fragCoord, sampler2D _depthMap, vec2 _viewRes)
{
    return (_fragCoord.z > texture(_depthMap, vec2(_fragCoord.xy / _viewRes)).r + 1e-5);
}
