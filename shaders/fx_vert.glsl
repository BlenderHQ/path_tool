in vec2 Coord;

uniform mat4 ModelViewProjectionMatrix;
uniform vec2 ViewResolution;

out vec2 FragUV;


void main()
{
    gl_Position = ModelViewProjectionMatrix * vec4(Coord, 0.0f, 1.0f);
    FragUV = Coord;
}