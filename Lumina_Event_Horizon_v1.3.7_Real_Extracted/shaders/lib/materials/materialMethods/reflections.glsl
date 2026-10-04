#include "/lib/misc/reprojection.glsl"

#ifdef OVERWORLD
    #include "/lib/atmospherics/sky.glsl"
#endif
#if defined END && defined COMPOSITE
    #include "/lib/atmospherics/enderBeams.glsl"
#endif

#ifdef ATM_COLOR_MULTS
    #include "/lib/colors/colorMultipliers.glsl"
#endif
#ifdef MOON_PHASE_INF_ATMOSPHERE
    #include "/lib/colors/moonPhaseInfluence.glsl"
#endif

#if WORLD_SPACE_REFLECTIONS_INTERNAL > 0 && defined COMPOSITE
    #include "/lib/voxelization/lightVoxelization.glsl"
    #include "/lib/materials/materialMethods/worldSpaceRef.glsl"
#endif

float GetApproxDistance(float depth) {
    return near * far / (far - depth * far);
}

vec3 nvec3(vec4 pos) {
    return pos.xyz/pos.w;
}

float refDist = far;

#include "/lib/materials/materialMethods/reflectionBackground.glsl"

vec4 GetReflection(vec3 normalM, vec3 viewPos, vec3 nViewPos, vec3 playerPos, float lViewPos, float z0,
                   sampler2D depthtex, float dither, float skyLightFactor, float fresnel,
                   float smoothness, vec3 geoNormal, vec3 color, vec3 shadowMult, float highlightMult) {
    bool waterSurface = false;
    #if defined OVERWORLD && defined GBUFFERS_WATER
        waterSurface = mat == 32000;
    #elif defined OVERWORLD && defined DH_WATER
        waterSurface = mat == DH_BLOCK_WATER;
    #endif
    // ============================== Step 1: Prepare ============================== //
    #if WORLD_SPACE_REFLECTIONS_INTERNAL == -1
        vec2 rEdge = vec2(0.6, 0.55);
    #else
        vec2 rEdge = vec2(0.525, 0.525);
    #endif
    vec3 normalMR = normalM;

    #if defined GBUFFERS_WATER && WATER_STYLE == 1 && defined GENERATED_NORMALS
        normalMR = normalize(mix(geoNormal, normalM, 0.05));
    #endif

    if (waterSurface) normalMR = normalize(mix(geoNormal, normalM, 0.90));
    vec3 nViewPosR = normalize(reflect(nViewPos, normalMR));
    float RVdotU = dot(nViewPosR, upVec);
    float RVdotS = dot(nViewPosR, sunVec);

    #if defined GBUFFERS_WATER && WATER_STYLE >= 2
        if (!waterSurface) normalMR = normalize(mix(geoNormal, normalM, 0.8));
    #endif
    // ============================== End of Step 1 ============================== //

    // ============================== Step 2: Calculate Terrain Reflection and Alpha ============================== //
    #if WORLD_SPACE_REFLECTIONS_INTERNAL > 0 && defined COMPOSITE && WATER_REFLECT_QUALITY >= 1
        // In COMPOSITE for translucents we just need to return WSR and that's it
        if (z0 != z1) {
            /*vec4 reflection;
            AddBackgroundReflection(reflection, color, playerPos, normalM, normalMR, nViewPos, nViewPosR,
                                    shadowMult, RVdotU, RVdotS, z0, dither, skyLightFactor, smoothness, highlightMult);

            return reflection;*/
            vec4 reflection = getWSR(playerPos, normalMR, nViewPosR, RVdotU, RVdotS, z0, dither);
            refDist = length(playerPos - wsrHitPos);
            return reflection;
        }
    #endif

    vec4 reflection = vec4(0.0);
    #if (defined COMPOSITE || WATER_REFLECT_QUALITY >= 1) && (WORLD_SPACE_REFLECTIONS_INTERNAL == -1 || WORLD_SPACE_REF_MODE == 2)
        #if defined COMPOSITE || WATER_REFLECT_QUALITY >= 2 && !defined DH_WATER
            // Method 1: Ray Marched Reflection //

            // Ray Marching
            vec3 start = viewPos + normalMR * (lViewPos * 0.025 * (1.0 - fresnel) + 0.05);
            #if defined GBUFFERS_WATER && WATER_STYLE >= 2
                vec3 vector = normalize(reflect(nViewPos, normalMR)); // Not using nViewPosR because normalMR changed
            #else
                vec3 vector = nViewPosR;
            #endif
            //vector = normalize(vector - 0.5 * (1.0 - smoothness) * (1.0 - fresnel) * normalMR); // reflection anisotropy test
            //vector = normalize(vector - 0.075 * dither * (1.0 - pow2(pow2(fresnel))) * normalMR);
            vector *= 0.5;
            vec3 vectorBase = vector;
            vec3 viewPosRT = viewPos + vector;
            vec3 tvector = vector;

            #if WORLD_SPACE_REFLECTIONS_INTERNAL == -1
                int sampleCount = 8;
                int refinementCount = 2;
            #else
                int sampleCount = 12;
                int refinementCount = 3;
            #endif

            if (waterSurface) {
                #if DETAIL_QUALITY >= 3
                    sampleCount = 16;
                #else
                    sampleCount = 12;
                #endif
                refinementCount = 3;
                viewPosRT = start + vector;
            }
            float hitDepth = 1.0;
            int sr = 0;
            float dist = 0.0;
            vec3 refPos = vec3(0.0);
            vec3 rfragpos = vec3(0.0);
            float err = 9999999.0;
            for (int i = 0; i < sampleCount; i++) {
                vec4 rayClip = gbufferProjection * vec4(viewPosRT, 1.0);
                if (waterSurface && rayClip.w <= 0.000001) break;
                refPos = nvec3(rayClip) * 0.5 + 0.5;
                if (waterSurface && (min(refPos.x, refPos.y) <= 0.0 || max(refPos.x, refPos.y) >= 1.0)) break;
                if (abs(refPos.x - 0.5) > rEdge.x || abs(refPos.y - 0.5) > rEdge.y) break;

                rfragpos = vec3(refPos.xy, texture2D(depthtex, refPos.xy).r);
                hitDepth = rfragpos.z;
                rfragpos = nvec3(gbufferProjectionInverse * vec4(rfragpos * 2.0 - 1.0, 1.0));
                dist = length(start - rfragpos);

                err = length(viewPosRT - rfragpos);
                if (err * 0.33333 < length(vector)) {
                    sr++;
                    if (sr >= refinementCount) break;
                    tvector -= vector;
                    vector *= 0.1;
                }
                vector *= 2.0;
                tvector += vector * (0.95 + 0.1 * dither);
                viewPosRT = start + tvector;
            }

            float lViewPosRT = length(rfragpos);

            // Finalizing Terrain Reflection and Alpha
            if (
                refPos.z < 0.99997
                && (!waterSurface || (sr >= refinementCount && hitDepth < 0.99997 && refPos.z > 0.0))
                #if WORLD_SPACE_REFLECTIONS_INTERNAL > 0 && COLORED_LIGHTING_INTERNAL >= 256
                    && (err < 2.0 + pow2(lViewPosRT) * 0.001 || lViewPosRT > 0.25 * COLORED_LIGHTING_INTERNAL)
                #endif
            ) {
                vec2 absPos = abs(refPos.xy - 0.5);
                vec2 cdist = absPos / rEdge;
                float border = clamp(1.0 - pow(max(cdist.x, cdist.y), 50.0), 0.0, 1.0);
                if (waterSurface) {
                    float edgeDistance = min(min(refPos.x, refPos.y), min(1.0 - refPos.x, 1.0 - refPos.y));
                    border = smoothstep(0.02, 0.12, edgeDistance);
                }
                reflection.a = border;

                if (reflection.a > 0.001) {
                    vec2 edgeFactor = pow2(pow2(pow2(cdist)));
                    #if WORLD_SPACE_REFLECTIONS_INTERNAL == -1
if (!waterSurface) refPos.y += (dither - 0.5) * (0.05 * (edgeFactor.x + edgeFactor.y));
                    #endif

                    #ifdef GBUFFERS_WATER
                        // The scene texture alpha is not ray-hit confidence.
                        if (waterSurface) reflection.rgb = texture2D(gaux2, refPos.xy).rgb;
                        else reflection = texture2D(gaux2, refPos.xy);
                        reflection.rgb = pow2(reflection.rgb * 2.0);
                    #else
                        float smoothnessDM = pow2(smoothness);
                        float lodFactor = 1.0 - exp(-0.125 * (1.0 - smoothnessDM) * dist);
                        float lod = log2(viewHeight / 8.0 * (1.0 - smoothnessDM) * lodFactor) * 0.45;
                        if (z0 <= 0.56) lod *= 2.22; // Using more lod to compensate for less roughness noise on held items
                        lod = max(lod - 1.0, 0.0);

                        reflection.rgb = texture2DLod(colortex0, refPos.xy, lod).rgb;
                    #endif

                    float skyFade = 0.0;

                    #ifdef GBUFFERS_WATER
                        float reflectionPrevAlpha = reflection.a;
                        DoFog(reflection, skyFade, lViewPosRT, ViewToPlayer(rfragpos.xyz), RVdotU, RVdotS, dither, true, lViewPos);
                        reflection.a = reflectionPrevAlpha;
                        //reflection.a *= 1.0 - skyFade;
                    #endif

                    edgeFactor.x = pow2(edgeFactor.x);
                    edgeFactor = 1.0 - edgeFactor;
                    float refFactor = pow(edgeFactor.x * edgeFactor.y, 2.0 + 3.0 * GetLuminance(reflection.rgb));
                    #if WORLD_SPACE_REFLECTIONS_INTERNAL > 0 && defined GBUFFERS_WATER
                        refFactor = min(refFactor, 0.1) * 10.0;
                    #endif
                    reflection.a *= refFactor;
                    refDist = dist;
                }

                float posDif = lViewPosRT - lViewPos;
                reflection.a *= clamp(posDif + 3.0, 0.0, 1.0);
            }
            #if !defined COMPOSITE && defined DISTANT_HORIZONS
                else
            #endif
        #endif
        #if !defined COMPOSITE && (WATER_REFLECT_QUALITY < 2 || defined DISTANT_HORIZONS) || defined DH_WATER
        {   // Method 2: Mirorred Image Reflection //

            #if WATER_REFLECT_QUALITY < 2 && !defined DISTANT_HORIZONS
                float verticalStretch = 0.013; // for potato quality reflections
            #else
                float verticalStretch = 0.0025; // for distant horizons reflections
            #endif

            vec4 clipPosR = gbufferProjection * vec4(nViewPosR + verticalStretch * viewPos, 1.0);
            float reflectionClipW = abs(clipPosR.w) < 0.000001
                ? (clipPosR.w < 0.0 ? -0.000001 : 0.000001) : clipPosR.w;
            vec3 screenPosR = clipPosR.xyz / reflectionClipW * 0.5 + 0.5;
            vec2 screenPosRM = abs(screenPosR.xy - 0.5);

            if (screenPosRM.x < rEdge.x && screenPosRM.y < rEdge.y
                && (!waterSurface || (abs(clipPosR.w) >= 0.000001
                    && min(screenPosR.x, screenPosR.y) > 0.0 && max(screenPosR.x, screenPosR.y) < 1.0))) {
                vec2 edgeFactor = pow2(pow2(pow2(screenPosRM / rEdge)));
                if (!waterSurface) screenPosR.y += (dither - 0.5) * (0.03 * (edgeFactor.x + edgeFactor.y) + 0.004);
                #ifdef DH_WATER
                    // Match depthtex1: opaque DH terrain, reconstructed with the DH projection.
                    float z1R = texture2D(dhDepthTex1, screenPosR.xy).x;
                #else
                    float z1R = texture2D(depthtex1, screenPosR.xy).x;
                #endif
                screenPosR.z = z1R;
                vec3 viewPosR = ScreenToView(screenPosR);
                float lViewPosR = length(viewPosR);

                #if defined DISTANT_HORIZONS && !defined DH_WATER
                    float z1RDH = texture2D(dhDepthTex1, screenPosR.xy).x;
                    vec4 screenPos1DH = vec4(screenPosR.xy, z1RDH, 1.0);
                    vec4 viewPos1DH = dhProjectionInverse * (screenPos1DH * 2.0 - 1.0);
                    viewPos1DH /= viewPos1DH.w;
                    lViewPosR = min(lViewPosR, length(viewPos1DH.xyz));
                    
                    z1R = min(z1R, z1RDH);
                #endif

                if (z1R < 0.9997 && lViewPos <= 2.0 + lViewPosR) {
                    reflection.rgb = texture2D(gaux2, screenPosR.xy).rgb;
                    reflection.rgb = pow2(reflection.rgb * 2.0);

                    edgeFactor = 1.0 - edgeFactor;
                    reflection.a = edgeFactor.x * pow2(edgeFactor.y);
                    if (waterSurface) {
                        float edgeDistance = min(min(screenPosR.x, screenPosR.y), min(1.0 - screenPosR.x, 1.0 - screenPosR.y));
                        reflection.a *= smoothstep(0.02, 0.12, edgeDistance);
                    }
                    reflection.a *= clamp01((dot(nViewPos, nViewPosR) - 0.45) * 10.0); // Fixes perpendicular ref bug

                    #ifdef BORDER_FOG
                        float fog = lViewPosR / renderDistance;
                        fog = pow2(pow2(fog));
                        #ifndef DISTANT_HORIZONS
                            fog = pow2(pow2(fog));
                        #endif
                        reflection.a *= exp(-3.0 * fog);
                    #endif
                }
            }
        }
        #endif
    #endif

    // ============================== End of Step 2 ============================== //

    // ============================== Step 3: Add Sky or WSR Reflection ============================== //
    #if defined COMPOSITE || WATER_REFLECT_QUALITY >= 1
        if (reflection.a < 1.0)
    #endif
    {
        AddBackgroundReflection(reflection, color, playerPos, normalM, normalMR, nViewPos, nViewPosR,
                                shadowMult, RVdotU, RVdotS, z0, dither, skyLightFactor, smoothness, highlightMult);
    } 
    // ============================== End of Step 3 ============================== //

    return reflection;
}