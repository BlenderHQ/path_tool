uniform mat4 ModelViewProjectionMatrix;

uniform vec4 color;
uniform vec4 color_active;
uniform int active_index;

out vec4 fragColor;

void main()
{
	// 'linearrgb_to_srgb' defined in './common_lib.glsl'
	if (gl_PrimitiveID >= active_index) {
		fragColor = linearrgb_to_srgb(color_active);
	}
	else {
		fragColor = linearrgb_to_srgb(color);
	}
}
