#ifndef LUMINA_CLOUD_DENSITY_INCLUDED
#define LUMINA_CLOUD_DENSITY_INCLUDED

// Geometry and advection are identical for sky, reflections and ground shadows.
const float cloudStretch = 48.0;
const float cloudTallness = cloudStretch * 2.0;
const float cloudNarrowness = 0.00012;

float GetLuminaCloudDensity(vec3 worldPos, int cloudAltitude, float horizontalDistance, float playerHeight) {
    float height = (worldPos.y - (float(cloudAltitude) - cloudStretch)) / cloudTallness;
    if (height <= 0.0 || height >= 1.0) return -1.0;
    vec3 p = worldPos * cloudNarrowness * (float(LUMINA_CLOUD_SCALE) * 0.01);
    #if CLOUD_SPEED_MULT == 100
        float time = syncedTime;
    #else
        float time = frameTimeCounter * (float(CLOUD_SPEED_MULT) * 0.01);
    #endif
    p.z -= time * 0.0006 * (float(LUMINA_CLOUD_SCALE) * 0.01);

    // A broad weather field leaves open sky between independent cloud groups.
    float weather = texture2DLod(noisetex, p.xz * 0.25, 0.0).b * 0.65
                  + texture2DLod(noisetex, p.xz * 0.5 + vec2(0.31, 0.17), 0.0).b * 0.35;
    float threshold = clamp(0.48 + (LUMINA_CLOUD_SEPARATION - 1.0) * 0.12
                          - (LUMINA_CLOUD_COVERAGE - 1.0) * 0.18
                          - LUMINA_CLOUD_RAIN_DENSITY * rainFactor * 0.2, 0.2, 0.7);
    float formation = smoothstep(threshold, threshold + 0.22, weather);
    if (formation < 0.025) return -1.0;

    // Three-dimensional billows replace the vertically extruded 2D layers.
    p.y *= 2.0;
    float broad = Noise3D(p * 0.5);
    float billows = Noise3D(p + vec3(0.13, 0.37, 0.29));
    float shape = broad * 0.68 + billows * 0.32;
    #if CLOUD_QUALITY >= 2
        shape = shape * 0.88 + Noise3D(p * 2.0 + vec3(0.41, 0.23, 0.11)) * 0.12;
    #endif
    float top = mix(0.68, 0.98, smoothstep(0.25, 0.75, broad));
    float envelope = smoothstep(0.02, 0.18, height) * (1.0 - smoothstep(top - 0.35, top, height));
    float density = (shape - 0.32 - (1.0 - formation) * 0.2) * envelope;
    #if CLOUD_QUALITY >= 2
        float erosion = Noise3D(p * 4.0 + vec3(0.17, 0.43, 0.29));
        float detailFade = 1.0 - smoothstep(1200.0, 3600.0, horizontalDistance);
        density -= erosion * 0.04 * (1.0 - envelope * 0.5) * detailFade;
    #endif
    return density * formation * (1.0 + LUMINA_CLOUD_RAIN_DENSITY * rainFactor);
}
#endif
