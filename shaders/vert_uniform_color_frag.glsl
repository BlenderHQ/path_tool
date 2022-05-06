uniform mat4 ModelViewProjectionMatrix;

uniform vec3 color;
uniform vec3 color_active;
uniform int active_index;

out vec4 fragColor;

void main()
{
	if (gl_PrimitiveID >= active_index) {
		fragColor = vec4(color_active, 1.0f);
	}
	else {
		fragColor = vec4(color, 1.0f);
	}
}
