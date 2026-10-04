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

float LuminaCloudShape(vec3 worldPos, int altitude, float horizontalDistance, bool detail) {
    float h = (worldPos.y - (float(altitude) - cloudStretch)) / cloudTallness;
    if (h <= 0.0 || h >= 1.0) return 0.0;
    #if CLOUD_SPEED_MULT == 100
        float cloudTime = syncedTime;
    #else
        float cloudTime = frameTimeCounter * (float(CLOUD_SPEED_MULT) * 0.01);
    #endif
    vec2 wind = vec2(0.7, 0.24) * cloudTime;
    vec2 horizontal = (worldPos.xz - wind) * (float(LUMINA_CLOUD_SCALE) * 0.01) / 256.0;
    vec3 p = vec3(horizontal.x, h * 2.0, horizontal.y);
    float weather = LuminaCloudNoise(vec3(horizontal.x * 0.25, 0.0, horizontal.y * 0.25));
    float coverage = clamp(0.50 + 0.24 * (float(LUMINA_CLOUD_COVERAGE) - 1.0)
                         + 0.35 * float(LUMINA_CLOUD_RAIN_DENSITY) * rainFactor
                         + 0.28 * (weather - 0.5), 0.10, 0.95);
    float base = 0.55 * LuminaCloudNoise(p) + 0.30 * LuminaCloudNoise(p * 2.0 + vec3(11.0, 3.0, 7.0))
               + 0.15 * LuminaCloudNoise(p * 4.0 + vec3(7.0, 13.0, 3.0));
    // Rounded crowns and a flatter, soft base; empty regions remain genuinely empty.
    float heightProfile = smoothstep(0.0, 0.10, h) * (1.0 - smoothstep(0.48, 1.0, h));
    float body = max((base - (1.0 - coverage)) / coverage, 0.0);
    #if CLOUD_QUALITY >= 2
        if (detail && body > 0.0) {
            float erosion = LuminaCloudNoise(p * 8.0 + vec3(5.0, 9.0, 1.0));
            #if CLOUD_QUALITY >= 3
                erosion = erosion * 0.70 + LuminaCloudNoise(p * 16.0) * 0.30;
            #endif
            float detailFade = 1.0 - smoothstep(1200.0, 3600.0, horizontalDistance);
            body = max(body - (1.0 - erosion) * 0.16 * detailFade * (1.0 - body), 0.0);
        }
    #endif
    return clamp(body * heightProfile * 2.0, 0.0, 1.0);
}
#endif
