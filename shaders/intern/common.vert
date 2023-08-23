#ifndef USE_GPU_SHADER_CREATE_INFO

in vec3 P;

layout(binding = 0, std140) uniform u_Params { CommonParams _u_Params; };
uniform mat4 ModelViewProjectionMatrix;

void main() { gl_Position = ModelViewProjectionMatrix * _u_Params.model_matrix * vec4(P, 1.0); }

#else

void main() { gl_Position = ModelViewProjectionMatrix * u_Params.model_matrix * vec4(P, 1.0); }

#endif
