#!/usr/bin/env python3
"""Execute actual solar-axis, rain-streak and terrain-puddle blocks on OpenGL."""

import ctypes as c
import math
import runpy
from pathlib import Path

h = runpy.run_path(str(Path(__file__).with_name("check_render_polish_gpu.py")))
g, program, draw, root = (h[k] for k in ("g", "program", "draw", "root"))
common = (root / "lib/util/commonFunctions.glsl").read_text()
helpers = common[
    common.index("vec3 LuminaShadowLight") : common.index("float GetLuminance")
]
weather = (root / "program/gbuffers_weather.glsl").read_text()
streak = weather[weather.index("float LuminaRainStreak") : weather.index("//Program//")]
fixture = """
#define OVERWORLD
#define SHADOW_QUALITY 1
uniform mat4 gbufferModelView,shadowModelViewInverse;
uniform vec3 point;
uniform float timeAngle,clock;
out vec4 result;
"""
p = program(
    fixture + helpers + "void main(){result=vec4(LuminaShadowLight(vec3(1,0,0)),1);}"
)
g.glUniformMatrix4fv.argtypes = [c.c_int, c.c_int, c.c_ubyte, c.POINTER(c.c_float)]


def matrix(p, name, values):
    g.glUseProgram(p)
    g.glUniformMatrix4fv(
        g.glGetUniformLocation(p, name.encode()), 1, 0, (c.c_float * 16)(*values)
    )


identity = (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)
matrix(p, "gbufferModelView", identity)
last = None
for step in range(401):
    angle = -0.1 + step * 0.0005
    direction = (math.cos(angle), math.sin(angle), 0)
    # Third camera axis is the light direction in world space.
    m = list(identity)
    m[8:11] = direction
    matrix(p, "shadowModelViewInverse", m)
    v = draw(p, timeAngle=0.5 + angle)
    assert max(abs(a - b) for a, b in zip(v[:3], direction)) < 1e-6
    if last is not None:
        assert sum((a - b) ** 2 for a, b in zip(v, last)) ** 0.5 < 0.001
    last = v
print(
    "GPU solar: directional light follows shadow-camera axis continuously through the horizon."
)
ripple = program(
    fixture
    + helpers
    + "void main(){result=vec4(LuminaRainRipple(point.xz,clock),0,1);}"
)
changes = []
for x in range(32):
    a = draw(ripple, point=(x * 0.07, 0, 0.24), clock=0)
    b = draw(ripple, point=(x * 0.07, 0, 0.24), clock=0.25)
    assert all(math.isfinite(v) and abs(v) <= 1 for v in (*a, *b))
    changes.append(max(abs(a[i] - b[i]) for i in (0, 1)))
assert max(changes) > 0.001
rain = program(
    fixture + streak + "void main(){result=vec4(LuminaRainStreak(point.xy,clock));}"
)
values = [draw(rain, point=(i / 240, 0.31, 0), clock=0.1)[0] for i in range(240)]
assert all(0 <= v <= 1 for v in values) and max(values) > 0.1 and min(values) < 0.01
print("GPU rain: bounded thin streaks and animated, finite impact ripples.")
terrain = (root / "program/gbuffers_terrain.glsl").read_text()
block = terrain[
    terrain.index(
        "    #if defined OVERWORLD && RAIN_PUDDLES >= 1", terrain.index("//Program//")
    ) : terrain.index("    #if SHOW_LIGHT_LEVEL > 0")
]
puddle_fixture = """
#define texture2DLod textureLod
#define RAIN_PUDDLES 1
#define DETAIL_QUALITY 2
#define WATER_STYLE 3
uniform sampler2D noisetex;
uniform float wetness,rainFactor,inRainy,NdotUmax0;
uniform vec3 playerPos,cameraPosition;
const vec2 lmCoord=vec2(0,1);
const float noPuddles=0.,invNoonFactor=0.;
const int subsurfaceMode=0;
const mat3 tbnMatrix=mat3(1);
float max0(float x){return max(x,0.);}
float pow2(float x){return x*x;}
float sqrt1(float x){return sqrt(max(x,0.));}
"""
puddle = program(fixture + helpers + puddle_fixture + """void main(){
float frameTimeCounter=clock,lViewPos=length(playerPos);
vec4 color=vec4(1);vec3 normalM=vec3(0,0,1);
float smoothnessG=0.,smoothnessD=0.,highlightMult=1.;
""" + block + """result=vec4(smoothnessG,color.r,length(normalM.xy),1);}""")
g.glActiveTexture(0x84C2)
noise = c.c_uint()
g.glGenTextures(1, c.byref(noise))
g.glBindTexture(0x0DE1, noise)
g.glTexParameteri(0x0DE1, 0x2801, 0x2600)
g.glTexParameteri(0x0DE1, 0x2800, 0x2600)
g.glTexImage2D(
    0x0DE1, 0, 0x8814, 1, 1, 0, 0x1908, 0x1406, (c.c_float * 4)(0.8, 0.8, 0.8, 1)
)
g.glUseProgram(puddle)
g.glUniform1i(g.glGetUniformLocation(puddle, b"noisetex"), 2)
base = dict(
    rainFactor=1,
    inRainy=1,
    NdotUmax0=1,
    playerPos=(1, 0, 1),
    cameraPosition=(0, 0, 0),
    clock=0.2,
)
densities = [draw(puddle, wetness=w, **base)[0] for w in (0, 0.1, 0.3, 0.6, 1)]
assert (
    densities == sorted(densities) and densities[0] == 0 and densities[-1] > 0.7
), densities
wet = draw(puddle, wetness=1, **base)
assert wet[1] < 1
for key in ("inRainy", "NdotUmax0"):
    v = draw(puddle, wetness=1, **(base | {key: 0}))
    assert v[0] == 0 and v[1] == 1, v
remaining = draw(puddle, wetness=0.6, **(base | {"rainFactor": 0}))
assert remaining[0] > 0, remaining
print(
    "GPU puddles: accumulation monotonic, dry ground unchanged, rainy-biome/upward masks respected; residual wetness survives rain stopping."
)
