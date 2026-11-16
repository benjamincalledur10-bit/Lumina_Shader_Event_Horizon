// Voxy patch API 1 / VOXY macro 3. Uniforms are supplied by Voxy's std140 UBO.
// No legacy uniforms, gl_FragData, main() or global dynamic initializers here.
#include "/lib/common.glsl"
layout(location=0) out vec4 luminaVoxyColor;
#ifdef LUMINA_VOXY_TRANSLUCENT
layout(location=1) out vec4 luminaVoxyTransmission;
layout(location=2) out vec4 luminaVoxyNormal;
layout(location=3) out vec4 luminaVoxyMaterial;
layout(location=4) out vec4 luminaVoxyReflection;
#else
layout(location=1) out vec4 luminaVoxyNormal;
layout(location=2) out vec4 luminaVoxyMaterial;
#endif

vec3 LuminaVoxyFace(uint face) {
    // Voxy axes are Y,Z,X, with the low bit selecting positive faces.
    vec3 n = vec3(0.0);
    uint axis = face >> 1u;
    n[axis == 0u ? 1 : (axis == 1u ? 2 : 0)] = (face & 1u) == 0u ? -1.0 : 1.0;
    return n;
}

vec3 LuminaVoxyPosition() {
    vec2 uv = gl_FragCoord.xy / vec2(viewWidth,viewHeight);
    uv -= LuminaVoxyTAAOffset() * 0.5;
    // Voxy's patch transformer presents conventional depth here and vxProjInv
    // is the matching conventional projection (not the vanilla near/far pair).
    vec4 p = vxProjInv * vec4(uv * 2.0 - 1.0, gl_FragCoord.z * 2.0 - 1.0, 1.0);
    return p.xyz / (abs(p.w) > 1e-7 ? p.w : (p.w < 0.0 ? -1e-7 : 1e-7));
}

vec3 LuminaVoxyLight(vec3 albedo, vec3 worldNormal, vec2 lm, vec3 viewPos) {
    float phase;
    #if SHADOW_QUALITY == -1
        phase = float(worldTime) / 24000.0;
    #else
        float t = fract(sunAngle - 0.033333333);
        float linear = t < 0.433333333 ? t * 1.15384615385 : t * 0.882352941176 + 0.117647058824;
        float halfDay = linear > 0.5 ? 1.0 : 0.0;
        float f = fract(linear * 2.0);
        phase = (mix(f, f*f*(3.0-2.0*f), halfDay < 0.5 ? 0.3 : -0.1) + halfDay) * 0.5;
    #endif
    float solar = sin(phase * 6.28318530718);
    float noonFactor = sqrt(max(solar,0.0) * smoothstep(0.0,0.12,solar));
    float invNoonFactor = 1.0-noonFactor;
    vec3 viewSun = sunPosition / max(length(sunPosition),1e-6);
    float elevation = (mat3(gbufferModelViewInverse) * viewSun).y;
    float sunVisibility = smoothstep(-0.0625,0.0625,elevation);
    float sunVisibility2 = sunVisibility*sunVisibility;
    float vsBrightness = clamp(screenBrightness,0.0,1.0);
    vec3 lavaLightColor = vec3(0.19,0.072,0.012);
    vec3 netherColor = fogColor * 0.6 + 0.2 * normalize(fogColor + 0.0001);
    #ifdef NETHER
        #if NETHER_COLOR_MODE == 0
            netherColor = vec3(0.69722423,0.26275879,0.07307493)*0.6;
        #elif NETHER_COLOR_MODE == 3
            float weight = inNetherWastes+inCrimsonForest+inWarpedForest+inBasaltDeltas+inSoulValley;
            netherColor = mix(netherColor,
                inNetherWastes*vec3(.43824534,.14148231,.03196956)+inCrimsonForest*vec3(.41985012,.04564224,.03208611)+
                inWarpedForest*vec3(.05500586,.28065756,.26659877)+inBasaltDeltas*vec3(.22004336,.22053661,.22712321)+
                inSoulValley*vec3(.08007813,.20064409,.29647857),clamp(weight,0.0,1.0));
        #endif
    #endif
    // Same palette code as near terrain; variables remain local to this function.
    #include "/lib/colors/lightAndAmbientColors.glsl"
    vec3 axis;
    #ifdef END
        axis = EVENT_HORIZON_DIRECTION;
    #elif defined OVERWORLD
        #if SHADOW_QUALITY >= 0
            axis = shadowModelViewInverse[2].xyz;
        #else
            axis = mat3(gbufferModelViewInverse) * viewSun
                 * ((phase < 0.5325 || phase > 0.9675) ? 1.0 : -1.0);
        #endif
    #else
        axis = vec3(0.0); // Nether has ambient/block lighting, not a solar source.
    #endif
    axis /= max(length(axis),1e-6); // Also safe before a shadow map is initialized.
    float diffuse = max(dot(worldNormal,axis),0.0);
    float sky = lm.y*lm.y;
    vec3 block = vec3(.1775,.104,.077)*vec3(XLIGHT_R,XLIGHT_G,XLIGHT_B)*XLIGHT_I*lm.x*lm.x*4.0;
    vec3 illumination = ambientColor*(0.10+0.90*sky)*(float(AMBIENT_MULT)*0.01)
                      + lightColor*diffuse*sky + block;
    return albedo * max(illumination,vec3(0.025));
}

void voxy_emitFragment(VoxyFragmentParameters parameters) {
    vec3 viewPos = LuminaVoxyPosition();
    vec3 normal = LuminaVoxyFace(parameters.face);
    vec2 lm = clamp((parameters.lightMap-vec2(0.03125))*1.066666667,0.0,1.0);
    vec4 albedo = parameters.sampledColour * parameters.tinting;
    vec3 lit = LuminaVoxyLight(albedo.rgb,normal,lm,viewPos);
    // Emission IDs are Lumina's existing block.properties IDs, not Voxy model IDs.
    if (parameters.customId == 10068u) lit += albedo.rgb * 1.5;
    else if (parameters.customId == 10412u || parameters.customId == 10448u) lit += albedo.rgb;
    float smoothness = 0.0;
    float material = 0.0;
    #ifdef LUMINA_VOXY_TRANSLUCENT
        bool water = parameters.customId == 32000u;
        float alpha = clamp(albedo.a,0.0,1.0);
        if (water) {
            vec3 worldPos = (vxModelViewInv * vec4(viewPos,1.0)).xyz + cameraPosition;
            float clock = frameTimeCounter * float(WATER_SPEED_MULT) * 0.018;
            #if WATER_STYLE >= 2
                vec2 slope = vec2(cos(dot(worldPos.xz,vec2(.16,.07))-clock*11.0),
                                  cos(dot(worldPos.xz,vec2(-.09,.13))-clock*8.0)) * 0.035 * float(WATER_BUMPINESS);
                normal = normalize(normal + vec3(slope.x,0.0,slope.y)*abs(normal.y));
            #endif
            vec3 viewNormal = normalize(mat3(vxModelView)*normal);
            float facing = clamp(abs(dot((-viewPos / max(length(viewPos),1e-6)),viewNormal)),0.0,1.0);
            float fresnel = 0.02+0.98*pow(1.0-facing,5.0);
            vec3 reflected = reflect(viewPos / max(length(viewPos),1e-6),viewNormal);
            vec3 worldReflected = mat3(vxModelViewInv)*reflected;
            vec3 sky = mix(fogColor,skyColor,smoothstep(0.0,0.6,worldReflected.y));
            lit = mix(lit*vec3(.86,.97,1.04),max(sky,vec3(0.0)),fresnel*lm.y);
            alpha = mix(0.38,0.90,fresnel);
            if (isEyeInWater == 1) alpha = 0.75;
            smoothness = 1.0;
            material = 241.0/255.0;
        }
        luminaVoxyColor = vec4(max(lit,vec3(0.0)),alpha);
        // Multiplicative transmission follows Lumina's 1-transmission encoding.
        luminaVoxyTransmission = vec4((vec3(1.0)-clamp(albedo.rgb,0.0,1.0))*alpha,alpha);
        luminaVoxyReflection = vec4(0.0); // Distant-water reflections are sky-only for now.
    #else
        luminaVoxyColor = vec4(max(lit,vec3(0.0)),1.0);
    #endif
    // Fully initialize metadata; never leave stale near-terrain reflection values.
    luminaVoxyNormal = vec4(normal,0.0);
    #ifdef IRIS_FEATURE_FADE_VARIABLE
        float skyLight = lm.y*0.5;
    #else
        float skyLight = lm.y;
    #endif
    luminaVoxyMaterial = vec4(smoothness,material,skyLight,1.0);
}
