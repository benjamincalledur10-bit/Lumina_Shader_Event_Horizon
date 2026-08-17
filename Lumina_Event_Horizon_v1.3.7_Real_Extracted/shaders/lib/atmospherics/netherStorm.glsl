vec4 GetNetherStorm(vec3 color, vec3 translucentMult, vec3 nPlayerPos, vec3 playerPos, float lViewPos, float lViewPos1, float dither) {
    if (isEyeInWater != 0) return vec4(0.0);
    vec4 netherStorm = vec4(1.0, 1.0, 1.0, 0.0);

    float netherBiomeMixer = inNetherWastes + inCrimsonForest + inWarpedForest + inBasaltDeltas + inSoulValley;
    float stormBiomeWeighted = (
        inNetherWastes * 1.00 + inCrimsonForest * 1.12 + inWarpedForest * 0.62 +
        inBasaltDeltas * 1.45 + inSoulValley * 0.68
    ) / max(netherBiomeMixer, 0.0001);
    float stormBiomeIntensity = mix(1.0, stormBiomeWeighted, clamp01(netherBiomeMixer));
    float basaltAsh = clamp01(inBasaltDeltas);

    #ifdef BORDER_FOG
        float maxDist = min(renderDistance, NETHER_VIEW_LIMIT); // consistency9023HFUE85JG
    #else
        float maxDist = renderDistance;
    #endif

    #ifndef LOW_QUALITY_NETHER_STORM
        int sampleCount = max(int(maxDist / 8.0 + 0.001), 1);

        vec3 traceAdd = nPlayerPos * maxDist / sampleCount;
        vec3 tracePos = cameraPosition;
        tracePos += traceAdd * dither;
    #else
        int sampleCount = max(int(maxDist / 16.0 + 0.001), 1);

        vec3 traceAdd = 0.75 * nPlayerPos * maxDist / sampleCount;
        vec3 tracePos = cameraPosition;
        tracePos += traceAdd * dither;
        tracePos += traceAdd * sampleCount * 0.25;
    #endif

    vec3 translucentMultM = pow(translucentMult, vec3(1.0 / sampleCount));

    for (int i = 0; i < sampleCount; i++) {
        tracePos += traceAdd;

        vec3 tracedPlayerPos = tracePos - cameraPosition;
        float lTracePos = length(tracedPlayerPos);
        if (lTracePos > lViewPos1) break;

        vec3 wind = vec3(frameTimeCounter * 0.002);

        vec3 tracePosM = tracePos * 0.001;
        tracePosM.y += tracePosM.x;
        tracePosM += Noise3D(tracePosM - wind) * 0.01;
        tracePosM = tracePosM * vec3(2.0, 0.5, 2.0);

        float traceAltitudeM = abs(tracePos.y - NETHER_STORM_LOWER_ALT);
        if (tracePos.y < NETHER_STORM_LOWER_ALT) traceAltitudeM *= 10.0;
        traceAltitudeM = 1.0 - min1(abs(traceAltitudeM) / NETHER_STORM_HEIGHT);

        for (int h = 0; h < 4; h++) {
            float stormNoise = Noise3D(tracePosM + wind);
            float stormSample = pow2(pow2(stormNoise));
            float ashSample = pow2(stormNoise) * 0.72;
            stormSample = mix(stormSample, ashSample, basaltAsh * 0.58);
            stormSample *= traceAltitudeM;
            stormSample = pow2(stormSample);
            stormSample *= sqrt1(max0(1.0 - lTracePos / maxDist));

            netherStorm.a += stormSample;
            tracePosM *= 2.0;
            wind *= -2.0;
        }

        if (lTracePos > lViewPos) netherStorm.rgb *= translucentMultM;
    }

    #ifdef LOW_QUALITY_NETHER_STORM
        netherStorm.a *= 1.8;
    #endif

    netherStorm.a = min1(netherStorm.a * NETHER_STORM_I * stormBiomeIntensity);

    vec3 stormBiomeColor = mix(netherColor, vec3(0.29, 0.275, 0.26), basaltAsh * 0.62);
    netherStorm.rgb *= stormBiomeColor * 3.0 * (1.0 - maxBlindnessDarkness);

    //if (netherStorm.a > 0.98) netherStorm.rgb = vec3(1,0,1);
    //netherStorm.a *= 1.0 - max0(netherStorm.a - 0.98) * 50.0;

    return netherStorm;
}
