#ifndef INCLUDE_CLOUD_SHADOWS
#define INCLUDE_CLOUD_SHADOWS
#include "/lib/atmospherics/clouds/cloudShape.glsl"

float GetCloudShadow(vec3 playerPos) {
    #if !defined OVERWORLD || CLOUD_QUALITY == 0
        return 1.0;
    #else
        vec3 worldPos = playerPos + cameraPosition;
        vec3 direction = normalize(mat3(gbufferModelViewInverse) * lightVec);
        float top = float(cloudAlt1i) + cloudStretch;
        if (worldPos.y >= top || direction.y <= 0.02) return 1.0;
        float bottom = max(worldPos.y, float(cloudAlt1i) - cloudStretch);
        float stepHeight = (top - bottom) / 3.0;
        float opticalDepth = 0.0;
        for (int i = 0; i < 3; i++) {
            float y = bottom + (float(i) + 0.5) * stepHeight;
            vec3 samplePos = worldPos + direction * ((y - worldPos.y) / direction.y);
            opticalDepth += LuminaCloudShape(samplePos, cloudAlt1i, length(samplePos.xz - cameraPosition.xz), false)
                          * stepHeight / direction.y * 0.055;
        }
        float shadow = 0.85 * (1.0 - exp(-opticalDepth));
        return 1.0 - shadow * smoothstep(0.02, 0.12, direction.y);
    #endif
}
#endif
