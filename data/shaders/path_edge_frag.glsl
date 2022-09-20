precision highp float;

uniform sampler2D OriginalViewDepthMap;
uniform vec4 viewportMetrics;
uniform vec3 ColorPath;

out vec4 FragColor;

void main()
{
	if (frag_depth_greater_biased(gl_FragCoord, OriginalViewDepthMap, viewportMetrics.zw)) {
		discard;
	}

	FragColor = vec4(ColorPath, 1.0f);
}