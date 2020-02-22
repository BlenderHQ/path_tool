uniform vec4 color;

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
    fragColor = linearrgb_to_srgb(color);
}
