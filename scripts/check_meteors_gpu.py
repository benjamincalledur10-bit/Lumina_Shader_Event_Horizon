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
#define METEORS 1
uniform int worldDay,testLane;
uniform float timeAngle,sunVisibility,invRainFactor,frameTimeCounter,testSlot,maxBlindnessDarkness;
uniform vec3 testRay,testCell;
uniform mat4 gbufferModelViewInverse;
out vec4 result;
"""
seed_program = program(
    fixture
    + source
    + "void main(){result=vec4(LuminaSkyEventSeed(testCell.xy,testSlot,testLane==1),1.0);}"
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
    scale = 3 if fireball else 6
    center = tuple((0.5 + (seed[i] - 0.5) * 0.16) / scale for i in range(2))
    raw = tuple(seed[i + 1] * 2 - 1 + center[i] * 0.6 for i in range(2))
    length = max(sum(x * x for x in raw), 0.0001) ** 0.5
    direction = tuple(x / length for x in raw)
    if sum(x * x for x in direction) < 0.1:
        direction = (0.6, 0.8)
    q = tuple(
        center[i] + direction[i] * ((progress - 0.5) * 0.32 / scale) for i in range(2)
    )
    squared = sum(x * x for x in q)
    return (
        2 * q[0] / (1 + squared),
        (1 - squared) / (1 + squared),
        2 * q[1] / (1 + squared),
    )


events = []
for lane in (0, 1):
    integer(seed_program, "testLane", lane)
    for slot in range(1000):
        seed = draw(seed_program, testSlot=slot)[:3]
        if seed[0] < (0.008 if lane == 1 else 0.01):
            break
    else:
        raise AssertionError("No seeded event found")
    p = program(
        fixture.replace("SHOOTING_STARS 1", f"SHOOTING_STARS {int(lane == 0)}").replace(
            "METEORS 1", f"METEORS {int(lane == 1)}"
        )
        + source
        + "void main(){result=vec4(GetLuminaMeteors(testRay),LuminaMeteorNightWindow());}"
    )
    matrix(p, identity)
    interval = (20, 67)[lane]
    duration = (1.6 + 0.8 * seed[1]) if lane == 1 else (0.55 + 0.35 * seed[1])
    delay = 1 + seed[2] * (interval - duration - 2)
    start = slot * interval + delay
    for progress in (0.2, 0.5, 0.8):
        direction = trajectory(seed, progress, lane == 1)
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
        if lane == 1 and progress == 0.5:
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
    p = program(
        fixture.replace("SHOOTING_STARS 1", f"SHOOTING_STARS {int(lane == 0)}").replace(
            "METEORS 1", f"METEORS {int(lane == 1)}"
        )
        + source
        + "void main(){result=vec4(GetLuminaMeteors(testRay),1.0);}"
    )
    matrix(p, identity)
    draw(p, timeAngle=0.75, sunVisibility=0, invRainFactor=1)
    direction = trajectory(seed, 0.99, lane == 1)
    after = draw(p, frameTimeCounter=start + duration + 0.001, testRay=direction)
    before = draw(
        p, frameTimeCounter=start - 0.001, testRay=trajectory(seed, 0, lane == 1)
    )
    assert max(after[:3]) == 0 and max(before[:3]) == 0, (before, after)
# Option off does not depend on the static-star or nebula options.
off = program(
    fixture.replace("SHOOTING_STARS 1", "SHOOTING_STARS 0").replace(
        "METEORS 1", "METEORS 0"
    )
    + source
    + "void main(){result=vec4(GetLuminaMeteors(testRay),1.0);}"
)
assert draw(off, testRay=direction, timeAngle=0.75, invRainFactor=1)[:3] == (0, 0, 0)
# Every independent frequency combination must compile and link on the GPU.
for stars in (0, 1, 5, 10, 50, 100):
    for meteors in (0, 1, 5):
        variant = program(
            fixture.replace("SHOOTING_STARS 1", f"SHOOTING_STARS {stars}").replace(
                "METEORS 1", f"METEORS {meteors}"
            )
            + source
            + "void main(){result=vec4(GetLuminaMeteors(testRay),1.0);}"
        )
        matrix(variant, identity)
        value = draw(variant, testRay=direction, timeAngle=0.75, invRainFactor=1)
        assert all(math.isfinite(x) for x in value)
# Higher frequency admits more deterministic candidates, without adding loops.
for fireball, frequencies in ((False, (1, 5, 10, 50, 100)), (True, (1, 5))):
    integer(seed_program, "testLane", int(fireball))
    seeds = [draw(seed_program, testSlot=slot)[0] for slot in range(300)]
    counts = [
        sum(x < min(f * (0.008 if fireball else 0.01), 1) for x in seeds)
        for f in frequencies
    ]
    assert counts == sorted(counts) and counts[-1] > counts[0], counts

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
