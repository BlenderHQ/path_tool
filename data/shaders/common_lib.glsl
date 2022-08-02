/* `_DEPTH_BIAS` may be overriden */
#ifndef _DEPTH_BIAS
    #define _DEPTH_BIAS 1e-5
#endif

bool frag_depth_greater_biased(vec4 _fragCoord, sampler2D _depthMap, vec2 _viewRes)
{
    return (_fragCoord.z > texture(_depthMap, vec2(_fragCoord.xy / _viewRes)).r + _DEPTH_BIAS);
}
