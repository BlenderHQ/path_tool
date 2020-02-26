uniform vec4 color;
uniform vec4 color_active;
uniform int active_index;

#ifdef USE_CLIP_PLANES
uniform bool use_clip_planes;
in vec4 clip_distance;
#endif

out vec4 fragColor;

void main()
{
#ifdef USE_CLIP_PLANES
	if (use_clip_planes &&
	   ((clip_distance[0] < 0) ||
	    (clip_distance[1] < 0) ||
	    (clip_distance[2] < 0) ||
	    (clip_distance[3] < 0)))
	{
		discard;
	}
#endif
	if (gl_PrimitiveID == active_index) {
		fragColor = linearrgb_to_srgb(color_active);
	}
	else {
		fragColor = linearrgb_to_srgb(color);
	}
}
