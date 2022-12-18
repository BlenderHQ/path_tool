//! #version 460
//! #include "common_lib.glsl"

layout(points) in;
layout(triangle_strip, max_vertices = 12) out;

uniform mat4 ModelViewProjectionMatrix;
uniform mat4 ModelMatrix;

uniform vec4 viewportMetrics;
uniform int ActiveControlElementIndex;
uniform float DiskRadius;

out flat int IsActive;
out vec2 v_coord;

/* Disk R=1 triangle strip */
const vec2 _DiskR1Coord[] = vec2[](
    /*    X/U         Y/V            Index */
    vec2( 0.000000f,  1.000000f), // 0
    vec2( 0.500000f,  0.866025f), // 11
    vec2(-0.500000f,  0.866025f), // 1
    vec2( 0.866025f,  0.500000f), // 10
    vec2(-0.866025f,  0.500000f), // 2
    vec2( 1.000000f,  0.000000f), // 9
    vec2(-1.000000f,  0.000000f), // 3
    vec2( 0.866025f, -0.500000f), // 8
    vec2(-0.866025f, -0.500000f), // 4
    vec2( 0.500000f, -0.866025f), // 7
    vec2(-0.500000f, -0.866025f), // 5
    vec2( 0.000000f, -1.000000f)  // 6
);


void main()
{
    vec4 _Center = vec4(gl_in[0].gl_Position.xyz / gl_in[0].gl_Position.w, 1.0f);

    v_coord = (2.0 * (gl_in[0].gl_Position.xy / gl_in[0].gl_Position.w * viewportMetrics.xy) - 1.0);
    
    IsActive = (gl_PrimitiveIDIn < ActiveControlElementIndex) ? 0 : 1;
    
    for (int i = 0; i < 12; ++i) {
        gl_Position = _Center + vec4(_DiskR1Coord[i].xy * viewportMetrics.xy * DiskRadius, 0.0f, 0.0f);
        EmitVertex();
    }

    EndPrimitive();
}
