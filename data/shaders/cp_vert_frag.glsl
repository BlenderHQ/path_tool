uniform sampler2D OriginalViewDepthMap;
uniform vec4 viewportMetrics;
uniform vec3 ColorControlElement;
uniform vec3 ColorActiveControlElement;

in flat int IsActive;
out vec4 FragColor;

void main()
{
	if (frag_depth_greater_biased(gl_FragCoord, OriginalViewDepthMap, viewportMetrics.zw)) {
		discard;
	}
	
	FragColor = vec4((IsActive == 0) ? ColorControlElement : ColorActiveControlElement, 1.0f);
}
