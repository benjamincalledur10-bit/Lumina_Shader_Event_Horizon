#!/usr/bin/env python3
"""Native/software GPU checks of the actual procedural meteor shader."""

import ctypes as c
import math
import runpy
from pathlib import Path

h = runpy.run_path(str(Path(__file__).with_name("check_render_polish_gpu.py")))
g, program, draw, root = (h[k] for k in ("g", "program", "draw", "root"))
source = (root / "lib/atmospherics/meteors.glsl").read_text()
fixture = """
#define SHOOTING_STARS 1
uniform int worldDay,testLane;
uniform float timeAngle,sunVisibility,invRainFactor,frameTimeCounter,testSlot,maxBlindnessDarkness;
uniform vec3 testRay;
uniform mat4 gbufferModelViewInverse;
out vec4 result;
"""
seed_program = program(
    fixture
    + source
    + "void main(){result=vec4(LuminaMeteorSeed(testSlot,testLane),1.0);}"
)
p = program(
    fixture
    + source
    + "void main(){result=vec4(GetLuminaMeteors(testRay),LuminaMeteorNightWindow());}"
)
g.glUniformMatrix4fv.argtypes = [c.c_int, c.c_int, c.c_ubyte, c.POINTER(c.c_float)]
identity = (c.c_float * 16)(1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)


def matrix(p, m):
    g.glUseProgram(p)
    g.glUniformMatrix4fv(g.glGetUniformLocation(p, b"gbufferModelViewInverse"), 1, 0, m)


def integer(p, name, value):
    g.glUseProgram(p)
    g.glUniform1i(g.glGetUniformLocation(p, name.encode()), value)


matrix(p, identity)
for angle in (0.0, 0.25, 0.5):
    assert (
        draw(p, timeAngle=angle, sunVisibility=0, invRainFactor=1, testRay=(0, 1, 0))[3]
        == 0
    )
values = [draw(p, timeAngle=t)[3] for t in (0.625, 0.65, 0.7, 0.75)]
assert values == sorted(values) and values[0] < 0.01 and values[-1] > 0.99, values
assert draw(p, timeAngle=0.75, invRainFactor=0)[3] == 0


# Find actual GPU-seeded events, then sample their head trajectories.
def unit(v):
    l = math.sqrt(sum(x * x for x in v))
    return tuple(x / l for x in v)


def trajectory(seed, progress, fireball):
    azimuth = seed[1] * 2 * math.pi
    elevation = 0.35 + 0.45 * seed[2]
    horizontal = math.sqrt(1 - elevation * elevation)
    start = (math.cos(azimuth) * horizontal, elevation, math.sin(azimuth) * horizontal)
    right = (-math.sin(azimuth), 0, math.cos(azimuth))
    up = unit(tuple((1 if i == 1 else 0) - start[i] * start[1] for i in range(3)))
    sign = -0.8 if seed[2] < 0.5 else 0.8
    travel = unit(tuple(right[i] * sign - up[i] * 0.6 for i in range(3)))
    angle = progress * (0.24 if fireball else 0.32)
    return tuple(
        start[i] * math.cos(angle) + travel[i] * math.sin(angle) for i in range(3)
    )


events = []
for lane in (0, 1, 2):
    integer(seed_program, "testLane", lane)
    for slot in range(30):
        seed = draw(seed_program, testSlot=slot)[:3]
        if seed[0] < (0.24 if lane == 2 else 0.55):
            break
    else:
        raise AssertionError("No seeded event found")
    interval = (13, 19, 67)[lane]
    duration = (1.6 + 0.8 * seed[1]) if lane == 2 else (0.55 + 0.35 * seed[1])
    delay = 1 + seed[2] * (interval - duration - 2)
    start = slot * interval + delay
    for progress in (0.2, 0.5, 0.8):
        direction = trajectory(seed, progress, lane == 2)
        v = draw(
            p,
            timeAngle=0.75,
            sunVisibility=0,
            invRainFactor=1,
            frameTimeCounter=start + duration * progress,
            testRay=direction,
        )
        assert all(math.isfinite(x) and x >= 0 for x in v), v
        assert max(v[:3]) > 0.1, (lane, progress, v)
        if lane == 2 and progress == 0.5:
            assert v[1] > v[0] and v[1] > v[2], v
        rain = draw(p, invRainFactor=0)
        assert max(rain[:3]) == 0, rain
        obscured = draw(p, invRainFactor=1, maxBlindnessDarkness=1)
        assert max(obscured[:3]) == 0, obscured
        draw(p, maxBlindnessDarkness=0)
        below = draw(p, invRainFactor=1, testRay=(0, -1, 0))
        assert max(below[:3]) == 0, below
    events.append((lane, seed, start, duration))
# Camera rotation preserves the same world event and intensity.
lane, seed, start, duration = events[-1]
direction = trajectory(seed, 0.5, True)
expected = draw(p, testRay=direction, frameTimeCounter=start + duration * 0.5)
rotation = (c.c_float * 16)(0, 0, -1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1)
matrix(p, rotation)
actual = draw(p, testRay=(-direction[2], direction[1], direction[0]))
assert max(abs(a - b) for a, b in zip(expected, actual)) < 0.01, (expected, actual)
matrix(p, identity)
# Slot boundaries are empty and event endpoints fade rather than pop.
for lane, seed, start, duration in events:
    direction = trajectory(seed, 0.99, lane == 2)
    after = draw(p, frameTimeCounter=start + duration + 0.001, testRay=direction)
    before = draw(
        p, frameTimeCounter=start - 0.001, testRay=trajectory(seed, 0, lane == 2)
    )
    assert max(after[:3]) == 0 and max(before[:3]) == 0, (before, after)
# Option off does not depend on the static-star or nebula options.
off = program(
    fixture.replace("SHOOTING_STARS 1", "SHOOTING_STARS 0")
    + source
    + "void main(){result=vec4(GetLuminaMeteors(testRay),1.0);}"
)
assert draw(off, testRay=direction, timeAngle=0.75, invRainFactor=1)[:3] == (0, 0, 0)
# Render the green event in a sky patch, including actual derivative filtering.
lane, seed, start, duration = events[-1]
direction = trajectory(seed, 0.5, True)
preview = program(
    fixture
    + source
    + """void main(){vec2 offset=(gl_FragCoord.xy/vec2(640.,360.)-.5)*.18;vec3 side=normalize(cross(testRay,vec3(0,1,0)));vec3 up=normalize(cross(side,testRay));vec3 ray=normalize(testRay+side*offset.x+up*offset.y);result=vec4(vec3(.003,.006,.015)+GetLuminaMeteors(ray),1.0);}"""
)
matrix(preview, identity)
g.glActiveTexture(0x84C0)
g.glBindTexture(0x0DE1, h["tex"])
g.glTexImage2D(0x0DE1, 0, 0x8814, 640, 360, 0, 0x1908, 0x1406, None)
g.glViewport(0, 0, 640, 360)
draw(
    preview,
    testRay=direction,
    timeAngle=0.75,
    sunVisibility=0,
    invRainFactor=1,
    frameTimeCounter=start + duration * 0.5,
)
output = (c.c_float * (640 * 360 * 4))()
g.glReadPixels(0, 0, 640, 360, 0x1908, 0x1406, output)
assert all(math.isfinite(x) for x in output)
from PIL import Image

rgb = bytes(
    round((max(x, 0) / (1 + max(x, 0))) ** (1 / 2.2) * 255)
    for i, x in enumerate(output)
    if i % 4 != 3
)
Image.frombytes("RGB", (640, 360), rgb).transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(
    "/tmp/lumina-meteors-preview.png"
)
print(
    "GPU meteors passed: midnight gating, rain/horizon suppression, all event trajectories, green entry, camera invariance, smooth endpoints and option off."
)
