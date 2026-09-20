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

    vec2 dofOffsets[18] = vec2[18](
        vec2( 0.0    ,  0.25  ),
        vec2(-0.2165 ,  0.125 ),
        vec2(-0.2165 , -0.125 ),
        vec2( 0      , -0.25  ),
        vec2( 0.2165 , -0.125 ),
        vec2( 0.2165 ,  0.125 ),
        vec2( 0      ,  0.5   ),
        vec2(-0.25   ,  0.433 ),
        vec2(-0.433  ,  0.25  ),
        vec2(-0.5    ,  0     ),
        vec2(-0.433  , -0.25  ),
        vec2(-0.25   , -0.433 ),
        vec2( 0      , -0.5   ),
        vec2( 0.25   , -0.433 ),
        vec2( 0.433  , -0.2   ),
        vec2( 0.5    ,  0     ),
        vec2( 0.433  ,  0.25  ),
        vec2( 0.25   ,  0.433 )
    );
#endif

//Common Functions//
#if WORLD_BLUR == 3
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
        radius = min(radius, 48.0);
        if (radius < 0.5) return;

        // Radius is measured in pixels at 1080p, with equal horizontal/vertical scale.
        vec2 scale = vec2(1.0 / aspectRatio, 1.0) / 1080.0;
        #ifdef WB_ANAMORPHIC
            scale *= vec2(0.5, 1.5);
        #endif
        vec2 border = 0.5 / vec2(viewWidth, viewHeight);
        vec3 sum = color;
        float totalWeight = 1.0;
        for (int i = 0; i < WB_AF_QUALITY; i++) {
            float angle = float(i) * 2.39996323;
            float diskRadius = sqrt((float(i) + 0.5) / float(WB_AF_QUALITY));
            vec2 offset = vec2(cos(angle), sin(angle)) * diskRadius * radius * scale;
            vec2 uv = clamp(texCoord + offset, border, 1.0 - border);
            float sampleDepth = texture2DLod(depthtex1, uv, 0.0).r;
            // Reject hands and nearer silhouettes instead of smearing them over the background.
            if (sampleDepth < 0.56) continue;
            float sampleDistance = AutofocusSceneDepth(uv, sampleDepth);
            float tolerance = max(0.1, sceneDistance * 0.02);
            float weight = smoothstep(sceneDistance - tolerance, sceneDistance, sampleDistance);
            vec3 sampleColor = texture2DLod(colortex0, uv, 0.0).rgb;
            sum += sampleColor * weight;
            totalWeight += weight;
        }
        color = mix(color, sum / totalWeight, smoothstep(0.5, 1.5, radius));
    }
#endif

#if WORLD_BLUR > 0
    void DoWorldBlur(inout vec3 color, float z1, float lViewPos0) {
        if (z1 < 0.56) return;
        #if WORLD_BLUR == 3
            DoCinematicAutofocus(color, z1);
        #else
        vec3 dof = vec3(0.0);
        vec2 dofScale = vec2(1.0, aspectRatio);

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
        #ifdef WB_CHROMATIC
            float midDistX = texCoord.x - 0.5;
            float midDistY = texCoord.y - 0.5;
            vec2 chromaticScale = vec2(midDistX, midDistY);
            chromaticScale = sign(chromaticScale) * sqrt(abs(chromaticScale));
            chromaticScale *= vec2(1.0, viewHeight / viewWidth);
            vec2 aberration = (15.0 / vec2(viewWidth, viewHeight)) * chromaticScale * coc;
        #endif
        #ifdef WB_ANAMORPHIC
            dofScale *= vec2(0.5, 1.5);
        #endif

        if (coc * 0.5 > 1.0 / max(viewWidth, viewHeight)) {
            for (int i = 0; i < 18; i++) {
                vec2 offset = dofOffsets[i] * coc * 0.0085 * dofScale;
                float lod = log2(viewHeight * aspectRatio * coc * 0.75 / 320.0);
                #ifndef WB_CHROMATIC
                    dof += texture2DLod(colortex0, texCoord + offset, lod).rgb;
                #else
                    dof += vec3(texture2DLod(colortex0, texCoord + offset + aberration, lod).r,
                                texture2DLod(colortex0, texCoord + offset             , lod).g,
                                texture2DLod(colortex0, texCoord + offset - aberration, lod).b);
                #endif
            }
            dof /= 18.0;
            color = dof;
        }
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
