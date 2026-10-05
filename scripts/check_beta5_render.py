#!/usr/bin/env python3
"""Execute beta.5 GLSL using macOS OpenGL or Linux Mesa software OpenGL.

Tests cinematic depth boundaries, aperture quality variants, exact light
alignment, shadow twilight continuity and volumetric air/water integration.
Does not measure Minecraft performance or replace in-game visual testing.
"""

import ctypes as c
import math
import re
import runpy
from pathlib import Path

h = runpy.run_path(str(Path(__file__).with_name("check_render_polish_gpu.py")))
g, program, draw, root = (h[k] for k in ("g", "program", "draw", "root"))


def integer(p, name, value):
    g.glUseProgram(p)
    g.glUniform1i(g.glGetUniformLocation(p, name.encode()), value)


def texture(unit, values, size=1):
    g.glActiveTexture(0x84C0 + unit)
    handle = c.c_uint()
    g.glGenTextures(1, c.byref(handle))
    g.glBindTexture(0x0DE1, handle)
    data = (c.c_float * len(values))(*values)
    g.glTexImage2D(0x0DE1, 0, 0x8814, size, size, 0, 0x1908, 0x1406, data)
    g.glTexParameteri(0x0DE1, 0x2801, 0x2600)
    g.glTexParameteri(0x0DE1, 0x2800, 0x2600)
    g.glTexParameteri(0x0DE1, 0x2802, 0x812F)
    g.glTexParameteri(0x0DE1, 0x2803, 0x812F)
    g.glGenerateMipmap(0x0DE1)
    return handle


# Use real perspective depths (hand masking uses non-linear depth < .56).
def depth(distance):
    return 100.0 * (distance - 0.1) / (distance * 99.9)


source = (root / "program/composite3.glsl").read_text()
blur = source[
    source.index("#if WORLD_BLUR > 0\n    // Axial") : source.index("//Includes//")
]
BLUR_FIXTURE = """
#define texture2DLod textureLod
uniform sampler2D colortex0, depthtex1, dhDepthTex1;
uniform vec3 inputColor;
uniform float testDepth;
uniform int frameCounter;
const vec2 texCoord=vec2(0.5);
const float viewWidth=32.0,viewHeight=1080.0,aspectRatio=32.0/1080.0;
const float far=100.0,near=0.1,vsBrightness=0.5,WB_AF_STRENGTH=1.0;
const float centerDepthSmooth=0.990990991;
const float WB_DB_NIGHT_I=1.0, WB_DB_DAY_I=1.0, WB_DB_RAIN_I=1.0, WB_DB_WATER_I=1.0;
const float WB_DB_NETHER_I=1.0, WB_DB_END_I=1.0, WB_DOF_I=1.0;
const float sunFactor=1.0,eyeBrightnessM=1.0,rainFactor=0.0;
const int isEyeInWater=0;
const mat4 gbufferProjection=mat4(1.0);
const mat4 gbufferProjectionInverse=mat4(1,0,0,0,0,1,0,0,0,0,0,-4.995,0,0,-1,5.005);
const mat4 dhProjectionInverse=gbufferProjectionInverse;
float pow2(float x){return x*x;}
out vec4 result;
"""
texture(2, [0.4, 0.2, 0.1, 1] * 1024, 32)
texture(3, [depth(64)] * 4096, 32)
texture(4, [depth(64)] * 4096, 32)
for quality in (16, 32, 48, 64, 96):
    for taa in (False, True):
        for dh in (False, True):
            defines = f"#define WORLD_BLUR 3\n#define OVERWORLD\n#define WB_DOF_FOCUS 8\n#define WB_AF_QUALITY {quality}\n"
            if taa:
                defines += "#define TAA\n"
            if dh:
                defines += "#define DISTANT_HORIZONS\n"
            p = program(
                defines
                + BLUR_FIXTURE
                + blur
                + "void main(){vec3 color=inputColor;DoWorldBlur(color,testDepth,64.0);result=vec4(color,1);}"
            )
            for name, unit in (("colortex0", 2), ("depthtex1", 3), ("dhDepthTex1", 4)):
                integer(p, name, unit)
            for d in (depth(2), depth(8), depth(64), 1):
                actual = draw(p, inputColor=(0.4, 0.2, 0.1), testDepth=d)
                assert (
                    max(abs(actual[k] - v) for k, v in enumerate((0.4, 0.2, 0.1)))
                    < 1e-4
                ), (quality, taa, dh, d, actual)
            integer(p, "frameCounter", 7)
            assert (
                draw(p, inputColor=(0.8, 0.3, 0.1), testDepth=depth(8))[:3]
                == draw(p, inputColor=(0.8, 0.3, 0.1), testDepth=depth(2))[:3]
            )
# A bright foreground silhouette must not bleed into the defocused background.
colors = []
depths = []
for y in range(32):
    for x in range(32):
        front = x < 8
        colors.extend((8, 0, 0, 1) if front else (0, 0, 1, 1))
        depths.extend([depth(2 if front else 64)] * 4)
texture(2, colors, 32)
texture(3, depths, 32)
for quality in (16, 32, 48, 64, 96):
    p = program(
        f"#define WORLD_BLUR 3\n#define OVERWORLD\n#define WB_DOF_FOCUS 8\n#define WB_AF_QUALITY {quality}\n"
        + BLUR_FIXTURE
        + blur
        + "void main(){vec3 color=inputColor;DoWorldBlur(color,testDepth,64.0);result=vec4(color,1);}"
    )
    integer(p, "colortex0", 2)
    integer(p, "depthtex1", 3)
    v = draw(p, inputColor=(0, 0, 1), testDepth=depth(64))
    assert v[0] < 1e-4 and abs(v[2] - 1) < 1e-4, (quality, v)
print(
    "Render cinematic: 20 quality/TAA/DH variants, constant-color energy, focus/foreground protection, bright silhouette rejection.",
    flush=True,
)

functions = (root / "lib/util/commonFunctions.glsl").read_text()
fade = re.search(r"^\s*#define LUMINA_SHADOW_FADE[^\n]+", functions, re.M).group(0)
p = program(
    fade
    + "\nuniform float elevation;out vec4 result;void main(){result=vec4(LUMINA_SHADOW_FADE(elevation));}"
)
previous = 0
for i in range(301):
    value = i * 0.001
    v = draw(p, elevation=value)[0]
    assert 0 <= v <= 1 and v >= previous - 1e-6
    assert abs(v - draw(p, elevation=-value)[0]) < 1e-6
    previous = v
assert draw(p, elevation=0)[0] == 0 and draw(p, elevation=0.2)[0] == 1
sun = functions[
    functions.index("    vec3 GetSunVector()") : functions.index(
        "\n#endif", functions.index("    vec3 GetSunVector()")
    )
]
p = program(
    "#define OVERWORLD\nuniform vec3 sunPosition;out vec4 result;"
    + sun
    + "\nvoid main(){result=vec4(GetSunVector(),1);}"
)
for angle in (0, 0.01, 0.25, 0.49, 0.5, 0.51, 0.75, 0.99, 1):
    pos = (math.sin(angle * math.tau) * 100, math.cos(angle * math.tau) * 100, 0)
    v = draw(p, sunPosition=pos)
    assert max(abs(v[k] - pos[k] / 100) for k in range(3)) < 1e-5
print(
    "Render shadows: continuous symmetric horizon fade and exact loader solar direction.",
    flush=True,
)

volume = (
    (root / "lib/atmospherics/volumetricLight.glsl")
    .read_text()
    .replace('#include "/lib/colors/lightAndAmbientColors.glsl"', "")
)
VOLUME_FIXTURE = """
#define OVERWORLD
#define SHADOW_QUALITY 1
#define WATER_FOG_MULT 100
#define LIGHTSHAFT_BEHAVIOUR 0
#define LIGHTSHAFT_SUNSET_SATURATION 0.5
#define LIGHTSHAFT_DAY_I 100
#define LIGHTSHAFT_NIGHT_I 100
#define LIGHTSHAFT_RAIN_I 100
#define texture2D texture
#define texture2DLod textureLod
#define shadow2D shadowCompat
uniform sampler2D shadowtex0,shadowcolor1,depthtex0,dhDepthTex1,dhDepthTex;
uniform sampler2DShadow shadowtex1;
uniform vec3 ray,transmission;
uniform float distance0,distance1,rainFactor,sunVisibility;
uniform int isEyeInWater;
const float near=0.1,far=256.0,shadowMapBias=0.5,maxBlindnessDarkness=0.0;
const float rainFactor2=0.0,nightFactor=0.0,vsBrightness=0.5,vlTime=1.0;
const float invNoonFactor2=0.5,invNoonFactor=0.5,noonFactor=0.5,invRainFactor=1.0;
const float renderDistance=256.0,oceanAltitude=64.0;
const vec3 cameraPosition=vec3(0,60,0),lightColor=vec3(1),lightVec=normalize(vec3(0.2,0.9,0.3));
const mat4 gbufferModelViewInverse=mat4(1.0),gbufferProjectionInverse=mat4(1.0),dhProjectionInverse=mat4(1.0);
const mat4 shadowModelView=mat4(0.01,0,0,0,0,0.01,0,0,0,0,0.01,0,0,0,0,1),shadowProjection=mat4(1.0);
float pow2(float x){return x*x;}
vec3 pow2(vec3 x){return x*x;}
float max0(float x){return max(x,0.0);}
float min1(float x){return min(x,1.0);}
float clamp01(float x){return clamp(x,0.0,1.0);}
float smoothstep1(float x){return x*x*(3.0-2.0*x);}
float sqrt1(float x){return sqrt(max(x,0.0));}
vec4 shadowCompat(sampler2DShadow s,vec3 p){return vec4(1.0);}
float Noise3D(vec3 p){return 0.5;}
out vec4 result;
"""
texture(5, [1] * 4)
texture(6, [0, 0, 0, 0])
for quality in (1, 2, 3, 4):
    for taa in (False, True):
        defines = f"#define LIGHTSHAFT_QUALI {quality}\n"
        if taa:
            defines += "#define TAA\n"
        p = program(
            defines
            + VOLUME_FIXTURE
            + volume
            + "void main(){vec3 color=vec3(0);float factor=.7;result=GetVolumetricLight(color,factor,transmission,distance0,distance1,normalize(ray),.8,.5,vec2(.5),.9,.9,.5);}"
        )
        integer(p, "shadowtex0", 5)
        integer(p, "shadowcolor1", 6)
        integer(p, "isEyeInWater", 0)
        v = draw(
            p,
            ray=(0, 0, -1),
            transmission=(1, 1, 1),
            distance0=64,
            distance1=64,
            sunVisibility=1,
        )
        assert v[0] > 0 and all(x >= 0 for x in v), (quality, taa, v)
        empty = draw(
            p,
            ray=(0, 0, -1),
            transmission=(1, 1, 1),
            distance0=0,
            distance1=0,
            sunVisibility=1,
        )
        assert max(empty) < 1e-5, empty
        integer(p, "isEyeInWater", 1)
        v = draw(
            p,
            ray=(0, 0, -1),
            transmission=(0.6, 0.8, 0.9),
            distance0=0,
            distance1=64,
            sunVisibility=1,
        )
        assert 0 < v[0] < v[1] < v[2], (quality, taa, v)
        integer(p, "isEyeInWater", 0)
        texture(5, [0] * 4)
        v = draw(
            p,
            ray=(0, 0, -1),
            transmission=(1, 1, 1),
            distance0=64,
            distance1=64,
            sunVisibility=1,
        )
        assert max(v[:3]) < 1e-5, (quality, taa, v)
        texture(5, [1] * 4)
print(
    "Render rays: every quality/TAA variant compiles; air, zero path, opaque occlusion and wavelength-dependent underwater attenuation verified.",
    flush=True,
)
