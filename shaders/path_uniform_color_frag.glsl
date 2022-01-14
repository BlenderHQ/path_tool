uniform vec4 color;
out vec4 fragColor;

void main()
{
	// 'linearrgb_to_srgb' defined in './common_lib.glsl'
	fragColor = linearrgb_to_srgb(color);
}
