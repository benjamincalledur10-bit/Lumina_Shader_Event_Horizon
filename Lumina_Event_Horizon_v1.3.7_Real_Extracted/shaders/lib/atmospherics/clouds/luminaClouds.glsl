#include "/lib/atmospherics/clouds/cloudDensity.glsl"

vec4 GetVolumetricClouds(int cloudAltitude, float distanceThreshold, inout float cloudLinearDepth, float skyFade, float skyMult0, vec3 cameraPos, vec3 nPlayerPos, float lViewPosM, float VdotS, float VdotU, float dither) {
    vec4 volumetricClouds = vec4(0.0);

    float higherPlaneAltitude = cloudAltitude + cloudStretch;
    float lowerPlaneAltitude  = cloudAltitude - cloudStretch;

    float minPlaneDistance;
    float maxPlaneDistance;
    if (abs(nPlayerPos.y) < 0.0001) {
        if (cameraPos.y < lowerPlaneAltitude || cameraPos.y > higherPlaneAltitude) return vec4(0.0);
        minPlaneDistance = 0.0;
        maxPlaneDistance = distanceThreshold;
    } else {
        float lowerPlaneDistance  = (lowerPlaneAltitude - cameraPos.y) / nPlayerPos.y;
        float higherPlaneDistance = (higherPlaneAltitude - cameraPos.y) / nPlayerPos.y;
        minPlaneDistance = max(min(lowerPlaneDistance, higherPlaneDistance), 0.0);
        maxPlaneDistance = max(lowerPlaneDistance, higherPlaneDistance);
    }
    if (maxPlaneDistance < 0.0) return vec4(0.0);

    // Clip the ray interval before deriving the sample spacing. Without this,
    // almost-horizontal rays can span an enormous distance and the first
    // capped sample can jump beyond the cloud render distance.
    float horizontalDirectionLength = length(nPlayerPos.xz);
    if (horizontalDirectionLength > 0.0001) {
        maxPlaneDistance = min(maxPlaneDistance, distanceThreshold / horizontalDirectionLength);
    }

    float planeDistanceDif = maxPlaneDistance - minPlaneDistance;
    if (planeDistanceDif <= 0.0) return vec4(0.0);

    #ifndef DEFERRED1
        float stepMult = 32.0;
    #elif CLOUD_QUALITY == 1
        float stepMult = 24.0;
    #elif CLOUD_QUALITY == 2
        float stepMult = 14.0;
    #elif CLOUD_QUALITY == 3
        float stepMult = 8.0;
    #endif

    #if LUMINA_CLOUD_SCALE > 100
        stepMult = stepMult / sqrt(float(LUMINA_CLOUD_SCALE_M));
    #endif

    int sampleCount = min(int(planeDistanceDif / stepMult + dither + 1), 128);

    #ifdef FIX_AMD_REFLECTION_CRASH
        sampleCount = min(sampleCount, 30); // BFARC
    #endif

    stepMult = planeDistanceDif / float(max(sampleCount, 1));
    vec3 traceAdd = nPlayerPos * stepMult;
    vec3 tracePos = cameraPos + minPlaneDistance * nPlayerPos;
    tracePos += traceAdd * dither;
    tracePos.y -= traceAdd.y;

    float firstHitPos = -1.0;
    float VdotSM1 = max0(sunVisibility > 0.5 ? VdotS : - VdotS);
    float VdotSM1M = VdotSM1 * invRainFactor;
    float VdotSM2 = pow2(VdotSM1) * abs(sunVisibility - 0.5) * 2.0;
    float VdotSM3 = VdotSM2 * (2.5 + rainFactor) + 1.5 * rainFactor;
    float VdotSM4 = pow(VdotSM1M, 100.0) * sunVisibility;

    for (int i = 0; i < sampleCount; i++) {
        tracePos += traceAdd;

        if (abs(tracePos.y - cloudAltitude) > cloudStretch) break;

        vec3 cloudPlayerPos = tracePos - cameraPos;
        float lTracePos = length(cloudPlayerPos);
        float lTracePosXZ = length(cloudPlayerPos.xz);
        float cloudMult = 1.0;
        if (lTracePosXZ > distanceThreshold) break;
        if (lTracePos > lViewPosM) {
            if (skyFade < 0.7) continue;
            else cloudMult = skyMult0;
        }

        float cloudNoise = GetLuminaCloudDensity(tracePos, cloudAltitude, lTracePosXZ, cloudPlayerPos.y);

        if (cloudNoise > 0.00001) {
            #ifdef CLOUD_CLOSED_AREA_CHECK
                #if SHADOW_QUALITY > -1
                    float shadowLength = shadowDistance * 0.9166667; //consistent08JJ622
                    if (shadowLength > lTracePos)
                    if (GetShadowOnCloud(tracePos, cameraPos, cloudAltitude, lowerPlaneAltitude, higherPlaneAltitude)) {
                        if (eyeBrightness.y != 240) continue;
                    }
                #endif
            #endif

            if (firstHitPos < 0.0) {
                firstHitPos = lTracePos;
            }

            float opacityFactor = 1.0 - exp(-max0(cloudNoise) * stepMult * 0.08);
            float powderFactor = 1.0 - exp(-cloudNoise * 4.0);

            float cloudShading = 1.0 - (higherPlaneAltitude - tracePos.y) / cloudTallness;
            cloudShading = pow(max0(cloudShading), 1.2);
            cloudShading *= exp(-max0(cloudNoise) * 2.5);
            float scattering = pow(VdotSM1, 6.0) * (1.0 - opacityFactor) * 2.0 * powderFactor;
            cloudShading *= 1.0 + 0.3 * VdotSM3 * (1.0 - opacityFactor) + VdotSM4 + scattering;

            float silverLining = exp(-cloudNoise * 18.0) * pow(VdotSM1, 8.0) * invRainFactor;

            vec3 colorSample = cloudAmbientColor * (0.35 + 0.65 * cloudShading) + cloudLightColor * cloudShading;
            colorSample += cloudLightColor * scattering * 0.5;
            colorSample += cloudLightColor * silverLining * 0.65;
            vec3 cloudSkyColor = GetSky(VdotU, VdotS, dither, isEyeInWater == 0, false);
            #ifdef ATM_COLOR_MULTS
                cloudSkyColor *= sqrtAtmColorMult; // C72380KD - Reduced atmColorMult impact on some things
            #endif
            float distanceRatio = (distanceThreshold - lTracePosXZ) / distanceThreshold;
            float cloudDistanceFactor = clamp(distanceRatio, 0.0, 0.8) * 1.25;
            float cloudFogFactor = pow2(pow1_5(clamp(distanceRatio, 0.0, 1.0)));
            float skyMult1 = 1.0 - 0.2 * (1.0 - skyFade) * max(sunVisibility2, nightFactor);
            float skyMult2 = 1.0 - 0.33333 * skyFade;
            colorSample = mix(cloudSkyColor, colorSample * skyMult1, cloudFogFactor * skyMult2 * 0.72);
            colorSample *= pow2(1.0 - maxBlindnessDarkness);

            float sampleAlpha = clamp01(opacityFactor * pow(cloudDistanceFactor, 0.5 + 10.0 * pow(abs(VdotSM1M), 90.0)) * cloudMult);
            float contribution = (1.0 - volumetricClouds.a) * sampleAlpha;
            volumetricClouds.rgb += colorSample * contribution;
            volumetricClouds.a += contribution;

            if (volumetricClouds.a > 0.995) {
                break;
            }
        }
    }

    if (volumetricClouds.a > 0.0001) volumetricClouds.rgb /= volumetricClouds.a;

    if (volumetricClouds.a > 0.5) cloudLinearDepth = sqrt(firstHitPos / renderDistance);

    return volumetricClouds;
}
