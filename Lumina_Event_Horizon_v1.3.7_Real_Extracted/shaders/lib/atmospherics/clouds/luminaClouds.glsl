#if CLOUD_QUALITY == 1 || !defined DEFERRED1
    const float cloudStretchRaw = 20.0;
#elif CLOUD_QUALITY == 2
    const float cloudStretchRaw = 26.0;
#elif CLOUD_QUALITY == 3
    const float cloudStretchRaw = 32.0;
#endif
#if LUMINA_CLOUD_SCALE <= 100
    const float cloudStretch = cloudStretchRaw;
#else
    const float cloudStretch = cloudStretchRaw / float(LUMINA_CLOUD_SCALE_M);
#endif

#if CLOUD_QUALITY > 1
    const float cloudNarrowness = 0.00012;
#else
    const float cloudNarrowness = 0.00006;
#endif

const float cloudTallness = cloudStretch * 2.0;

float GetLuminaCloudDensity(vec3 tracePos, int cloudAltitude, float lTracePosXZ, float cloudPlayerPosY) {
    vec3 tracePosM = tracePos.xyz * cloudNarrowness;
    float wind = 0.0006;
    float noise = 0.0;
    float currentPersist = 1.0;
    float total = 0.0;

    #if CLOUD_SPEED_MULT == 100
        #define CLOUD_SPEED_MULT_M CLOUD_SPEED_MULT * 0.01
        wind *= syncedTime;
    #else
        #define CLOUD_SPEED_MULT_M CLOUD_SPEED_MULT * 0.01
        wind *= frameTimeCounter * CLOUD_SPEED_MULT_M;
    #endif
    #if LUMINA_CLOUD_SCALE != 100
        tracePosM *= LUMINA_CLOUD_SCALE_M;
        wind *= LUMINA_CLOUD_SCALE_M;
    #endif
    vec3 baseTracePosM = tracePosM;
    float baseWind = wind;

    #if CLOUD_QUALITY == 1
        int sampleCount = 4;
        float persistance = 0.55;
        float noiseMult = 1.05;
        wind *= 0.5;
    #elif CLOUD_QUALITY == 2 || !defined DEFERRED1
        int sampleCount = 5;
        float persistance = 0.55;
        float noiseMult = 1.20;
    #elif CLOUD_QUALITY == 3
        int sampleCount = 6;
        float persistance = 0.55;
        float noiseMult = 1.15;
    #endif

    #ifndef DEFERRED1
        noiseMult *= 1.2;
    #endif

    for (int i = 0; i < sampleCount; i++) {
        #if CLOUD_QUALITY >= 3
            noise += Noise3D(tracePosM - vec3(0.0, 0.0, wind)) * currentPersist;
        #else
            noise += texture2DLod(noisetex, tracePosM.xz - vec2(0.0, wind), 0.0).b * currentPersist;
        #endif
        total += currentPersist;

        tracePosM *= 3.0;
        wind *= 0.5;
        currentPersist *= persistance;
    }
    noise = pow(noise / total, 1.85);

    #define LUMINA_CLOUD_BASE_ADD 1.35
    #define LUMINA_CLOUD_ABOVE_ADD 0.1

    noiseMult *= LUMINA_CLOUD_BASE_ADD
                + LUMINA_CLOUD_ABOVE_ADD * clamp01(-cloudPlayerPosY / cloudTallness)
                + LUMINA_CLOUD_RAIN_DENSITY * rainFactor;
    noise *= noiseMult * LUMINA_CLOUD_COVERAGE;

    float normalizedHeight = clamp01((tracePos.y - (cloudAltitude - cloudStretch)) / cloudTallness);
    float threshold = clamp(abs(cloudAltitude - tracePos.y) / cloudStretch, 0.001, 0.999);
    threshold = pow2(pow2(pow2(threshold)));

    float cloudDensity = noise - (threshold * 0.3 + 0.22);
    #if CLOUD_QUALITY >= 2
        vec3 erosionPos = baseTracePosM * 2.35 + vec3(0.17, 0.43, 0.29);
        float erosion = Noise3D(erosionPos - vec3(0.0, 0.0, baseWind * 0.35)) - 0.5;
        float detailFade = 1.0 - smoothstep(1200.0, 3600.0, lTracePosXZ);
        cloudDensity += erosion * 0.10 * detailFade;

        float anvilShape = smoothstep(0.52, 0.82, normalizedHeight)
                         * (1.0 - smoothstep(0.82, 1.0, normalizedHeight));
        cloudDensity += anvilShape * 0.035;
    #endif

    return cloudDensity;
}

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
        float stepMult = 64.0;
    #elif CLOUD_QUALITY == 1
        float stepMult = 54.0;
    #elif CLOUD_QUALITY == 2
        float stepMult = 48.0;
    #elif CLOUD_QUALITY == 3
        float stepMult = 32.0;
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
            #if defined CLOUD_CLOSED_AREA_CHECK && SHADOW_QUALITY > -1
                float shadowLength = shadowDistance * 0.9166667; //consistent08JJ622
                if (shadowLength > lTracePos)
                if (GetShadowOnCloud(tracePos, cameraPos, cloudAltitude, lowerPlaneAltitude, higherPlaneAltitude)) {
                    if (eyeBrightness.y != 240) continue;
                }
            #endif

            if (firstHitPos < 0.0) {
                firstHitPos = lTracePos;
                #if CLOUD_QUALITY == 1 && defined DEFERRED1
                    tracePos.y += 4.0 * (texture2DLod(noisetex, tracePos.xz * cloudNarrowness * 16.0, 0.0).r - 0.5);
                #endif
            }

            float opacityFactor = min1(cloudNoise * 8.0);
            float powderFactor = 1.0 - exp(-cloudNoise * 4.0);

            float cloudShading = 1.0 - (higherPlaneAltitude - tracePos.y) / cloudTallness;
            cloudShading = pow(max0(cloudShading), 1.2);
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

            volumetricClouds.rgb = mix(volumetricClouds.rgb, colorSample, 1.0 - min1(volumetricClouds.a));
            volumetricClouds.a += opacityFactor * pow(cloudDistanceFactor, 0.5 + 10.0 * pow(abs(VdotSM1M), 90.0)) * cloudMult;

            if (volumetricClouds.a > 0.9) {
                volumetricClouds.a = 1.0;
                break;
            }
        }
    }

    if (volumetricClouds.a > 0.5) cloudLinearDepth = sqrt(firstHitPos / renderDistance);

    return volumetricClouds;
}
