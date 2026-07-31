#ifndef INCLUDE_CLOUD_SHADOWS
    #define INCLUDE_CLOUD_SHADOWS

    float GetCloudShadow(vec3 playerPos) {
        #ifndef OVERWORLD
            return 1.0;
        #endif
        #if CLOUD_QUALITY == 0
            return 1.0;
        #endif

        vec3 worldPos = playerPos + cameraPosition;
        vec3 worldLightDir = normalize(mat3(gbufferModelViewInverse) * lightVec);
        float altitudeDistance = float(CLOUD_ALT1) - worldPos.y;
        float lightDirY = max(abs(worldLightDir.y), 0.05);
        vec2 cloudWorldPos = worldPos.xz + worldLightDir.xz * (altitudeDistance / lightDirY);
        #if CLOUD_QUALITY > 1
            const float shadowCloudNarrowness = 0.00012;
        #else
            const float shadowCloudNarrowness = 0.00006;
        #endif
        vec3 shadowPos = vec3(cloudWorldPos.x, float(CLOUD_ALT1), cloudWorldPos.y) * shadowCloudNarrowness;
        float wind = 0.0006;
        float noise = 0.0;
        float currentPersist = 1.0;
        float total = 0.0;

        #if CLOUD_SPEED_MULT == 100
            wind *= syncedTime;
        #else
            wind *= frameTimeCounter * (CLOUD_SPEED_MULT * 0.01);
        #endif
        #if LUMINA_CLOUD_SCALE != 100
            const float cloudScale = LUMINA_CLOUD_SCALE * 0.01;
            shadowPos *= cloudScale;
            wind *= cloudScale;
        #endif

        #if CLOUD_QUALITY == 1
            const int sampleCount = 4;
            const float noiseMult = 1.05;
            wind *= 0.5;
        #elif CLOUD_QUALITY == 2
            const int sampleCount = 5;
            const float noiseMult = 1.20;
        #else
            const int sampleCount = 6;
            const float noiseMult = 1.15;
        #endif

        vec3 baseShadowPos = shadowPos;
        float baseWind = wind;
        for (int i = 0; i < sampleCount; i++) {
            #if CLOUD_QUALITY >= 3
                noise += Noise3D(shadowPos - vec3(0.0, 0.0, wind)) * currentPersist;
            #else
                noise += texture2DLod(noisetex, shadowPos.xz - vec2(0.0, wind), 0.0).b * currentPersist;
            #endif
            total += currentPersist;

            shadowPos *= 3.0;
            wind *= 0.5;
            currentPersist *= 0.55;
        }

        noise = pow(noise / total, 1.85);
        noise *= noiseMult
               * (1.35 + LUMINA_CLOUD_RAIN_DENSITY * rainFactor)
               * LUMINA_CLOUD_COVERAGE;

        float cloudDensity = noise - 0.22;
        #if CLOUD_QUALITY >= 2
            vec3 erosionPos = baseShadowPos * 2.35 + vec3(0.17, 0.43, 0.29);
            float erosion = Noise3D(erosionPos - vec3(0.0, 0.0, baseWind * 0.35)) - 0.5;
            float detailFade = 1.0 - smoothstep(1200.0, 3600.0, length(cloudWorldPos - cameraPosition.xz));
            cloudDensity += erosion * 0.10 * detailFade;
        #endif

        float shadowDensity = min1(max0(cloudDensity) * 8.0);
        return 1.0 - 0.85 * smoothstep1(shadowDensity);
    }

#endif
