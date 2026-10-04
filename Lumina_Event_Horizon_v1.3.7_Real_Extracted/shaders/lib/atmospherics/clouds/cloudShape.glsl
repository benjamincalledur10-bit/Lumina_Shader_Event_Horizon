#ifndef INCLUDE_LUMINA_CLOUD_SHAPE
#define INCLUDE_LUMINA_CLOUD_SHAPE

// Shared world-space shape: quality changes sampling/detail, never layer geometry.
const float cloudStretch = 64.0 / sqrt(float(LUMINA_CLOUD_SCALE) * 0.01);
const float cloudTallness = cloudStretch * 2.0;
const float cloudNarrowness = 1.0 / 131072.0;

float LuminaCloudNoise(vec3 p) {
    vec3 cell = floor(p);
    vec3 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    vec2 uv = (cell.xz + vec2(37.0, 17.0) * cell.y + f.xz + 0.5) / 128.0;
    float a = texture2DLod(noisetex, uv, 0.0).r;
    float b = texture2DLod(noisetex, uv + vec2(37.0, 17.0) / 128.0, 0.0).r;
    return mix(a, b, f.y);
}

// Periodic, independent seeds avoid inheriting large smooth patches from the
// loader's noise texture. The period agrees with the camera-coordinate wrapping.
vec3 LuminaCloudSeed(vec2 cell) {
    vec3 p = fract(vec3(mod(cell, 256.0).xyx) * vec3(0.1031, 0.1030, 0.0973));
    p += dot(p, p.yxz + 33.33);
    return fract((p.xxy + p.yzz) * p.zyx);
}

float LuminaCloudLobe(vec3 delta, vec3 radius) {
    vec3 q = delta / radius;
    return max(1.0 - dot(q, q), 0.0);
}

float LuminaCloudShape(vec3 worldPos, int altitude, float horizontalDistance, bool detail) {
    float h = (worldPos.y - (float(altitude) - cloudStretch)) / cloudTallness;
    if (h <= 0.0 || h >= 1.0) return 0.0;
    #if CLOUD_SPEED_MULT == 100
        float cloudTime = syncedTime;
    #else
        float cloudTime = frameTimeCounter * (float(CLOUD_SPEED_MULT) * 0.01);
    #endif
    float scale = float(LUMINA_CLOUD_SCALE) * 0.01;
    vec2 horizontal = (worldPos.xz - vec2(0.7, 0.24) * cloudTime) * scale;
    vec2 cell = floor(horizontal / 512.0);
    float coverage = clamp(0.48 + 0.30 * (float(LUMINA_CLOUD_COVERAGE) - 1.0)
                         + 0.55 * float(LUMINA_CLOUD_RAIN_DENSITY) * rainFactor, 0.10, 0.98);
    vec3 p = vec3(horizontal.x, h * 128.0, horizontal.y) / 32.0;
    vec3 warp = (vec3(LuminaCloudNoise(p), LuminaCloudNoise(p + vec3(19.0, 7.0, 3.0)),
                     LuminaCloudNoise(p + vec3(5.0, 13.0, 23.0))) - 0.5) * 28.0;
    float shape = 0.0;
    // Separate cloud clusters with a flattened underside and overlapping crowns.
    // Neighbouring cells are necessary to keep moving clouds continuous at seams.
    for (int x = -1; x <= 1; x++) for (int z = -1; z <= 1; z++) {
        vec2 tile = cell + vec2(float(x), float(z));
        vec3 seed = LuminaCloudSeed(tile);
        float activation = smoothstep(seed.z, seed.z + 0.10, coverage);
        if (activation <= 0.0) continue;
        vec2 center = (tile + 0.22 + seed.xy * 0.56) * 512.0;
        vec2 deltaXZ = horizontal + warp.xz - center;
        float radius = mix(105.0, 185.0, seed.x) * (0.85 + coverage * 0.45);
        float crown = mix(0.36, 0.58, seed.y);
        vec3 delta = vec3(deltaXZ.x, (h - crown) * 128.0 + warp.y, deltaXZ.y);
        float body = LuminaCloudLobe(delta, vec3(radius, 34.0, radius * 0.82));
        body = max(body, LuminaCloudLobe(delta - vec3(radius * 0.35, 24.0, radius * 0.12),
                                       vec3(radius * 0.48, 42.0, radius * 0.47)));
        body = max(body, LuminaCloudLobe(delta - vec3(-radius * 0.38, 13.0, -radius * 0.22),
                                       vec3(radius * 0.52, 37.0, radius * 0.48)));
        shape = max(shape, body * activation);
    }
    if (shape <= 0.0) return 0.0;
    float erosion = LuminaCloudNoise(p);
    #if CLOUD_QUALITY >= 2
        if (detail) {
            float small = LuminaCloudNoise(p * 2.0 + vec3(5.0, 9.0, 1.0));
            #if CLOUD_QUALITY >= 3
                small = small * 0.65 + LuminaCloudNoise(p * 4.0) * 0.35;
            #endif
            erosion = mix(erosion, erosion * 0.65 + small * 0.35,
                          1.0 - smoothstep(1600.0, 3600.0, horizontalDistance));
        }
    #endif
    // Remove wispy edges rather than turning the whole slab into opaque haze.
    float density = max(shape - (1.0 - erosion) * 0.26 * (1.0 - shape), 0.0);
    float base = smoothstep(0.0, 0.10, h);
    return clamp(density * base * 1.25, 0.0, 1.0);
}
#endif
