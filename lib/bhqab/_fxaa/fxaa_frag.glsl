precision highp float;

uniform sampler2D image;
uniform vec4 viewportMetrics;

noperspective in vec2 v_pos;

out vec4 color;

void main()
{
    color = FxaaPixelShader(
        v_pos,
        image,
        viewportMetrics.xy,
        0.75,
        0.063,
        0.0312
    );
}