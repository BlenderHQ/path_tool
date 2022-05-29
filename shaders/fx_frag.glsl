in vec2 FragUV;

uniform sampler2D ViewOverlay;
uniform vec2 ViewResolution;

out vec4 FragColor;

void main()
{
    FragColor = texture(ViewOverlay, FragUV);

    /* Outline */
    if (FragColor.a == 0.0f) {
        for (int i = -1; i < 2; ++i) {
            for (int j = -1; j < 2; ++j) {
                if (texture(ViewOverlay, FragUV + vec2((1.0 / ViewResolution.x) * i, (1.0 / ViewResolution.y) * j)).r > 0.0f) {
                    FragColor = vec4(0.0, 0.0, 0.0, 1.0);
                }
            }
        }
    }
}