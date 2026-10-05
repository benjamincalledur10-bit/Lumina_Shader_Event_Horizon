#!/usr/bin/env python3
"""Run native macOS GPU regression checks for the beta.3 water upgrade.

Uses the actual water/reflection GLSL with controlled lighting and scene fixtures.
Includes the previous rendering regressions. Does not replace in-game testing.
"""

import ctypes as c
import math
import re
import runpy
from pathlib import Path

h = runpy.run_path(str(Path(__file__).with_name("check_render_polish_gpu.py")))
g, program, draw, root, tex = (h[k] for k in ("g", "program", "draw", "root", "tex"))
g.glActiveTexture(0x84C2)
input_texture = c.c_uint()
g.glGenTextures(1, c.byref(input_texture))
g.glBindTexture(0x0DE1, input_texture)
pixels = (c.c_float * 4)(0.5, 0.5, 0.5, 0.5)
g.glTexImage2D(0x0DE1, 0, 0x8814, 1, 1, 0, 0x1908, 0x1406, pixels)
g.glTexParameteri(0x0DE1, 0x2801, 0x2600)
g.glTexParameteri(0x0DE1, 0x2800, 0x2600)


def integer(p, name, value):
    g.glUseProgram(p)
    g.glUniform1i(g.glGetUniformLocation(p, name.encode()), value)


def samplers(p, names):
    for name in names:
        integer(p, name, 2)


water = (root / "lib/materials/specificMaterials/translucents/water.glsl").read_text()
MATERIAL_FIXTURE = r"""
#define texture2D texture
#define texture2DLod textureLod
#define MC_VERSION 11300
#define WATERCOLOR_MODE 3
#define WATER_SPEED_MULT 1.10
#define WATER_SIZE_MULT 100
#define WATER_BUMPINESS 1.25
#define WATER_BUMP_SMALL 0.75
#define WATER_BUMP_MED 1.70
#define WATER_BUMP_BIG 2.00
#define WATER_FOG_MULT 100
#define WATER_ALPHA_MULT 100
#define WATER_FOAM_I 100
#define RAIN_PUDDLES 0
#define SUN_MOON_STYLE 2
#define WORLD_SPACE_REFLECTIONS_INTERNAL 0
#define BRIGHT_CAVE_WATER
uniform sampler2D depthtex1,dhDepthTex1,gaux4,noisetex;
uniform mat4 gbufferModelViewInverse;
uniform vec3 cameraPosition,bottomViewPos;
uniform vec4 glColor;
uniform float frameTimeCounter,rainFactor;
uniform int isEyeInWater;
float pow2(float x){return x*x;}
vec3 pow2(vec3 x){return x*x;}
float max0(float x){return max(x,0.0);}
float min1(float x){return min(x,1.0);}
float sqrt1(float x){return sqrt(max(x,0.0));}
vec3 sqrt1(vec3 x){return sqrt(max(x,vec3(0.0)));}
float sqrt2(float x){return sqrt(max(x,0.0));}
vec3 sqrt2(vec3 x){return sqrt(max(x,vec3(0.0)));}
float GetLuminance(vec3 x){return dot(x,vec3(.299,.587,.114));}
vec3 ScreenToView(vec3 p){return bottomViewPos;}
vec2 TAAJitter(vec2 p,float t){return p;}
uniform float testViewZ;
uniform int outputNormal;
out vec4 result;
void main(){
vec4 colorP=vec4(.25,.4,.5,.8),color=colorP,translucentMult=vec4(1.0);
bool translucentMultCalculated=false,noGeneratedNormals=false,noDirectionalShading=false;
vec2 lmCoord=vec2(.5,1),lmCoordM=lmCoord;
float fresnel=.3,fresnelM=.2,materialMask=0,reflectMult=0,highlightMult=1,smoothnessG=0,NdotU=1,NdotUmax0=1,miplevel=0,sunVisibility=.9;
const float OSIEBCA=1.0/255.0;
vec3 viewPos=vec3(0,-10,0),nViewPos=normalize(viewPos),playerPos=viewPos,screenPos=vec3(.5,.5,.5),normalM=vec3(0,1,0),normal=normalM,shadowMult=vec3(1),viewVector=vec3(0.2,0.3,testViewZ),lightVec=vec3(0,1,0);
float lViewPos=length(viewPos),far=256;
ivec2 texelCoord=ivec2(0);
mat3 tbnMatrix=mat3(1,0,0,0,0,1,0,1,0);
"""

for dimension in ("OVERWORLD", "NETHER", "END"):
    for path in ("GBUFFERS_WATER", "DH_WATER"):
        for style in (1, 2, 3):
            for quality in (1, 2, 3):
                defines = f"#define {dimension}\n#define {path}\n#define WATER_STYLE {style}\n#define WATER_MAT_QUALITY {quality}\n"
                p = program(
                    defines
                    + MATERIAL_FIXTURE
                    + water
                    + "\nresult=outputNormal==1?vec4(normalM,1):color;}"
                )
                samplers(p, ("depthtex1", "dhDepthTex1", "gaux4", "noisetex"))
                for underwater in (0, 1):
                    integer(p, "isEyeInWater", underwater)
                    for depth in (0.0, 0.5, 4.0, 16.0, 64.0):
                        integer(p, "outputNormal", 0)
                        v = draw(
                            p,
                            bottomViewPos=(0.0, -10.0 - depth, 0.0),
                            frameTimeCounter=37.0,
                            rainFactor=0.8,
                            testViewZ=0.0,
                        )
                        assert all(x >= 0 for x in v[:3]) and 0 <= v[3] <= 1, (
                            dimension,
                            path,
                            style,
                            quality,
                            v,
                        )
                        integer(p, "outputNormal", 1)
                        v = draw(
                            p,
                            bottomViewPos=(0.0, -10.0 - depth, 0.0),
                            frameTimeCounter=37.0,
                            rainFactor=0.8,
                            testViewZ=0.0,
                        )
                        assert all(abs(x) <= 1.00001 for x in v[:3]), v
                        assert 0.5 < sum(x * x for x in v[:3]) <= 1.00001, v
                if dimension == "OVERWORLD":
                    integer(p, "isEyeInWater", 0)
                    integer(p, "outputNormal", 0)
                    previous_alpha = -1.0
                    previous_rgb = (100.0, 100.0, 100.0)
                    for depth in (
                        0.0,
                        0.25,
                        0.5,
                        1.0,
                        2.0,
                        4.0,
                        8.0,
                        16.0,
                        32.0,
                        64.0,
                        128.0,
                    ):
                        v = draw(
                            p,
                            bottomViewPos=(0.0, -10.0 - depth, 0.0),
                            frameTimeCounter=0.0,
                            rainFactor=0.0,
                            testViewZ=-10.0,
                        )
                        assert v[3] >= previous_alpha - 1e-5, (
                            path,
                            style,
                            quality,
                            depth,
                            v,
                        )
                        assert all(v[i] <= previous_rgb[i] + 1e-5 for i in range(3)), (
                            path,
                            style,
                            quality,
                            depth,
                            v,
                        )
                        previous_alpha, previous_rgb = v[3], v[:3]
    print(
        f"GPU full water material passed: {dimension}, regular/DH, 3 styles, 3 qualities, above/below water.",
        flush=True,
    )

# Ensure extreme wave controls cannot flatten/invalidate the tangent normal.
fixture = MATERIAL_FIXTURE.replace(
    "#define WATER_BUMPINESS 1.25", "#define WATER_BUMPINESS 2.50"
)
for name in ("WATER_BUMP_SMALL", "WATER_BUMP_MED", "WATER_BUMP_BIG"):
    fixture = re.sub(
        r"#define " + name + r" [^\n]+", "#define " + name + " 5.0", fixture
    )
p = program(
    "#define OVERWORLD\n#define GBUFFERS_WATER\n#define WATER_STYLE 3\n#define WATER_MAT_QUALITY 3\n"
    + fixture
    + water
    + "\nresult=vec4(normalM,1);}"
)
samplers(p, ("depthtex1", "gaux4", "noisetex"))
for time in (0.0, 1.0, 10.0, 100.0, 10000.0):
    v = draw(
        p,
        bottomViewPos=(0.0, -74.0, 0.0),
        frameTimeCounter=time,
        rainFactor=1.0,
        testViewZ=0.0,
    )
    assert v[1] >= 0.6 - 1e-5 and abs(sum(x * x for x in v[:3]) - 1) < 1e-5, v
print(
    "GPU water optics: monotone opacity/attenuation at every quality; maximum wave sliders remain finite and bounded.",
    flush=True,
)

# Exercise the full reflection functions against a synthetic planar scene.
REFLECTION_FIXTURE = r"""
#define texture2D texture
#define texture2DLod textureLod
#define WORLD_SPACE_REFLECTIONS_INTERNAL -1
#define WORLD_SPACE_REF_MODE 2
#define COLORED_LIGHTING_INTERNAL 0
#define WATER_STYLE 3
#define DH_BLOCK_WATER 1
uniform int mat;
uniform float testDither;
uniform float testSkyLight;
uniform sampler2D depthtex1,dhDepthTex1,gaux2,colortex0;
uniform mat4 gbufferProjection,gbufferProjectionInverse,dhProjectionInverse;
uniform vec3 testPosition,testDirection;
float near=.1,far=100,renderDistance=100,refDistDummy=0,invRainFactor=1;
int isEyeInWater=0;
vec3 upVec=vec3(0,1,0),sunVec=normalize(vec3(0,1,-1)),lightVec=vec3(0,1,0),highlightColor=vec3(1);
float pow2(float x){return x*x;}
vec2 pow2(vec2 x){return x*x;}
vec3 pow2(vec3 x){return x*x;}
float clamp01(float x){return clamp(x,0.,1.);}
float GetLuminance(vec3 x){return dot(x,vec3(.299,.587,.114));}
float GGX(vec3 a,vec3 b,vec3 d,float e,float f){return 0.;}
vec3 GetSky(float a,float b,float d,bool e,bool f){return vec3(.2,.4,.8);}
vec3 GetLowQualitySky(float a,float b,float d,bool e,bool f){return vec3(.1,.2,.4);}
vec3 ViewToPlayer(vec3 p){return p;}
vec3 ScreenToView(vec3 p){vec4 v=gbufferProjectionInverse*vec4(p*2.-1.,1);return v.xyz/v.w;}
void DoFog(inout vec4 col,inout float sky,float len,vec3 pos,float u,float s,float d,bool ref,float dist){}
"""
REFLECTION_FIXTURE += """
#define SHOOTING_STARS 1
const mat4 gbufferModelViewInverse=mat4(1.0);
const int worldDay=0;
float timeAngle=0.25,sunVisibility=1.0,frameTimeCounter=0.0,maxBlindnessDarkness=0.0;
""" + (root / "lib/atmospherics/meteors.glsl").read_text()
reflection = (root / "lib/materials/materialMethods/reflections.glsl").read_text()
reflection = re.sub(r"^\s*#include[^\n]*", "", reflection, flags=re.MULTILINE)
background = (
    root / "lib/materials/materialMethods/reflectionBackground.glsl"
).read_text()
background = re.sub(r"^\s*#include[^\n]*", "", background, flags=re.MULTILINE)
g.glActiveTexture(0x84C3)
depth_texture = c.c_uint()
g.glGenTextures(1, c.byref(depth_texture))
g.glBindTexture(0x0DE1, depth_texture)
g.glTexParameteri(0x0DE1, 0x2801, 0x2600)
g.glTexParameteri(0x0DE1, 0x2800, 0x2600)
g.glUniformMatrix4fv.argtypes = [c.c_int, c.c_int, c.c_ubyte, c.POINTER(c.c_float)]
a = -(100 + 0.1) / (100 - 0.1)
b = -2 * 100 * 0.1 / (100 - 0.1)
projection = (c.c_float * 16)(1, 0, 0, 0, 0, 1, 0, 0, 0, 0, a, -1, 0, 0, b, 0)
inverse = (c.c_float * 16)(1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1 / b, 0, 0, -1, a / b)
for path in ("GBUFFERS_WATER", "DH_WATER"):
    for quality in (0, 1, 2, 3):
        for detail in (0, 2, 3):
            defines = f"#define OVERWORLD\n#define {path}\n#define WATER_REFLECT_QUALITY {quality}\n#define DETAIL_QUALITY {detail}\n"
            if path == "DH_WATER":
                defines += "#define DISTANT_HORIZONS\n"
            p = program(
                defines + REFLECTION_FIXTURE + background + "\n" + reflection + """
out vec4 result;
void main(){result=GetReflection(vec3(0,1,0),testPosition,normalize(testDirection),testPosition,length(testPosition),-1.,depthtex1,testDither,testSkyLight,.3,1.,vec3(0,1,0),vec3(.1),vec3(1),0.);}
"""
            )
            samplers(p, ("gaux2", "colortex0"))
            draw(p, testSkyLight=1.0)
            integer(p, "depthtex1", 3)
            integer(p, "dhDepthTex1", 3)
            integer(p, "mat", 32000 if path == "GBUFFERS_WATER" else 1)
            g.glUseProgram(p)
            for name, matrix in (
                ("gbufferProjection", projection),
                ("gbufferProjectionInverse", inverse),
                ("dhProjectionInverse", inverse),
            ):
                g.glUniformMatrix4fv(
                    g.glGetUniformLocation(p, name.encode()), 1, 0, matrix
                )
            for scene_depth in (
                1.0,
                100 / (100 - 0.1) - 100 * 0.1 / ((100 - 0.1) * 20),
            ):
                values = (c.c_float * 4)(scene_depth, scene_depth, scene_depth, 1.0)
                g.glTexImage2D(0x0DE1, 0, 0x8814, 1, 1, 0, 0x1908, 0x1406, values)
                for dither in (0.0, 0.5, 1.0):
                    v = draw(
                        p,
                        testPosition=(0.0, -1.0, -5.0),
                        testDirection=(0.0, -1.0, -5.0),
                        testDither=dither,
                    )
                    assert 0 <= v[3] <= 1, v
                    if quality == 0 or scene_depth == 1.0:
                        assert (
                            max(
                                abs(v[i] - expected)
                                for i, expected in enumerate((0.2, 0.4, 0.8))
                            )
                            < 1e-5
                        ), v
                        assert v[3] == 0, v
                    else:
                        assert v[3] > 0.05, (path, quality, detail, dither, v)
            # Cave hits must preserve colored HDR emitters even without sky light.
            if quality >= 2:
                for emitted in ((4.0, 0.05, 0.01), (0.01, 0.1, 6.0)):
                    g.glActiveTexture(0x84C2)
                    g.glBindTexture(0x0DE1, input_texture)
                    encoded = (c.c_float * 4)(
                        *(math.sqrt(x) * 0.5 for x in emitted), 1.0
                    )
                    g.glTexImage2D(0x0DE1, 0, 0x8814, 1, 1, 0, 0x1908, 0x1406, encoded)
                    for distance in (5.02, 5.12, 5.5, 7.0, 20.0):
                        g.glActiveTexture(0x84C3)
                        g.glBindTexture(0x0DE1, depth_texture)
                        depth = 100 / (100 - 0.1) - 100 * 0.1 / ((100 - 0.1) * distance)
                        values = (c.c_float * 4)(depth, depth, depth, 1.0)
                        g.glTexImage2D(
                            0x0DE1, 0, 0x8814, 1, 1, 0, 0x1908, 0x1406, values
                        )
                        cave = draw(
                            p,
                            testPosition=(0.0, -1.0, -5.0),
                            testDirection=(0.0, -1.0, -5.0),
                            testDither=0.5,
                            testSkyLight=0.0,
                        )
                        assert cave[3] > 0.95, (path, quality, distance, cave)
                        assert (
                            max(abs(cave[i] - emitted[i]) for i in range(3)) < 0.01
                        ), (emitted, cave)
                    g.glActiveTexture(0x84C2)
                    g.glBindTexture(0x0DE1, input_texture)
                g.glTexImage2D(0x0DE1, 0, 0x8814, 1, 1, 0, 0x1908, 0x1406, pixels)
                draw(p, testSkyLight=1.0)
                g.glActiveTexture(0x84C3)
                g.glBindTexture(0x0DE1, depth_texture)
            # Ray projection with zero W and off-screen rays must fall back to sky.
            for pos, direction in (
                ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
                ((0.0, -1.0, -5.0), (10.0, -1.0, -1.0)),
            ):
                v = draw(p, testPosition=pos, testDirection=direction, testDither=0.5)
                assert v[3] == 0, (path, quality, detail, pos, v)
            if quality == 3:
                center = draw(
                    p,
                    testPosition=(0.0, -1.0, -5.0),
                    testDirection=(0.0, -1.0, -5.0),
                    testDither=0.0,
                )
                stable = draw(
                    p,
                    testPosition=(0.0, -1.0, -5.0),
                    testDirection=(0.0, -1.0, -5.0),
                    testDither=1.0,
                )
                edge = draw(
                    p,
                    testPosition=(0.0, -1.0, -5.0),
                    testDirection=(6.0, -1.0, -5.0),
                    testDither=0.5,
                )
                assert max(abs(a - b) for a, b in zip(center, stable)) < 1e-6, (
                    center,
                    stable,
                )
                assert edge[3] < center[3], (edge, center)
    print(
        f"GPU full reflections passed: {path}, Sky only/Potato/Medium/High, 3 detail levels, valid terrain hits and sky/off-screen/zero-W fallbacks.",
        flush=True,
    )

# Verify visible animation at every quality and the speed-zero control.
for quality in (1, 2, 3):
    for speed in (0.0, 1.10):
        fixture = MATERIAL_FIXTURE.replace(
            "#define WATER_SPEED_MULT 1.10", f"#define WATER_SPEED_MULT {speed}"
        )
        p = program(
            f"#define OVERWORLD\n#define GBUFFERS_WATER\n#define WATER_STYLE 3\n#define WATER_MAT_QUALITY {quality}\n"
            + fixture
            + water
            + "\nresult=vec4(normalM,1);}"
        )
        samplers(p, ("depthtex1", "gaux4", "noisetex"))
        dry = draw(
            p,
            bottomViewPos=(0.0, -26.0, 0.0),
            frameTimeCounter=0.0,
            rainFactor=0.0,
            testViewZ=-10.0,
        )
        later = draw(
            p,
            bottomViewPos=(0.0, -26.0, 0.0),
            frameTimeCounter=10.0,
            rainFactor=0.0,
            testViewZ=-10.0,
        )
        difference = max(abs(a - b) for a, b in zip(dry, later))
        assert difference < 1e-6 if speed == 0.0 else difference > 1e-3, (
            quality,
            speed,
            difference,
        )
        wet = draw(
            p,
            bottomViewPos=(0.0, -26.0, 0.0),
            frameTimeCounter=0.0,
            rainFactor=1.0,
            testViewZ=-10.0,
        )
        assert wet[0] ** 2 + wet[2] ** 2 >= dry[0] ** 2 + dry[2] ** 2, (dry, wet)
print(
    "GPU animation passed: broad waves move at all qualities, rain increases slope, speed zero freezes movement.",
    flush=True,
)

# A black biome tint must not introduce NaNs into the transmission output.
p = program(
    "#define OVERWORLD\n#define GBUFFERS_WATER\n#define WATER_STYLE 3\n#define WATER_MAT_QUALITY 1\n"
    + MATERIAL_FIXTURE
    + water
    + "\nresult=translucentMult;}"
)
samplers(p, ("depthtex1", "gaux4", "noisetex"))
v = draw(
    p,
    bottomViewPos=(0.0, -14.0, 0.0),
    frameTimeCounter=0.0,
    rainFactor=0.0,
    testViewZ=-10.0,
)
assert all(x == 0 for x in v[:3]), v
print(
    "GPU zero-biome-tint transmission passed: finite output instead of zero-vector normalization.",
    flush=True,
)

# Bilinear reflection filtering must preserve linear HDR energy and clamp borders.
sample_function = reflection[
    reflection.index("vec3 SampleHighWaterReflection(") : reflection.index(
        "vec3 HighWaterScenePosition("
    )
]
p = program(
    "uniform sampler2D gaux2;uniform vec3 testUV;vec3 pow2(vec3 x){return x*x;}"
    + sample_function
    + "out vec4 result;void main(){result=vec4(SampleHighWaterReflection(testUV.xy),1);}"
)
integer(p, "gaux2", 2)
g.glActiveTexture(0x84C2)
encoded = (c.c_float * 16)(
    0, 0, 0, 1, 0.25, 0.25, 0.25, 1, 0.5, 0.5, 0.5, 1, 1, 1, 1, 1
)
g.glTexImage2D(0x0DE1, 0, 0x8814, 2, 2, 0, 0x1908, 0x1406, encoded)
for uv, expected in (
    ((0.5, 0.5, 0), 1.3125),
    ((0, 0, 0), 0),
    ((1, 1, 0), 4),
    ((-1, -1, 0), 0),
    ((2, 2, 0), 4),
):
    v = draw(p, testUV=uv)
    assert max(abs(x - expected) for x in v[:3]) < 1e-6, (uv, v, expected)
print(
    "GPU High reflection passed: no dither jitter, edge fading, linear HDR bilinear filtering and clamped borders.",
    flush=True,
)

# Regular High water must reconstruct distant hits with the DH near/far planes.
g.glActiveTexture(0x84C4)
empty_depth = c.c_uint()
g.glGenTextures(1, c.byref(empty_depth))
g.glBindTexture(0x0DE1, empty_depth)
g.glTexImage2D(0x0DE1, 0, 0x8814, 1, 1, 0, 0x1908, 0x1406, (c.c_float * 4)(1, 1, 1, 1))
g.glTexParameteri(0x0DE1, 0x2801, 0x2600)
g.glTexParameteri(0x0DE1, 0x2800, 0x2600)
g.glActiveTexture(0x84C3)
dh_depth = 1000 / 999 - 1000 / (999 * 20)
g.glTexImage2D(
    0x0DE1,
    0,
    0x8814,
    1,
    1,
    0,
    0x1908,
    0x1406,
    (c.c_float * 4)(dh_depth, dh_depth, dh_depth, 1),
)
p = program(
    "#define OVERWORLD\n#define GBUFFERS_WATER\n#define DISTANT_HORIZONS\n#define WATER_REFLECT_QUALITY 3\n#define DETAIL_QUALITY 2\n"
    + REFLECTION_FIXTURE
    + background
    + "\n"
    + reflection
    + """
out vec4 result;void main(){result=GetReflection(vec3(0,1,0),testPosition,normalize(testDirection),testPosition,length(testPosition),-1.,depthtex1,testDither,testSkyLight,.3,1.,vec3(0,1,0),vec3(.1),vec3(1),0.);}
"""
)
integer(p, "gaux2", 2)
integer(p, "depthtex1", 4)
integer(p, "dhDepthTex1", 3)
integer(p, "mat", 32000)
dh_a = -1001 / 999
dh_b = -2000 / 999
dh_inverse = (c.c_float * 16)(
    1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1 / dh_b, 0, 0, -1, dh_a / dh_b
)
for name, matrix in (
    ("gbufferProjection", projection),
    ("gbufferProjectionInverse", inverse),
    ("dhProjectionInverse", dh_inverse),
):
    g.glUniformMatrix4fv(g.glGetUniformLocation(p, name.encode()), 1, 0, matrix)
v = draw(
    p, testPosition=(0.0, -1.0, -5.0), testDirection=(0.0, -1.0, -5.0), testDither=0.5
)
assert v[3] > 0.9, v
print(
    "GPU High DH fallback passed: regular-depth sky and opaque DH hit with different near/far planes.",
    flush=True,
)
