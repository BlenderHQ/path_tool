precision highp float;

in vec2 pos;
in vec2 texCoord;

out vec2 v_pos;
out vec2 v_pixcoord;
out vec4 v_offset[3];

void main()
{
  gl_Position = vec4(pos, 1.0, 1.0);
  v_pos = texCoord;

#if SMAA_STAGE == 0
  SMAAEdgeDetectionVS(v_pos, v_offset);
#elif SMAA_STAGE == 1
  SMAABlendingWeightCalculationVS(v_pos, v_pixcoord, v_offset);
#elif SMAA_STAGE == 2
  SMAANeighborhoodBlendingVS(v_pos, v_offset[0]);
#endif
}
