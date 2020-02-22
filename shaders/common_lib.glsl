float linearrgb_to_srgb(float c) {
    if (c < 0.0031308) {
        return (c < 0.0) ? 0.0 : c * 12.92;
    }
    else {
        return 1.055 * pow(c, 1.0 / 2.4) - 0.055;
    }
}

vec4 linearrgb_to_srgb(vec4 col_from) {
    // Convert color from linear to sRGB
    return vec4(
    linearrgb_to_srgb(col_from.r),
    linearrgb_to_srgb(col_from.g),
    linearrgb_to_srgb(col_from.b),
    col_from.a);
}