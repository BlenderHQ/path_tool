#ifndef USE_GPU_SHADER_CREATE_INFO

layout(binding = 0, std140) uniform _u_Params { CommonParams u_Params; };

uniform mat4 ModelViewProjectionMatrix;
uniform vec4 u_ViewportMetrics;

out flat int g_IsActive;
out vec2 g_CenterScreen;

#endif

/* Disk R=1 triangle strip */
const vec2 _DiskR1Coord[] = vec2[](
    /*    X/U         Y/V            Index */
    vec2(0.000000f, 1.000000f),   // 0
    vec2(0.500000f, 0.866025f),   // 11
    vec2(-0.500000f, 0.866025f),  // 1
    vec2(0.866025f, 0.500000f),   // 10
    vec2(-0.866025f, 0.500000f),  // 2
    vec2(1.000000f, 0.000000f),   // 9
    vec2(-1.000000f, 0.000000f),  // 3
    vec2(0.866025f, -0.500000f),  // 8
    vec2(-0.866025f, -0.500000f), // 4
    vec2(0.500000f, -0.866025f),  // 7
    vec2(-0.500000f, -0.866025f), // 5
    vec2(0.000000f, -1.000000f)   // 6
);

void main() {
  vec4 _Center = vec4(gl_in[0].gl_Position.xyz / gl_in[0].gl_Position.w, 1.0f);

  g_CenterScreen = 2.0 * (_Center.xy * u_ViewportMetrics.xy) - 1.0;

  g_IsActive = (gl_PrimitiveIDIn < u_Params.index_active) ? 0 : 1;

  for (int i = 0; i < 12; ++i) {
    gl_Position = _Center + vec4(_DiskR1Coord[i].xy * u_ViewportMetrics.xy * u_Params.point_size, 0.0f, 0.0f);
    EmitVertex();
  }

  EndPrimitive();
}
