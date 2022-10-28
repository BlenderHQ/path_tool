precision highp float;

uniform sampler2D OriginalViewDepthMap;
uniform vec4 viewportMetrics;
uniform vec4 ColorPath;

out vec4 FragColor;

void main()
{
	if (frag_depth_greater_biased(gl_FragCoord, OriginalViewDepthMap, viewportMetrics.zw + 1e-5)) {
		discard;
	}

	FragColor = ColorPath;
}
