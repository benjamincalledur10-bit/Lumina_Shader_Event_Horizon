#ifndef INCLUDE_CLOUD_SHADOWS
    #define INCLUDE_CLOUD_SHADOWS

    #include "/lib/atmospherics/clouds/cloudDensity.glsl"

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
        float cloudDensity = GetLuminaCloudDensity(vec3(cloudWorldPos.x, float(CLOUD_ALT1), cloudWorldPos.y),
                                                  CLOUD_ALT1, length(cloudWorldPos - cameraPosition.xz), 0.0);
        float shadowDensity = 1.0 - exp(-max0(cloudDensity) * cloudTallness * 0.08);
        return 1.0 - 0.85 * smoothstep1(shadowDensity);
    }

#endif
