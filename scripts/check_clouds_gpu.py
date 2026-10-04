#!/usr/bin/env python3
"""Native macOS GPU checks of the actual cloud shape, lighting and integration.

Synthetic scenes exercise ray limits and quality consistency; Minecraft visual
and performance validation is still required. Writes /tmp/lumina-clouds-preview.png.
"""

import ctypes as c
import math
import random
import runpy
from pathlib import Path

h = runpy.run_path(str(Path(__file__).with_name("check_render_polish_gpu.py")))
g, program, draw, root, tex = (h[k] for k in ("g", "program", "draw", "root", "tex"))
shape = (root / "lib/atmospherics/clouds/cloudShape.glsl").read_text()
volume = (
    (root / "lib/atmospherics/clouds/luminaClouds.glsl")
    .read_text()
    .replace('#include "/lib/atmospherics/clouds/cloudShape.glsl"', "")
)
shadow = (
    (root / "lib/lighting/cloudShadows.glsl")
    .read_text()
    .replace('#include "/lib/atmospherics/clouds/cloudShape.glsl"', "")
)
fixture = """
#define texture2DLod textureLod
#define OVERWORLD
#define SHADOW_QUALITY -1
#define CLOUD_SPEED_MULT 100
#define LUMINA_CLOUD_SCALE 100
#define LUMINA_CLOUD_RAIN_DENSITY 0.40
uniform sampler2D noisetex;
uniform float rainFactor, syncedTime, frameTimeCounter, skyFade, terrainDistance;
uniform vec3 ray, cameraPosition;
const mat4 gbufferModelViewInverse = mat4(1.0);
const vec3 lightVec = vec3(0.4, 0.8, 0.2);
const int cloudAlt1i=192;
const float sunVisibility=1.0, invRainFactor=1.0, maxBlindnessDarkness=0.0, renderDistance=256.0;
const int isEyeInWater=0;
vec3 cloudAmbientColor=vec3(0.32,0.38,0.46);
vec3 cloudLightColor=vec3(0.8,0.77,0.7);
float pow2(float x){return x*x;}
vec3 GetSky(float u,float s,float d,bool a,bool b){return mix(vec3(0.45,0.65,0.85),vec3(0.15,0.35,0.65),max(u,0.0));}
out vec4 result;
"""
g.glActiveTexture(0x84C2)
noise = c.c_uint()
g.glGenTextures(1, c.byref(noise))
g.glBindTexture(0x0DE1, noise)
g.glTexParameteri(0x0DE1, 0x2801, 0x2601)
g.glTexParameteri(0x0DE1, 0x2800, 0x2601)
g.glTexParameteri(0x0DE1, 0x2802, 0x2901)
g.glTexParameteri(0x0DE1, 0x2803, 0x2901)


def upload(values, size):
    data = (c.c_float * len(values))(*values)
    g.glTexImage2D(0x0DE1, 0, 0x8814, size, size, 0, 0x1908, 0x1406, data)


def bind(p):
    g.glUseProgram(p)
    g.glUniform1i(g.glGetUniformLocation(p, b"noisetex"), 2)


def build(quality, coverage=1.0, reflection=False, body=None, speed=100):
    opts = (
        f"#define CLOUD_QUALITY {quality}\n#define LUMINA_CLOUD_COVERAGE {coverage}\n"
    )
    if not reflection:
        opts += "#define DEFERRED1\n"
    main = (
        body
        or "float depth=1.0;result=GetVolumetricClouds(192,4000.0,depth,skyFade,1.0,cameraPosition,normalize(ray),terrainDistance,0.5,normalize(ray).y,0.5);"
    )
    p = program(
        opts
        + fixture.replace(
            "#define CLOUD_SPEED_MULT 100", f"#define CLOUD_SPEED_MULT {speed}"
        )
        + shape
        + volume
        + shadow
        + "void main(){"
        + main
        + "}"
    )
    bind(p)
    return p


upload([0.85] * 4, 1)
outputs = []
for reflection in (False, True):
    for quality in (1, 2, 3):
        p = build(quality, reflection=reflection)
        for camera, ray in (
            ((112, 64, 112), (0, 1, 0)),
            ((112, 192, 112), (1, 0, 0)),
            ((112, 400, 112), (0, -1, 0)),
        ):
            v = draw(p, skyFade=1, terrainDistance=1e9, cameraPosition=camera, ray=ray)
            assert 0 < v[3] <= 1, (quality, camera, v)
        for camera, ray in (
            ((112, 64, 112), (1, 0, 0)),
            ((112, 400, 112), (0, 1, 0)),
            ((112, 64, 112), (0, -1, 0)),
        ):
            assert (
                draw(p, skyFade=1, terrainDistance=1e9, cameraPosition=camera, ray=ray)[
                    3
                ]
                == 0
            )
        assert (
            draw(
                p,
                skyFade=0,
                terrainDistance=32,
                cameraPosition=(112, 64, 112),
                ray=(0, 1, 0),
            )[3]
            == 0
        )
        outputs.append(
            draw(
                p,
                skyFade=1,
                terrainDistance=1e9,
                cameraPosition=(112, 64, 112),
                ray=(0, 1, 0),
            )[3]
        )
assert max(outputs) - min(outputs) < 0.025, outputs
print(
    "GPU clouds: all quality/reflection variants; slab, horizontal, inside and terrain clipping; opacity consistency.",
    flush=True,
)
upload([0.0] * 4, 1)
for quality in (1, 2, 3):
    p = build(quality)
    assert (
        draw(
            p, skyFade=1, terrainDistance=1e9, cameraPosition=(0, 64, 0), ray=(0, 1, 0)
        )[3]
        == 0
    )
upload([0.85] * 4, 1)
# Shared shape boundaries, coverage/rain monotonicity and empty-space behavior.
for coverage in (0.7, 1.0, 2.0):
    p = build(
        3, coverage, body="result=vec4(LuminaCloudShape(cameraPosition,192,0.0,false));"
    )
    for y in (0, 128, 256, 400):
        assert draw(p, cameraPosition=(0, y, 0))[0] == 0
upload([0.5] * 4, 1)
densities = []
for coverage in (0.7, 1.0, 2.0):
    p = build(
        3, coverage, body="result=vec4(LuminaCloudShape(cameraPosition,192,0.0,false));"
    )
    densities.append(draw(p, cameraPosition=(200, 180, 112), rainFactor=0)[0])
    assert draw(p, cameraPosition=(200, 180, 112), rainFactor=1)[0] >= densities[-1]
assert densities == sorted(densities) and densities[-1] > densities[0]
for quality in (0, 1, 2, 3):
    p = build(quality, body="result=vec4(GetCloudShadow(vec3(0.0)));")
    assert draw(p, cameraPosition=(112, 400, 112))[0] == 1
    v = draw(p, cameraPosition=(112, 64, 112))[0]
    assert 0.15 <= v <= 1
    if quality == 0:
        assert v == 1
print(
    "GPU clouds: bounded shared density, coverage/rain monotonicity, above-layer and disabled shadows.",
    flush=True,
)
# Periodic wrapping and spatially monotone weather controls across many clusters.
periodic = build(
    3, body="result=vec4(LuminaCloudShape(cameraPosition,192,0.0,false));", speed=0
)
for pos in ((112, 180, 112), (200, 180, 112), (700, 192, 1400)):
    a = draw(periodic, cameraPosition=pos)
    b = draw(periodic, cameraPosition=(pos[0] + 131072, pos[1], pos[2] - 131072))
    assert max(abs(x - y) for x, y in zip(a, b)) < 0.002, (pos, a, b)
print("GPU clouds: camera-wrap period preserves cloud density.", flush=True)
# Deterministic noise and a perspective sky fixture rendered by the actual integrator.
rng = random.Random(1404)
values = []
for i in range(128 * 128):
    value = rng.random()
    values.extend([value] * 4)
upload(values, 128)
densityBody = "result=vec4(LuminaCloudShape(cameraPosition,192,0.0,false));"
animated = build(3, body=densityBody)
frozen = build(3, body=densityBody, speed=0)
differences = []
for x in range(0, 2048, 128):
    pos = (x, 180, 450)
    a = draw(animated, cameraPosition=pos, syncedTime=0)[0]
    b = draw(animated, cameraPosition=pos, syncedTime=600)[0]
    differences.append(abs(a - b))
    assert draw(frozen, cameraPosition=pos, frameTimeCounter=0) == draw(
        frozen, cameraPosition=pos, frameTimeCounter=600
    )
assert max(differences) > 0.02
print("GPU clouds: wind changes the density field; zero speed freezes it.", flush=True)
p = build(
    3,
    body="vec2 uv=gl_FragCoord.xy/vec2(640.0,360.0);vec3 direction=normalize(vec3((uv.x-0.5)*1.8,uv.y*0.75+0.04,1.0));float depth=1.0;vec4 cloud=GetVolumetricClouds(192,4000.0,depth,1.0,1.0,cameraPosition,direction,1e9,dot(direction,normalize(lightVec)),direction.y,0.5);result=vec4(mix(GetSky(direction.y,0.0,0.0,true,false),cloud.rgb,cloud.a),cloud.a);",
)
g.glActiveTexture(0x84C0)
g.glBindTexture(0x0DE1, tex)
g.glTexImage2D(0x0DE1, 0, 0x8814, 640, 360, 0, 0x1908, 0x1406, None)
g.glViewport(0, 0, 640, 360)
draw(p, cameraPosition=(200, 64, 450), syncedTime=0)
output = (c.c_float * (640 * 360 * 4))()
g.glReadPixels(0, 0, 640, 360, 0x1908, 0x1406, output)
assert all(math.isfinite(v) for v in output)
alpha = list(output)[3::4]
clear_fraction = sum(v < 0.02 for v in alpha) / len(alpha)
cloud_fraction = sum(v > 0.2 for v in alpha) / len(alpha)
assert clear_fraction > 0.25 and 0.01 < cloud_fraction < 0.70, (
    clear_fraction,
    cloud_fraction,
)
print(
    f"GPU clear-day fixture: {clear_fraction:.1%} clear sky, {cloud_fraction:.1%} visible clouds.",
    flush=True,
)
from PIL import Image

rgb = bytes(
    round(max(0, min(1, v)) ** (1 / 2.2) * 255)
    for i, v in enumerate(output)
    if i % 4 != 3
)
Image.frombytes("RGB", (640, 360), rgb).transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(
    "/tmp/lumina-clouds-preview.png"
)
print("GPU preview: /tmp/lumina-clouds-preview.png", flush=True)
