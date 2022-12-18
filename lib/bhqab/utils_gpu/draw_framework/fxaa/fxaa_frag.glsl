//! #version 460
//
// See ./__init__.py/SMAA/_eval_shaders(...):
//
//! #define FXAA_QUALITY__PRESET 39 // See ./__init__.py/SMAA/__quality_preset__:
//! #include "fxaa_lib.glsl"

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
