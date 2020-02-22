uniform vec4 color;
uniform vec4 color_active;

#ifdef USE_CLIP_PLANES
uniform bool use_clip_planes;
in vec4 clip_distance;
#endif

flat in int is_active_vert;
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
	if (is_active_vert == 1) {
		fragColor = linearrgb_to_srgb(color_active);
	}
	else {
		fragColor = linearrgb_to_srgb(color);
	}
}
