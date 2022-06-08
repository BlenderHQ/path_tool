in vec2 UVs;

uniform sampler2D colorTex;
uniform vec4 viewportMetrics;

out vec4 FragColor;

void main()
{
    FragColor = texture(colorTex, UVs);

    // if (FragColor.a == 0.0) {
        
    //     float f = 0.5;

    //     for (int i = -1; i < 2; ++i) {
    //         for (int j = -1; j < 2; ++j) {
    //             float a = texture(colorTex, UVs + vec2(viewportMetrics.x * i * f, viewportMetrics.y * j * f)).a;
    //             if (a > 0.0) {
    //                 FragColor = vec4(0.0, 0.0, 0.0, 1);
    //                 break;
    //             }
    //         }
    //     }
    // }
}