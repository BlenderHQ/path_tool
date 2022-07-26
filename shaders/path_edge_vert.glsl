in vec3 Coord;

uniform mat4 ModelViewProjectionMatrix;
uniform mat4 ModelMatrix;

void main()
{
	gl_Position = ModelViewProjectionMatrix * ModelMatrix * vec4(Coord, 1.0);
}
