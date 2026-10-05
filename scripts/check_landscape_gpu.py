#!/usr/bin/env python3
"""Render the actual landscape fog GLSL on native or software OpenGL."""

import math
import re
import runpy
from pathlib import Path

h = runpy.run_path(str(Path(__file__).with_name("check_render_polish_gpu.py")))
g, program, draw, root = (h[k] for k in ("g", "program", "draw", "root"))
source = (root / "lib/atmospherics/fog/mainFog.glsl").read_text()
atmosphere = source[
    source.index("#ifdef ATMOSPHERIC_FOG") : source.index(
        '#include "/lib/atmospherics/fog/waterFog.glsl"'
    )
]
atmosphere = re.sub(r"^\s*#include[^\n]*", "", atmosphere, flags=re.M)
fixture = """
#define OVERWORLD
#define ATMOSPHERIC_FOG
#define CAVE_FOG
#define ATM_FOG_ALTITUDE 63
#define ATM_FOG_DISTANCE 100
#define ATM_FOG_MULT 0.95
#define RAIN_STYLE 1
uniform vec3 cameraPosition, testPosition, inputColor;
uniform float testDistance, rainFactor, eyeBrightnessM, testCave, daylight;
uniform int isEyeInWater;
const float renderDistance=256.0;
float invRainFactor, rainFactor2, sunVisibility, sunVisibility2, invNightFactor, noonFactor;
vec3 nightUpSkyColor=vec3(0.01,0.02,0.05),dayDownSkyColor=vec3(0.38,0.55,0.8);
float pow2(float x){return x*x;}
float sqrt2(float x){return sqrt(sqrt(max(x,0.0)));}
float min1(float x){return min(x,1.0);}
float max0(float x){return max(x,0.0);}
float GetCaveFactor(){return testCave;}
out vec4 result;
"""
setup = "invRainFactor=1.-rainFactor;rainFactor2=rainFactor*rainFactor;sunVisibility=daylight;sunVisibility2=daylight*daylight;invNightFactor=daylight;noonFactor=daylight;"
programs = []
for dh in (False, True):
    prefix = "#define DISTANT_HORIZONS\n" if dh else ""
    p = program(
        prefix
        + fixture
        + atmosphere
        + "void main(){"
        + setup
        + "vec4 color=vec4(inputColor,1.);DoAtmosphericFog(color,testPosition,testDistance,0.0);result=color;}"
    )
    programs.append(p)
    for altitude in (64.0, 180.0, 400.0):
        alphas = []
        for distance in (0.0, 24.0, 96.0, 256.0, 512.0, 1024.0, 4096.0):
            v = draw(
                p,
                cameraPosition=(0, 64, 0),
                testPosition=(0, altitude - 64, 0),
                testDistance=distance,
                inputColor=(0.02, 0.04, 0.08),
                rainFactor=0,
                eyeBrightnessM=1,
                testCave=0,
                daylight=1,
            )
            assert all(math.isfinite(x) and 0 <= x <= 1 for x in v), v
            alphas.append(v[3])
        assert alphas == sorted(alphas, reverse=True), alphas
        assert alphas[0] == 1 and alphas[-1] < 0.6, alphas
    for cave, eye in ((1, 1), (0, 0)):
        v = draw(
            p,
            cameraPosition=(0, 64, 0),
            testPosition=(0, 100, 0),
            testDistance=1000,
            inputColor=(0.2, 0.3, 0.1),
            testCave=cave,
            eyeBrightnessM=eye,
        )
        assert max(abs(v[i] - x) for i, x in enumerate((0.2, 0.3, 0.1, 1))) < 1e-5, v
# Clear-weather terrain shares precisely the same fog law across the DH boundary.
for distance in (128, 255.9, 256, 256.1, 512, 2000):
    values = [
        draw(
            p,
            cameraPosition=(0, 64, 0),
            testPosition=(0, 160, 0),
            testDistance=distance,
            inputColor=(0.15, 0.25, 0.08),
            rainFactor=0,
            eyeBrightnessM=1,
            testCave=0,
            daylight=1,
        )
        for p in programs
    ]
    assert max(abs(a - b) for a, b in zip(*values)) < 1e-5, values
# Rain transitions remain continuous; HDR highlights stay finite at extreme paths.
for p in programs:
    last = None
    for rain in (0, 0.001, 0.25, 0.5, 0.75, 0.999, 1):
        v = draw(
            p,
            cameraPosition=(0, 64, 0),
            testPosition=(0, 180, 0),
            testDistance=700,
            inputColor=(4, 1, 0.1),
            rainFactor=rain,
            eyeBrightnessM=1,
            testCave=0,
            daylight=1,
        )
        assert all(math.isfinite(x) and x >= 0 for x in v), v
        if last is not None and rain == 1:
            assert max(abs(a - b) for a, b in zip(v, last)) < 0.02, (v, last)
        last = v
    draw(p, rainFactor=0)
# Higher camera/target paths contain less haze, but mountain-top haze remains.
p = programs[0]
low = draw(p, cameraPosition=(0, 64, 0), testPosition=(0, 0, 0), testDistance=1000)[3]
high = draw(p, cameraPosition=(0, 300, 0), testPosition=(0, 0, 0), testDistance=1000)[3]
assert low < high < 1, (low, high)
# Spectral attenuation retains more blue-channel scene contrast at long range.
dark = draw(
    p, cameraPosition=(0, 64, 0), testPosition=(0, 100, 0), inputColor=(0.1, 0.1, 0.1)
)[0:3]
bright = draw(p, inputColor=(0.2, 0.2, 0.2))[0:3]
contrast = [b - a for a, b in zip(dark, bright)]
assert 0 < contrast[0] < contrast[1] < contrast[2], contrast
# Terrain chroma is restrained, preserves neutrals, and is inactive nearby/night/rain.
p = program(
    fixture
    + atmosphere
    + "void main(){"
    + setup
    + "result=vec4(LuminaTerrainColor(inputColor,testDistance),1.);}"
)
for color in ((0, 0, 0), (0.2, 0.2, 0.2), (4, 4, 4)):
    v = draw(
        p,
        inputColor=color,
        testDistance=256,
        daylight=1,
        rainFactor=0,
        eyeBrightnessM=1,
    )
    assert max(abs(v[i] - color[i]) for i in range(3)) < 1e-5, v
for distance, day, rain in ((0, 1, 0), (256, 0, 0), (256, 1, 1)):
    v = draw(
        p,
        inputColor=(0.1, 0.3, 0.05),
        testDistance=distance,
        daylight=day,
        rainFactor=rain,
    )
    assert max(abs(v[i] - x) for i, x in enumerate((0.1, 0.3, 0.05))) < 1e-5, v
v = draw(p, inputColor=(0.1, 0.3, 0.05), testDistance=256, daylight=1, rainFactor=0)
assert v[1] > 0.3 and 0 < v[2] < 0.05, v
print(
    "GPU landscape passed: distance/height haze, DH continuity, cave isolation, spectral contrast and restrained daylight terrain color.",
    flush=True,
)

# Synthetic mountain layers rendered through the actual shared fog/color functions.
import ctypes as c
from PIL import Image

p = program(fixture + atmosphere + "void main(){" + setup + """
vec2 uv=gl_FragCoord.xy/vec2(640.0,360.0);
vec3 sky=mix(vec3(0.46,0.65,0.84),vec3(0.15,0.33,0.60),uv.y);
vec4 color=vec4(sky,1.0);
for(int layer=0;layer<3;layer++){
    float index=float(layer);
    float crest=0.54-index*0.11+sin(uv.x*(10.0+index*4.0)+index*2.0)*0.055
                 +sin(uv.x*27.0+index)*0.018;
    if(uv.y<crest){
        float distance=1400.0/(1.0+index*2.5);
        float relief=clamp(0.65+(crest-uv.y)*2.0+sin(uv.x*29.0+index)*0.12,0.4,1.1);
        vec3 terrain=vec3(0.12,0.22,0.07)*relief;
        color=vec4(LuminaTerrainColor(terrain,distance),1.0);
        DoAtmosphericFog(color,vec3(0.0,180.0-index*50.0,0.0),distance,0.0);
    }
}
result=vec4(color.rgb,1.0);
}""")
g.glActiveTexture(0x84C0)
g.glBindTexture(0x0DE1, h["tex"])
g.glTexImage2D(0x0DE1, 0, 0x8814, 640, 360, 0, 0x1908, 0x1406, None)
g.glViewport(0, 0, 640, 360)
draw(
    p, cameraPosition=(0, 64, 0), daylight=1, rainFactor=0, eyeBrightnessM=1, testCave=0
)
output = (c.c_float * (640 * 360 * 4))()
g.glReadPixels(0, 0, 640, 360, 0x1908, 0x1406, output)
assert all(math.isfinite(x) for x in output)
rgb = bytes(
    round(max(0, min(1, x)) ** (1 / 2.2) * 255)
    for i, x in enumerate(output)
    if i % 4 != 3
)
Image.frombytes("RGB", (640, 360), rgb).transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(
    "/tmp/lumina-landscape-preview.png"
)
print("GPU synthetic landscape preview: /tmp/lumina-landscape-preview.png", flush=True)
