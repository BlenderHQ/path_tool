#define mad(a, b, c) (a * b + c)

in vec2 aPosition;

uniform vec2 resolution;

out vec2 vTexCoord0;
out vec4 vOffset[3];


void main() {
    vec4 SMAA_RT_METRICS = vec4(1.0 / resolution.x, 1.0 / resolution.y, resolution.x, resolution.y);

    vTexCoord0 = vec2((aPosition + 1.0) / 2.0);

    vOffset[0] = (SMAA_RT_METRICS.xyxy * vec4(-1.0, 0.0, 0.0, -1.0) + vTexCoord0.xyxy);
    vOffset[1] = (SMAA_RT_METRICS.xyxy * vec4( 1.0, 0.0, 0.0,  1.0) + vTexCoord0.xyxy);
    vOffset[2] = (SMAA_RT_METRICS.xyxy * vec4(-2.0, 0.0, 0.0, -2.0) + vTexCoord0.xyxy);

    gl_Position = vec4(aPosition, 0.0, 1.0);
}