precision highp float;

in vec2 v_pos;
in vec2 v_pixcoord;
in vec4 v_offset[3];

uniform sampler2D colorTex;
uniform sampler2D edgesTex;
uniform sampler2D areaTex;
uniform sampler2D searchTex;
uniform sampler2D blendTex;
uniform sampler2D predicationTex;

out vec2 out_edges;
out vec4 out_weights;
out vec4 out_color;

void main()
{
#if SMAA_STAGE == 0
  /* Detect edges in color and revealage buffer. */
  out_edges = SMAALumaEdgeDetectionPS(v_pos, v_offset, colorTex);

#elif SMAA_STAGE == 1
  out_weights = SMAABlendingWeightCalculationPS(
      v_pos, v_pixcoord, v_offset, edgesTex, areaTex, searchTex, vec4(0));

#elif SMAA_STAGE == 2
  
  out_color = SMAANeighborhoodBlendingPS(v_pos, v_offset[0], colorTex, blendTex);
#endif
}
