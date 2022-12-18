//! #version 460
//! #include "common_lib.glsl"

uniform sampler2D OriginalViewDepthMap;
uniform vec4 viewportMetrics;
uniform vec4 ColorControlElement;
uniform vec4 ColorActiveControlElement;

in flat int IsActive;
in vec2 v_coord;
out vec4 FragColor;

void main()
{
	if (frag_depth_greater_biased(gl_FragCoord, OriginalViewDepthMap, viewportMetrics.zw)) {
		discard;
	}
	
	FragColor = ((IsActive == 0) ? ColorControlElement : ColorActiveControlElement);
	FragColor.a = distance(v_coord, gl_FragCoord.xy);
}
