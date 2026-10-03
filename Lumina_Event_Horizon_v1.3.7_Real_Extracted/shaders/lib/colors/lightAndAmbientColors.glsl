#ifndef INCLUDE_LIGHT_AND_AMBIENT_COLORS
    #define INCLUDE_LIGHT_AND_AMBIENT_COLORS

    #if defined OVERWORLD
        #ifndef COMPOSITE1
            vec3 noonClearLightColor = vec3(0.70, 0.62, 0.48) * 2.4; //ground and cloud color
        #else
            vec3 noonClearLightColor = vec3(0.4, 0.75, 1.3); //light shaft color
        #endif
        vec3 noonClearAmbientColor = pow(skyColor, vec3(0.85)) * vec3(0.75, 0.82, 1.15) * 0.85;

        #ifndef COMPOSITE1
            vec3 sunsetClearLightColor = pow(vec3(0.75, 0.35, 0.15), vec3(1.6 + invNoonFactor)) * 6.5; //ground and cloud color
        #else
            vec3 sunsetClearLightColor = pow(vec3(0.62, 0.39, 0.24), vec3(1.5 + invNoonFactor)) * 6.8; //light shaft color
        #endif
        vec3 sunsetClearAmbientColor   = noonClearAmbientColor * vec3(1.3, 0.75, 0.6) * 1.1;

        #if !defined COMPOSITE1 && !defined DEFERRED1
            vec3 nightClearLightColor = 0.8 * vec3(0.08, 0.10, 0.25) * (0.35 + vsBrightness * 0.45); //ground color
        #elif defined DEFERRED1
            vec3 nightClearLightColor = 0.8 * vec3(0.08, 0.12, 0.22); //cloud color
        #else
            vec3 nightClearLightColor = vec3(0.06, 0.10, 0.25); //light shaft color
        #endif
        vec3 nightClearAmbientColor   = 0.75 * vec3(0.06, 0.08, 0.15) * (1.6 + vsBrightness * 0.8);

        #ifdef SPECIAL_BIOME_WEATHER
            vec3 drlcSnowM = inSnowy * vec3(-0.06, 0.0, 0.04);
            vec3 drlcDryM = inDry * vec3(0.01, -0.035, -0.06);
        #else
            vec3 drlcSnowM = vec3(0.0), drlcDryM = vec3(0.0);
        #endif
        #if RAIN_STYLE == 2
            vec3 drlcRainMP = vec3(-0.03, 0.0, 0.02);
            #ifdef SPECIAL_BIOME_WEATHER
                vec3 drlcRainM = inRainy * drlcRainMP;
            #else
                vec3 drlcRainM = drlcRainMP;
            #endif
        #else
            vec3 drlcRainM = vec3(0.0);
        #endif
        vec3 dayRainLightColor   = vec3(0.21, 0.16, 0.13) * 0.85 + noonFactor * vec3(0.0, 0.02, 0.06)
                                 + drlcRainM + drlcSnowM + drlcDryM;
        vec3 dayRainAmbientColor = vec3(0.2, 0.2, 0.25) * (1.8 + 0.5 * vsBrightness);

        vec3 nightRainLightColor   = vec3(0.03, 0.035, 0.05) * (0.5 + 0.5 * vsBrightness);
        vec3 nightRainAmbientColor = vec3(0.16, 0.20, 0.3) * (0.75 + 0.6 * vsBrightness);

        #ifndef COMPOSITE1
            float noonFactorDM = noonFactor; //ground and cloud factor
        #else
            float noonFactorDM = noonFactor * noonFactor; //light shaft factor
        #endif
        // Lumina daylight palette: warm sunlight, gently cool skylight.
        // Preserve luminance so this color pass does not alter exposure/contrast.
        // Fade the extra warmth at sunset, where the existing light is already orange.
        vec3 dayLightColorBase = mix(sunsetClearLightColor, noonClearLightColor, noonFactorDM);
        vec3 dayAmbientColorBase = mix(sunsetClearAmbientColor, noonClearAmbientColor, noonFactorDM);
        vec3 dayLightTint = mix(vec3(1.0), vec3(1.04, 1.0, 0.94), noonFactorDM);
        vec3 dayAmbientTint = mix(vec3(1.0), vec3(0.96, 1.0, 1.04), 0.5 + 0.5 * noonFactorDM);
        vec3 paletteLumaWeights = vec3(0.299, 0.587, 0.114);
        vec3 dayLightColor = dayLightColorBase * dayLightTint
                          * (dot(dayLightColorBase, paletteLumaWeights)
                          / max(dot(dayLightColorBase * dayLightTint, paletteLumaWeights), 1e-6));
        vec3 dayAmbientColor = dayAmbientColorBase * dayAmbientTint
                            * (dot(dayAmbientColorBase, paletteLumaWeights)
                            / max(dot(dayAmbientColorBase * dayAmbientTint, paletteLumaWeights), 1e-6));

        vec3 clearLightColor   = mix(nightClearLightColor, dayLightColor, sunVisibility2);
        vec3 clearAmbientColor = mix(nightClearAmbientColor, dayAmbientColor, sunVisibility2);

        float rainShadowVisReduce = 0.0
            #ifdef SUN_MOON_DURING_RAIN
                #ifdef SPECIAL_BIOME_WEATHER
                    + 0.2 * inSnowy + 0.2 * inDry
                #elif RAIN_STYLE == 2
                    + 0.2
                #endif
            #else
                + 0.4
            #endif
        ;

        vec3 rainLightColor   = mix(nightRainLightColor, dayRainLightColor * (1.0 - rainShadowVisReduce), sunVisibility2) * 2.5;
        vec3 rainAmbientColor = mix(nightRainAmbientColor, dayRainAmbientColor * (1.0 + rainShadowVisReduce), sunVisibility2);

        vec3 lightColor   = mix(clearLightColor, rainLightColor, rainFactor);
        vec3 ambientColor = mix(clearAmbientColor, rainAmbientColor, rainFactor);
    #elif defined NETHER
        vec3 lightColor   = vec3(0.0);
        vec3 ambientColor = (netherColor + 0.5 * lavaLightColor) * (0.9 + 0.45 * vsBrightness);
    #elif defined END
        // Lumina cosmic palette: precomputed tint preserves the existing luminance.
        vec3 endLightColor = vec3(0.65616497, 0.51495421, 1.10700483);
        vec3 endOrangeCol = vec3(1.0, 0.3, 0.0);
        float endLightBalancer = 0.2 * vsBrightness;
        vec3 lightColor    = endLightColor * (0.35 - endLightBalancer);
        vec3 ambientColor  = endLightColor * (0.2 + endLightBalancer);
    #endif

#endif //INCLUDE_LIGHT_AND_AMBIENT_COLORS