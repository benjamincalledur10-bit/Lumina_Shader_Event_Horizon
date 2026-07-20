#ifndef INCLUDE_CLOUD_SHADOWS
    #define INCLUDE_CLOUD_SHADOWS

    float GetCloudShadow(vec3 playerPos) {
        #ifndef OVERWORLD
            return 1.0;
        #endif

        vec3 worldPos = playerPos + cameraPosition;
        vec2 shadowPos = (worldPos.xz + worldPos.y * 0.25) * cloudNarrowness;
        float wind = 0.0006;
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
            wind *= 0.5;
        #endif
        shadowPos -= vec2(0.0, wind);

        vec2 shadowOffsets[8] = vec2[8](
            vec2( 0.0   , 1.0   ),
            vec2( 0.7071, 0.7071),
            vec2( 1.0   , 0.0   ),
            vec2( 0.7071,-0.7071),
            vec2( 0.0   ,-1.0   ),
            vec2(-0.7071,-0.7071),
            vec2(-1.0   , 0.0   ),
            vec2(-0.7071, 0.7071));

        float cloudSample = 0.0;
        for (int i = 0; i < 8; i++) {
            cloudSample += texture2DLod(noisetex, shadowPos + 0.005 * shadowOffsets[i], 0.0).b;
        }

        float shadowDensity = pow2(min1(cloudSample * 0.2 * LUMINA_CLOUD_COVERAGE));
        shadowDensity *= 0.75 + 0.25 * rainFactor;
        return 1.0 - 0.85 * smoothstep1(shadowDensity);
    }

#endif
