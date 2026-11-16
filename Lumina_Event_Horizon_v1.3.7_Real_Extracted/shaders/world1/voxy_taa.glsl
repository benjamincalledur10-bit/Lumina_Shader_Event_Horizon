{
#define LUMINA_VOXY_PATCH
#include "/lib/common.glsl"
#if defined TAA && TAA_JITTER > 0
    vec2 offsets[8] = vec2[8](vec2(.125,-.375),vec2(-.125,.375),vec2(.625,.125),vec2(.375,-.625),vec2(-.625,.625),vec2(-.875,-.125),vec2(.375,-.875),vec2(.875,.875));
    vec2 offset = offsets[int(framemod8)] / vec2(viewWidth,viewHeight);
    #if TAA_JITTER == 1
        offset *= 0.125;
    #elif TAA_JITTER == 2
        offset *= 0.33;
    #endif
    return offset;
#else
    return vec2(0.0);
#endif
}
