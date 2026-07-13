#ifndef INCLUDE_ENDER_BEAMS
    #define INCLUDE_ENDER_BEAMS

    #include "/lib/colors/lightAndAmbientColors.glsl"

    vec2 wind = vec2(syncedTime * 0.00);

    float BeamNoise(vec2 planeCoord, vec2 wind) {
        float noise = texture2DLod(noisetex, planeCoord * 0.175   - wind * 0.0625, 0.0).b;
              noise+= texture2DLod(noisetex, planeCoord * 0.04375 + wind * 0.0375, 0.0).b * 5.0;

        return noise;
    }

    vec3 DrawEnderBeams(float VdotU, vec3 playerPos, vec3 nViewPos) {
        return vec3(0.0);
    }

#endif //INCLUDE_ENDER_BEAMS