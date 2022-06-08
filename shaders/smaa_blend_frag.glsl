precision highp float;

#define mad(a, b, c) (a * b + c)

uniform sampler2D colorTex;
uniform sampler2D blendTex;

uniform vec2 resolution;

in vec2 vTexCoord0;
in vec4 vOffset;

out vec4 FragColor;

vec4 SMAA_RT_METRICS = vec4(1.0 / resolution.x, 1.0 / resolution.y, resolution.x, resolution.y);

/**
 * Conditional move:
 */
void SMAAMovc(bvec2 cond, inout vec2 variable, vec2 value) {
  if (cond.x) variable.x = value.x;
  if (cond.y) variable.y = value.y;
}

void SMAAMovc(bvec4 cond, inout vec4 variable, vec4 value) {
  SMAAMovc(cond.xy, variable.xy, value.xy);
  SMAAMovc(cond.zw, variable.zw, value.zw);
}

void main() {
  vec4 color;

  // Fetch the blending weights for current pixel:
  vec4 a;
  a.x = texture2D(blendTex, vOffset.xy).a; // Right
  a.y = texture2D(blendTex, vOffset.zw).g; // Top
  a.wz = texture2D(blendTex, vTexCoord0).xz; // Bottom / Left

  // Is there any blending weight with a value greater than 0.0?
  if (dot(a, vec4(1.0, 1.0, 1.0, 1.0)) <= 1e-5) {
    color = texture2D(colorTex, vTexCoord0); // LinearSampler
  } else {
    bool h = max(a.x, a.z) > max(a.y, a.w); // max(horizontal) > max(vertical)

    // Calculate the blending offsets:
    vec4 blendingOffset = vec4(0.0, a.y, 0.0, a.w);
    vec2 blendingWeight = a.yw;
    SMAAMovc(bvec4(h, h, h, h), blendingOffset, vec4(a.x, 0.0, a.z, 0.0));
    SMAAMovc(bvec2(h, h), blendingWeight, a.xz);
    blendingWeight /= dot(blendingWeight, vec2(1.0, 1.0));

    // Calculate the texture coordinates:
    vec4 blendingCoord = mad(blendingOffset, vec4(SMAA_RT_METRICS.xy, -SMAA_RT_METRICS.xy), vTexCoord0.xyxy);

    // We exploit bilinear filtering to mix current pixel with the chosen
    // neighbor:
    color = blendingWeight.x * texture2D(colorTex, blendingCoord.xy); // LinearSampler
    color += blendingWeight.y * texture2D(colorTex, blendingCoord.zw); // LinearSampler
  }

  FragColor = color;
}