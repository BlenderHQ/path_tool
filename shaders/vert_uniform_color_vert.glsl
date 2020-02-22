uniform mat4 ModelViewProjectionMatrix;
uniform mat4 ModelMatrix;
uniform int active_index;

#ifdef USE_CLIP_PLANES
uniform mat4 ModelViewMatrix;
uniform bool use_clip_planes;
uniform vec4 clip_plane[4];
out vec4 clip_distance;
#endif

in vec3 pos;
flat out int is_active_vert;

void main()
{
#ifdef USE_CLIP_PLANES
	if (use_clip_planes) {
		vec4 g_pos = ModelViewMatrix * vec4(pos, 1.0);

		for (int i = 0; i != 4; i++) {
			clip_distance[i] = dot(clip_plane[i], g_pos);
		}
	}
#endif
	is_active_vert = 0;
	if (gl_VertexID == active_index) {
		is_active_vert = 1;
	}
	gl_Position = ModelViewProjectionMatrix * ModelMatrix * vec4(pos, 1.0);
}
