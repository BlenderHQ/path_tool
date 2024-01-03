#ifndef USE_GPU_SHADER_CREATE_INFO
layout(binding = 0, std140) uniform u_Params { CommonParams _u_Params; };
uniform mat4 ModelViewProjectionMatrix;
uniform vec4 u_ViewportMetrics;
out flat int g_IsActive;
#endif
const vec2 _DiskR1Coord[] = vec2[](
vec2(0.000000f, 1.000000f),
vec2(0.500000f, 0.866025f),
vec2(-0.500000f, 0.866025f),
vec2(0.866025f, 0.500000f),
vec2(-0.866025f, 0.500000f),
vec2(1.000000f, 0.000000f),
vec2(-1.000000f, 0.000000f),
vec2(0.866025f, -0.500000f),
vec2(-0.866025f, -0.500000f),
vec2(0.500000f, -0.866025f),
vec2(-0.500000f, -0.866025f),
vec2(0.000000f, -1.000000f)
);
void main() {
vec4 _Center = vec4(gl_in[0].gl_Position.xyz / gl_in[0].gl_Position.w, 1.0f);
g_IsActive = (gl_PrimitiveIDIn < _u_Params.index_active) ? 0 : 1;
for (int i = 0; i < 12; ++i) {
gl_Position = _Center + vec4(_DiskR1Coord[i].xy * u_ViewportMetrics.xy * _u_Params.point_size, 0.0f, 0.0f);
EmitVertex();
}
EndPrimitive();
}