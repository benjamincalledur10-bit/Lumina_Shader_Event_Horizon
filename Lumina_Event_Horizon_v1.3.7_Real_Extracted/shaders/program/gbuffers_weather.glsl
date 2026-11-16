/////////////////////////////////////
// Lumina Shader - Event Horizon //
/////////////////////////////////////

//Common//
#include "/lib/common.glsl"

//////////Fragment Shader//////////Fragment Shader//////////Fragment Shader//////////
#ifdef FRAGMENT_SHADER

flat in vec2 lmCoord;
in vec2 texCoord;

flat in vec3 upVec, sunVec;

flat in vec4 glColor;

//Pipeline Constants//

//Common Variables//
float SdotU = dot(sunVec, upVec);
float sunFactor = LUMINA_DAY_BLEND(SdotU);
float sunVisibility = LUMINA_SUN_VISIBILITY(SdotU);
float sunVisibility2 = sunVisibility * sunVisibility;

//Common Functions//

//Includes//
#include "/lib/colors/lightAndAmbientColors.glsl"

#ifdef COLOR_CODED_PROGRAMS
    #include "/lib/misc/colorCodedPrograms.glsl"
#endif

// Rain streaks retain the loader texture mask, so snow/resource-pack shapes survive.
float LuminaRainStreak(vec2 uv, float clock) {
    vec2 q = uv * vec2(24.0, 12.0);
    float column = floor(q.x);
    float seed = fract(sin(column * 127.1) * 43758.5453);
    float x = abs(fract(q.x) - 0.5);
    float y = fract(q.y + clock * 5.0 + seed);
    float aa = max(fwidth(q.x), 0.025);
    float core = 1.0 - smoothstep(0.08, 0.16 + aa, x);
    float tail = smoothstep(0.05, 0.20, y) * (1.0 - smoothstep(0.45, 0.95, y));
    return core * tail;
}

//Program//
void main() {
    vec4 color = texture2D(tex, texCoord);
    color *= glColor;

    if (color.a < 0.1 || isEyeInWater == 3) discard;

    if (color.r + color.g < 1.5) {
        float streak = LuminaRainStreak(texCoord, frameTimeCounter);
        color.a *= rainTexOpacity * mix(0.22, 1.35, streak);
        color.rgb = mix(color.rgb, vec3(dot(color.rgb, vec3(0.299, 0.587, 0.114))), 0.35);
    }
    else color.a *= snowTexOpacity;

    color.rgb = sqrt3(color.rgb) * (blocklightCol * 2.0 * lmCoord.x + (ambientColor + 0.2 * lightColor) * lmCoord.y * (0.6 + 0.3 * sunFactor));

    #ifdef COLOR_CODED_PROGRAMS
        ColorCodeProgram(color, -1);
    #endif

    /* DRAWBUFFERS:0 */
    gl_FragData[0] = color;
    #ifdef PBR_REFLECTIONS
        /* DRAWBUFFERS:04 */
        gl_FragData[1] = vec4(0);
    #endif
}

#endif

//////////Vertex Shader//////////Vertex Shader//////////Vertex Shader//////////
#ifdef VERTEX_SHADER

flat out vec2 lmCoord;
out vec2 texCoord;

flat out vec3 upVec, sunVec;

flat out vec4 glColor;

//Attributes//

//Common Variables//

//Common Functions//

//Includes//

//Program//
void main() {
    vec4 position = gbufferModelViewInverse * gl_ModelViewMatrix * gl_Vertex;
    glColor = gl_Color;

    #ifdef WAVING_RAIN
        float rainWavingFactor = eyeBrightnessM2; // Prevents clipping inside interiors
        position.xz += rainWavingFactor * (0.4 * position.y + 0.2) * vec2(sin(frameTimeCounter * 0.3) + 0.5, sin(frameTimeCounter * 0.5) * 0.5);
        position.xz *= 1.0 - 0.08 * position.y * rainWavingFactor;
    #endif

    gl_Position = gl_ProjectionMatrix * gbufferModelView * position;

    texCoord = (gl_TextureMatrix[0] * gl_MultiTexCoord0).xy;
    lmCoord  = GetLightMapCoordinates();

    upVec = normalize(gbufferModelView[1].xyz);
    sunVec = GetSunVector();
}

#endif
