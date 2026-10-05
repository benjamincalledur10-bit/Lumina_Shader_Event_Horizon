#include "/lib/atmospherics/clouds/cloudShape.glsl"

float GetLuminaCloudDensity(vec3 tracePos, int cloudAltitude, float horizontalDistance, float relativeY) {
    #ifdef DEFERRED1
        return LuminaCloudShape(tracePos, cloudAltitude, horizontalDistance, true);
    #else
        return LuminaCloudShape(tracePos, cloudAltitude, horizontalDistance, false);
    #endif
}

vec4 GetVolumetricClouds(int cloudAltitude, float distanceThreshold, inout float cloudLinearDepth,
                       float skyFade, float skyMult0, vec3 cameraPos, vec3 nPlayerPos,
                       float lViewPosM, float VdotS, float VdotU, float dither) {
    float lowerPlaneAltitude = float(cloudAltitude) - cloudStretch;
    float higherPlaneAltitude = float(cloudAltitude) + cloudStretch;
    float startDistance = 0.0;
    float endDistance = distanceThreshold;
    if (abs(nPlayerPos.y) < 0.0001) {
        if (cameraPos.y <= lowerPlaneAltitude || cameraPos.y >= higherPlaneAltitude) return vec4(0.0);
    } else {
        float a = (lowerPlaneAltitude - cameraPos.y) / nPlayerPos.y;
        float b = (higherPlaneAltitude - cameraPos.y) / nPlayerPos.y;
        startDistance = max(min(a, b), 0.0);
        endDistance = max(a, b);
    }
    endDistance = min(endDistance, distanceThreshold / max(length(nPlayerPos.xz), 0.0001));
    if (skyFade < 0.7) endDistance = min(endDistance, lViewPosM);
    float interval = endDistance - startDistance;
    if (interval <= 0.0) return vec4(0.0);

    #ifndef DEFERRED1
        const int maxSamples = 16;
        const float targetStep = 16.0;
        const int lightSamples = 1;
    #elif CLOUD_QUALITY == 1
        const int maxSamples = 32;
        const float targetStep = 12.0;
        const int lightSamples = 1;
    #elif CLOUD_QUALITY == 2
        const int maxSamples = 64;
        const float targetStep = 6.0;
        const int lightSamples = 2;
    #else
        const int maxSamples = 80;
        const float targetStep = 4.0;
        const int lightSamples = 3;
    #endif
    int sampleCount = min(int(ceil(interval / targetStep)), maxSamples);
    #ifdef FIX_AMD_REFLECTION_CRASH
        sampleCount = min(sampleCount, 30);
    #endif
    float stepLength = interval / float(max(sampleCount, 1));
    vec3 worldLightDir = normalize(mat3(gbufferModelViewInverse) * lightVec);
    float forwardLight = max(mix(-VdotS, VdotS, smoothstep(0.35, 0.65, sunVisibility)), 0.0);
    float phase = 0.55 + pow(forwardLight, 8.0) * 0.85 * invRainFactor;
    vec3 skyColor = GetSky(VdotU, VdotS, dither, isEyeInWater == 0, false);
    vec3 accumulated = vec3(0.0);
    float transmittance = 1.0;
    float firstHit = -1.0;

    for (int i = 0; i < sampleCount; i++) {
        float rayDistance = startDistance + (float(i) + clamp(dither, 0.001, 0.999)) * stepLength;
        vec3 tracePos = cameraPos + nPlayerPos * rayDistance;
        float horizontalDistance = rayDistance * length(nPlayerPos.xz);
        float density = GetLuminaCloudDensity(tracePos, cloudAltitude, horizontalDistance, tracePos.y - cameraPos.y);
        if (density <= 0.00001) continue;
        #if defined CLOUD_CLOSED_AREA_CHECK && SHADOW_QUALITY > -1
            if (rayDistance < shadowDistance * 0.9166667 && eyeBrightness.y != 240)
                if (GetShadowOnCloud(tracePos, cameraPos, cloudAltitude, lowerPlaneAltitude, higherPlaneAltitude)) continue;
        #endif
        float opticalDepth = 0.055 * density * stepLength;
        float distanceFade = 1.0 - smoothstep(distanceThreshold * 0.65, distanceThreshold, horizontalDistance);
        float visibility = rayDistance > lViewPosM ? clamp(skyMult0, 0.0, 1.0) : 1.0;
        float sampleAlpha = (1.0 - exp(-opticalDepth)) * distanceFade * visibility;
        if (sampleAlpha <= 0.00001) continue;
        if (firstHit < 0.0) firstHit = rayDistance;

        float sunOpticalDepth = 0.0;
        float lightDistance = 0.0;
        for (int j = 0; j < lightSamples; j++) {
            float lightStep = 16.0 * exp2(float(j));
            vec3 lightPos = tracePos + worldLightDir * (lightDistance + lightStep * 0.5);
            sunOpticalDepth += LuminaCloudShape(lightPos, cloudAltitude, horizontalDistance, false) * lightStep * 0.055;
            lightDistance += lightStep;
        }
        float sunlight = exp(-sunOpticalDepth);
        float height = clamp((tracePos.y - lowerPlaneAltitude) / cloudTallness, 0.0, 1.0);
        float ambientVisibility = 0.35 + 0.65 * height;
        float multipleScattering = 0.22 * (1.0 - exp(-density * 3.0)) * exp(-sunOpticalDepth * 0.25);
        vec3 sampleColor = cloudAmbientColor * ambientVisibility * 0.75
                         + cloudLightColor * (sunlight * phase + multipleScattering) * 0.70;
        float peak = max(sampleColor.r, max(sampleColor.g, sampleColor.b));
        sampleColor /= 1.0 + 0.12 * max(peak - 2.5, 0.0);
        float haze = 1.0 - exp(-horizontalDistance * 0.00035);
        sampleColor = mix(sampleColor, skyColor, haze);
        sampleColor *= pow2(1.0 - maxBlindnessDarkness);
        accumulated += transmittance * sampleAlpha * sampleColor;
        transmittance *= 1.0 - sampleAlpha;
        if (transmittance < 0.01) break;
    }
    float alpha = 1.0 - transmittance;
    if (alpha > 0.5 && firstHit >= 0.0) cloudLinearDepth = sqrt(firstHit / renderDistance);
    // Callers blend straight RGB with alpha; retain correct front-to-back energy.
    return vec4(accumulated / max(alpha, 0.00001), alpha);
}
