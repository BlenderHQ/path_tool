uniform mat4 ModelViewProjectionMatrix;
uniform mat4 ModelMatrix;

in vec3 pos;

void main()
{
	gl_Position = ModelViewProjectionMatrix * ModelMatrix * vec4(pos, 1.0);
}
