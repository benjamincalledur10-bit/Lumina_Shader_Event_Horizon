/////////////////////////////////////
// Lumina Shader - Event Horizon //
/////////////////////////////////////

//Common//
#include "/lib/common.glsl"

//////////Fragment Shader//////////Fragment Shader//////////Fragment Shader//////////
#ifdef FRAGMENT_SHADER

#if WORLD_BLUR > 0
    noperspective in vec2 texCoord;

    flat in vec3 upVec, sunVec;
#endif

//Pipeline Constants//
#if WORLD_BLUR > 0
    const bool colortex0MipmapEnabled = true;
#endif

//Common Variables//
#if WORLD_BLUR > 0
    #if WORLD_BLUR >= 2 && WB_DOF_FOCUS >= 0
        #if WB_DOF_FOCUS == 0
            uniform float centerDepthSmooth;
        #else
            float centerDepthSmooth = (far * (WB_DOF_FOCUS - near)) / (WB_DOF_FOCUS * (far - near));
        #endif
    #endif
#endif

#if WORLD_BLUR > 0
    float SdotU = dot(sunVec, upVec);
    float sunFactor = SdotU < 0.0 ? clamp(SdotU + 0.375, 0.0, 0.75) / 0.75 : clamp(SdotU + 0.03125, 0.0, 0.0625) / 0.0625;


#endif

//Common Functions//
#if WORLD_BLUR > 0
    // Axial view depth keeps an entire focus plane sharp, including screen edges.
    float AutofocusViewDepth(vec2 uv, float depth, mat4 projectionInverse) {
        vec4 p = projectionInverse * vec4(uv * 2.0 - 1.0, depth * 2.0 - 1.0, 1.0);
        return max(abs(p.z) / max(abs(p.w), 0.000001), 0.05);
    }

    float AutofocusSceneDepth(vec2 uv, float depth) {
        float distance = AutofocusViewDepth(uv, depth, gbufferProjectionInverse);
        #ifdef DISTANT_HORIZONS
            if (depth >= 0.999999) {
                float dhDepth = texture2DLod(dhDepthTex1, uv, 0.0).r;
                distance = AutofocusViewDepth(uv, dhDepth, dhProjectionInverse);
            }
        #endif
        return distance;
    }

    // Explicit filtering: colortex0 can use nearest filtering on some loaders.
    float BlurTexelVisibility(ivec2 pixel, ivec2 size, float distance) {
        float z = texelFetch(depthtex1, pixel, 0).r;
        if (z < 0.56) return 0.0;
        float sampleDistance = AutofocusSceneDepth((vec2(pixel) + 0.5) / vec2(size), z);
        float tolerance = max(0.1, distance * 0.1);
        return smoothstep(distance - tolerance, distance - tolerance * 0.2, sampleDistance);
    }

    vec3 SmoothBlurLevel(vec2 uv, int level, float distance) {
        ivec2 size = textureSize(colortex0, level);
        vec2 p = uv * vec2(size) - 0.5;
        ivec2 base = ivec2(floor(p));
        vec2 f = fract(p);
        ivec2 last = size - ivec2(1);
        vec3 a = texelFetch(colortex0, clamp(base, ivec2(0), last), level).rgb;
        vec3 b = texelFetch(colortex0, clamp(base + ivec2(1, 0), ivec2(0), last), level).rgb;
        vec3 c = texelFetch(colortex0, clamp(base + ivec2(0, 1), ivec2(0), last), level).rgb;
        vec3 d = texelFetch(colortex0, clamp(base + ivec2(1), ivec2(0), last), level).rgb;
        if (level == 0) {
            vec4 weights = vec4((1.0 - f.x) * (1.0 - f.y), f.x * (1.0 - f.y), (1.0 - f.x) * f.y, f.x * f.y);
            weights *= vec4(BlurTexelVisibility(clamp(base, ivec2(0), last), size, distance),
                            BlurTexelVisibility(clamp(base + ivec2(1, 0), ivec2(0), last), size, distance),
                            BlurTexelVisibility(clamp(base + ivec2(0, 1), ivec2(0), last), size, distance),
                            BlurTexelVisibility(clamp(base + ivec2(1), ivec2(0), last), size, distance));
            return (a * weights.x + b * weights.y + c * weights.z + d * weights.w) / max(dot(weights, vec4(1.0)), 0.0001);
        }
        return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
    }

    vec3 SmoothBlurColor(vec2 uv, float lod, float distance) {
        int level = int(floor(lod));
        vec3 low = SmoothBlurLevel(uv, level, distance);
        if (fract(lod) < 0.001) return low;
        return mix(low, SmoothBlurLevel(uv, level + 1, distance), fract(lod));
    }

    void DoSmoothCinematicBlur(inout vec3 color, float depth, float radius) {
        radius = clamp(radius, 0.0, 48.0);
        if (radius < 0.5) return;
        float sceneDistance = AutofocusSceneDepth(texCoord, depth);
        vec2 scale = vec2(1.0 / aspectRatio, 1.0) / 1080.0;
        #ifdef WB_ANAMORPHIC
            scale *= vec2(0.5, 1.5);
        #endif
        vec2 border = 0.5 / vec2(viewWidth, viewHeight);
        // Overlapping prefiltered footprints suppress discrete copies of bright edges.
        // Physical pixel radius grows with resolution, including 4K rendering.
        float footprint = radius * (viewHeight / 1080.0) * 2.0 / sqrt(float(WB_AF_QUALITY));
        float maxLod = floor(log2(max(min(viewWidth, viewHeight), 1.0)));
        float lod = clamp(log2(max(footprint, 1.0)), 0.0, min(5.0, maxLod));
        // Near silhouettes, use the full-resolution source to avoid mipmap color leakage.
        for (int j = 0; j < 8; j++) {
            float angle = float(j) * 0.78539816;
            vec2 uv = clamp(texCoord + vec2(cos(angle), sin(angle)) * (radius + footprint * 2.0) * scale, border, 1.0 - border);
            float z = texture2DLod(depthtex1, uv, 0.0).r;
            if (z < 0.56 || AutofocusSceneDepth(uv, z) < sceneDistance * 0.9) lod = 0.0;
        }
        vec3 sum = vec3(0.0);
        float totalWeight = 0.0;
        for (int i = 0; i < WB_AF_QUALITY; i++) {
            float angle = float(i) * 2.39996323;
            float diskRadius = sqrt((float(i) + 0.5) / float(WB_AF_QUALITY));
            vec2 offset = vec2(cos(angle), sin(angle)) * diskRadius * radius * scale;
            vec2 uv = clamp(texCoord + offset, border, 1.0 - border);
            float sampleDepth = texture2DLod(depthtex1, uv, 0.0).r;
            if (sampleDepth < 0.56) continue;
            float sampleDistance = AutofocusSceneDepth(uv, sampleDepth);
            float tolerance = max(0.1, sceneDistance * 0.1);
            float visibility = smoothstep(sceneDistance - tolerance, sceneDistance - tolerance * 0.2, sampleDistance);
            // Soft aperture edges reduce rings and repeated outlines; no noisy temporal jitter.
            float weight = exp(-2.5 * diskRadius * diskRadius) * visibility;
            vec3 sampleColor = SmoothBlurColor(uv, lod, sceneDistance);
            #if defined WB_CHROMATIC && WORLD_BLUR != 3
                vec2 fringe = offset * 0.035;
                sampleColor.r = SmoothBlurColor(clamp(uv + fringe, border, 1.0 - border), lod, sceneDistance).r;
                sampleColor.b = SmoothBlurColor(clamp(uv - fringe, border, 1.0 - border), lod, sceneDistance).b;
            #endif
            sum += sampleColor * weight;
            totalWeight += weight;
        }
        if (totalWeight > 0.0001) {
            color = mix(color, sum / totalWeight, smoothstep(0.5, 1.5, radius));
        }
    }
#endif

#if WORLD_BLUR == 3
    void DoCinematicAutofocus(inout vec3 color, float depth) {
        float sceneDistance = AutofocusSceneDepth(texCoord, depth);
        #if WB_DOF_FOCUS == 0
            float focusDistance = AutofocusSceneDepth(vec2(0.5), centerDepthSmooth);
        #elif WB_DOF_FOCUS > 0
            float focusDistance = float(WB_DOF_FOCUS);
        #else
            float focusDistance = mix(1.0, 256.0, pow2(vsBrightness));
        #endif
        // Preserve the subject and foreground; blur only behind the focus plane.
        float focusBand = max(0.1, focusDistance * 0.05);
        float defocus = max(sceneDistance - focusDistance - focusBand, 0.0) / max(sceneDistance, 0.05);
        float radius = min(24.0 * WB_AF_STRENGTH * defocus, 48.0);
        #ifdef WB_FOV_SCALED
            radius *= clamp(gbufferProjection[1][1] * 0.8, 0.25, 4.0);
        #endif
        DoSmoothCinematicBlur(color, depth, radius);
    }
#endif

#if WORLD_BLUR > 0
    void DoWorldBlur(inout vec3 color, float z1, float lViewPos0) {
        if (z1 < 0.56) return;
        #if WORLD_BLUR == 3
            DoCinematicAutofocus(color, z1);
        #else

        #if WORLD_BLUR == 1 // Distance Blur
            #ifdef OVERWORLD
                float dbMult;
                if (isEyeInWater == 0) {
                    dbMult = mix(WB_DB_NIGHT_I, WB_DB_DAY_I, sunFactor * eyeBrightnessM);
                    dbMult = mix(dbMult, WB_DB_RAIN_I, rainFactor * eyeBrightnessM);
                } else dbMult = WB_DB_WATER_I;
            #elif defined NETHER
                float dbMult = WB_DB_NETHER_I;
            #elif defined END
                float dbMult = WB_DB_END_I;
            #endif
            float coc = clamp(lViewPos0 * 0.001, 0.0, 0.1) * dbMult * 0.03;
        #elif WORLD_BLUR == 2 // Depth Of Field
            #if WB_DOF_FOCUS >= 0
                float coc = max(abs(z1 - centerDepthSmooth) * 0.125 * WB_DOF_I - 0.0001, 0.0);
            #elif WB_DOF_FOCUS == -1
                float coc = clamp(abs(lViewPos0 * 0.005 - pow2(vsBrightness)), 0.0, 0.1) * WB_DOF_I * 0.03;
            #endif
        #endif
        coc = coc / sqrt(coc * coc + 0.1);

        #ifdef WB_FOV_SCALED
            coc *= gbufferProjection[1][1] * 0.8;
        #endif
        DoSmoothCinematicBlur(color, z1, coc * 9.0);
        #endif
    }
#endif

//Includes//
#if WORLD_BLUR > 0 && defined BLOOM_FOG_COMPOSITE3
    #include "/lib/atmospherics/fog/bloomFog.glsl"
#endif

//Program//
void main() {
    vec3 color = texelFetch(colortex0, texelCoord, 0).rgb;

    #if WORLD_BLUR > 0
        float z1 = texelFetch(depthtex1, texelCoord, 0).r;
        float z0 = texelFetch(depthtex0, texelCoord, 0).r;

        vec4 screenPos = vec4(texCoord, z0, 1.0);
        vec4 viewPos = gbufferProjectionInverse * (screenPos * 2.0 - 1.0);
        viewPos /= viewPos.w;
        float lViewPos = length(viewPos.xyz);

        #if defined DISTANT_HORIZONS && defined NETHER
            float z0DH = texelFetch(dhDepthTex, texelCoord, 0).r;
            vec4 screenPosDH = vec4(texCoord, z0DH, 1.0);
            vec4 viewPosDH = dhProjectionInverse * (screenPosDH * 2.0 - 1.0);
            viewPosDH /= viewPosDH.w;
            lViewPos = min(lViewPos, length(viewPosDH.xyz));
        #endif

        DoWorldBlur(color, z1, lViewPos);

        #ifdef BLOOM_FOG_COMPOSITE3
            color *= GetBloomFog(lViewPos); // Reminder: Bloom Fog can move between composite1-3
        #endif
    #endif

    /* DRAWBUFFERS:0 */
    gl_FragData[0] = vec4(color, 1.0);
}

#endif

//////////Vertex Shader//////////Vertex Shader//////////Vertex Shader//////////
#ifdef VERTEX_SHADER

#if WORLD_BLUR > 0
    noperspective out vec2 texCoord;

    flat out vec3 upVec, sunVec;
#endif

//Attributes//

//Common Variables//

//Common Functions//

//Includes//

//Program//
void main() {
    gl_Position = ftransform();

    #if WORLD_BLUR > 0
        texCoord = (gl_TextureMatrix[0] * gl_MultiTexCoord0).xy;
        upVec = normalize(gbufferModelView[1].xyz);
        sunVec = GetSunVector();
    #endif
}

#endif
