//! #version 460
//! #include "common_lib.glsl"

uniform sampler2D OriginalViewDepthMap;
uniform vec4 viewportMetrics;
uniform vec4 ColorControlElement;
uniform vec4 ColorActiveControlElement;
uniform int ActiveControlElementIndex;

out vec4 FragColor;

void main()
{
	if (frag_depth_greater_biased(gl_FragCoord, OriginalViewDepthMap, viewportMetrics.zw)) {
		discard;
	}
	
	FragColor = ((gl_PrimitiveID < ActiveControlElementIndex) ? ColorControlElement : ColorActiveControlElement);
}