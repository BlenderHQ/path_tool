//! #version 460

in vec2 pos;
in vec2 texCoord;

uniform vec4 viewportMetrics;

noperspective out vec2 v_pos;

void main()
{
    gl_Position = vec4(pos, 1.0, 1.0);
    v_pos = texCoord;
}
