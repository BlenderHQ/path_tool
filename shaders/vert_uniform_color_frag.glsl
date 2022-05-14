uniform mat4 ModelViewProjectionMatrix;

uniform vec3 color;
uniform vec3 colorActive;
uniform int activeIndex;

out vec4 fragColor;

void main()
{
	if (gl_PrimitiveID >= activeIndex) {
		fragColor = vec4(colorActive, 1.0f);
	}
	else {
		fragColor = vec4(color, 1.0f);
	}
}
