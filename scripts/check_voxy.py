#!/usr/bin/env python3
"""Voxy API-1/VOXY-3 contract, GLSL compilation and isolated native GPU checks.

This models the documented upstream injection ABI; it does not launch Voxy/Iris.
Upstream reference: MCRcortex/voxy 5bf33350a1cc7bb7e2b5d947b236c56d878b8a7d.
"""

import argparse
import ctypes as c
import itertools
import json
import os
import re
import runpy
import shutil
import subprocess
import tempfile
from pathlib import Path
import check_water_preprocess as water

ROOT = water.ROOT
parser = argparse.ArgumentParser()
parser.add_argument("--gpu", action="store_true")
args = parser.parse_args()

TYPES = {
    name: "float"
    for name in (
        "sunAngle",
        "worldTime",
        "screenBrightness",
        "rainFactor",
        "inSnowy",
        "inDry",
        "inRainy",
        "viewWidth",
        "viewHeight",
        "framemod8",
        "frameTimeCounter",
        "isEyeInWater",
        "inNetherWastes",
        "inCrimsonForest",
        "inWarpedForest",
        "inBasaltDeltas",
        "inSoulValley",
    )
}
TYPES.update(
    {
        name: "mat4"
        for name in (
            "vxProjInv",
            "vxModelView",
            "vxModelViewInv",
            "gbufferModelView",
            "gbufferModelViewInverse",
            "shadowModelViewInverse",
        )
    }
)
TYPES.update(
    {name: "vec3" for name in ("sunPosition", "cameraPosition", "skyColor", "fogColor")}
)
TYPES.update(worldTime="int", isEyeInWater="int")
ABI = """
struct VoxyFragmentParameters {
    vec4 sampledColour; vec2 tile; vec2 uv; uint face; uint modelId;
    vec2 lightMap; vec4 tinting; uint customId;
};
uniform vec4 testColour;
uniform float testFace,testId;
"""
MAIN = """void main(){voxy_emitFragment(VoxyFragmentParameters(testColour,vec2(0),vec2(0),uint(testFace),0u,vec2(.03125,.96875),vec4(1),uint(testId)));}"""


def preprocess(path, opts=None, *, voxy=3, mac=False, dh=False, custom_images=False):
    prelude = "#define MC_VERSION 260300\n#define IS_IRIS\n#define IRIS_VERSION 10900\n"
    if voxy is not None:
        prelude += f"#define VOXY {voxy}\n"
    if mac:
        prelude += "#define MC_OS_MAC\n"
    if dh:
        prelude += "#define DISTANT_HORIZONS\n"
    if custom_images:
        prelude += "#define IRIS_FEATURE_CUSTOM_IMAGES\n#define MC_RENDER_STAGE_TERRAIN_SOLID 1\n#define MC_RENDER_STAGE_TERRAIN_TRANSLUCENT 2\n#define MC_RENDER_STAGE_TERRAIN_CUTOUT 3\n#define MC_RENDER_STAGE_TERRAIN_CUTOUT_MIPPED 4\n"
    output = subprocess.run(
        water.command,
        input=prelude
        + re.sub(r"(?m)^\s*#extension[^\n]*", "", water.expand(path, opts or {})),
        text=True,
        capture_output=True,
        check=True,
    ).stdout
    # GNU cpp -C retains stdc-predef copyright comments even for empty JSON.
    return re.sub(r"/\*.*?\*/", "", output, flags=re.S)


def patch(dimension, kind, opts, *, ubo=True):
    data = json.loads(preprocess(ROOT / dimension / "voxy.json"))
    declarations = "\n".join(f"{TYPES[name]} {name};" for name in data["uniforms"])
    header = (
        (
            "layout(std140,binding=4) uniform ShaderUniformBindings {\n"
            + declarations
            + "\n};"
        )
        if ubo
        else "\n".join("uniform " + line for line in declarations.splitlines())
    )
    return (
        header + ABI + preprocess(ROOT / dimension / f"voxy_{kind}.glsl", opts) + MAIN
    )


def compile_source(src, suffix=".frag", compat=False):
    compiler = shutil.which("glslangValidator")
    if not compiler:
        raise SystemExit("glslangValidator required for Voxy GLSL checks")
    with tempfile.NamedTemporaryFile("w", suffix=suffix) as f:
        f.write(
            ("#version 460 compatibility\n" if compat else "#version 460 core\n")
            + re.sub(r"/\*.*?\*/|//[^\n]*", "", src, flags=re.S)
        )
        f.flush()
        result = subprocess.run([compiler, f.name], text=True, capture_output=True)
        assert result.returncode == 0, result.stdout + result.stderr


for dimension in ("world0", "world-1", "world1"):
    data = json.loads(preprocess(ROOT / dimension / "voxy.json"))
    assert data["version"] == 1 and data["excludeLodsFromVanillaDepth"] is True
    for kind in ("opaque", "translucent"):
        wrapper = (ROOT / dimension / f"voxy_{kind}.glsl").read_text()
        assert f'#include "/{dimension}/voxy_taa.glsl"' in wrapper
    assert len(set(data["uniforms"])) == len(data["uniforms"])
    assert set(data["uniforms"]) == set(TYPES)
    assert data["opaqueDrawBuffers"] == [0, 4, 6] and data[
        "translucentDrawBuffers"
    ] == [0, 3, 4, 6, 8]
    assert set(map(int, data["blending"])) == {-1, 0, 1, 2, 3, 4}
    for kwargs in ({"voxy": None}, {"voxy": 2}, {"mac": True}, {"dh": True}):
        assert not preprocess(ROOT / dimension / "voxy.json", **kwargs).strip(), kwargs

count = 0
for dimension, profile, kind in itertools.product(
    ("world0", "world-1", "world1"),
    ("POTATO", "MEDIUM", "HIGH", "ULTRA"),
    ("opaque", "translucent"),
):
    opts = water.profiles[profile]
    compile_source(patch(dimension, kind, opts))
    count += 1
    if kind == "opaque":
        data = json.loads(preprocess(ROOT / dimension / "voxy.json"))
        decl = "\n".join(f"{TYPES[name]} {name};" for name in data["uniforms"])
        taa = preprocess(ROOT / dimension / "voxy_taa.glsl", opts)
        compile_source(
            "layout(std140,binding=4) uniform U {\n"
            + decl
            + "\n};\nvec2 shift()\n"
            + taa
            + "\nvoid main(){gl_Position=vec4(shift(),0,1);}",
            ".vert",
        )
        count += 1
print(
    f"Voxy ABI/GLSL passed: {count} patches; platform/API/DH exclusion; output buffers, UBO and TAA contracts."
)

# Verify the separate-depth bridge is present only with supported Voxy.
for mac, voxy, dh in itertools.product((False, True), (None, 2, 3), (False, True)):
    src = preprocess(
        ROOT / "world0/deferred1.fsh", water.profiles["HIGH"], voxy=voxy, mac=mac, dh=dh
    )
    enabled = voxy == 3 and not mac and not dh
    assert ("uniform sampler2D vxDepthTexTrans, vxDepthTexOpaque;" in src) == enabled
    if enabled:
        assert (
            "gbufferModelView * vxModelViewInv * vxProjInv" in src
            and "float((vxRenderDistance * 16))" in src
        )
print(
    "Voxy depth bridge passed: separate opaque/translucent samplers, matching projection and render-distance units."
)

# Compile the real Voxy-enabled Lumina consumers, not only the injection stubs.
consumer_count = 0
for dimension, profile, stage in itertools.product(
    ("world0", "world-1", "world1"),
    ("POTATO", "MEDIUM", "HIGH", "ULTRA"),
    (
        "deferred1",
        "composite",
        "composite1",
        "composite2",
        "gbuffers_water",
        "gbuffers_terrain",
    ),
):
    if not (ROOT / dimension / (stage + ".fsh")).is_file():
        continue
    src = preprocess(ROOT / dimension / (stage + ".fsh"), water.profiles[profile])
    compile_source(src, compat=True)
    consumer_count += 1
for profile, stage in itertools.product(
    ("HIGH", "ULTRA"), ("gbuffers_terrain.fsh", "gbuffers_water.fsh", "shadow.vsh")
):
    src = preprocess(
        ROOT / "world0" / stage, water.profiles[profile], custom_images=True
    )
    compile_source(src, ".vert" if stage.endswith("vsh") else ".frag", compat=True)
    consumer_count += 1
print(
    f"Voxy-enabled Lumina consumers compiled: {consumer_count}, including custom-image paths."
)

if args.gpu:
    h = runpy.run_path(str(Path(__file__).with_name("check_render_polish_gpu.py")))
    g, program, draw = (h[k] for k in ("g", "program", "draw"))
    g.glUniformMatrix4fv.argtypes = [c.c_int, c.c_int, c.c_ubyte, c.POINTER(c.c_float)]
    import math

    identity = (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)

    def setup(p):
        g.glUseProgram(p)
        for name in (
            "vxProjInv",
            "vxModelView",
            "vxModelViewInv",
            "gbufferModelView",
            "gbufferModelViewInverse",
            "shadowModelViewInverse",
        ):
            mat = list(identity)
            if name == "vxProjInv":
                mat[14] = -32
            g.glUniformMatrix4fv(
                g.glGetUniformLocation(p, name.encode()), 1, 0, (c.c_float * 16)(*mat)
            )
        for name, value in (("worldTime", 6000), ("isEyeInWater", 0)):
            g.glUniform1i(g.glGetUniformLocation(p, name.encode()), value)

    def native_program(src):
        # GLSL 150 has no output-location layout syntax; preserve its semantics
        # with explicit bindings when exercising the same math on native macOS.
        src = re.sub(r"layout\(location=\d+\)\s*", "", src)
        fs = h["shader"](0x8B30, "#version 150\n" + src)
        p = g.glCreateProgram()
        g.glAttachShader(p, h["vs"])
        g.glAttachShader(p, fs)
        g.glBindFragDataLocation.argtypes = [c.c_uint, c.c_uint, c.c_char_p]
        g.glBindFragDataLocation(p, 0, b"luminaVoxyColor")
        g.glLinkProgram(p)
        ok = c.c_int()
        g.glGetProgramiv(p, 0x8B82, c.byref(ok))
        if not ok.value:
            message = c.create_string_buffer(8192)
            g.glGetProgramInfoLog(p, 8192, None, message)
            raise AssertionError(message.value.decode())
        return p

    for dimension, kind, profile in itertools.product(
        ("world0", "world-1", "world1"), ("opaque", "translucent"), ("POTATO", "HIGH")
    ):
        src = patch(
            dimension, kind, water.profiles[profile] | {"FXAA_DEFINE": -1}, ubo=False
        )
        p = native_program(src)
        setup(p)
        for rain, phase, face, material in itertools.product(
            (0.0, 1.0), (0.03, 0.25, 0.53, 0.75), range(6), (1, 32000, 10068, 10412)
        ):
            # vec4 uniforms are set explicitly; draw's helper supports float/vec3.
            g.glUseProgram(p)
            g.glUniform4f.argtypes = [
                c.c_int,
                c.c_float,
                c.c_float,
                c.c_float,
                c.c_float,
            ]
            g.glUniform4f(g.glGetUniformLocation(p, b"testColour"), 0.3, 0.5, 0.7, 0.4)
            v = draw(
                p,
                viewWidth=1,
                viewHeight=1,
                framemod8=0,
                frameTimeCounter=2,
                sunPosition=(0, 100, 0),
                skyColor=(0.3, 0.5, 0.8),
                fogColor=(0.2, 0.3, 0.4),
                screenBrightness=0.5,
                sunAngle=phase,
                rainFactor=rain,
                testFace=face,
                testId=material,
            )
            assert all(math.isfinite(x) and x >= 0 for x in v), (dimension, kind, v)
            assert 0 <= v[3] <= 1, v
            if kind == "opaque":
                assert v[3] == 1
            elif material != 32000:
                assert abs(v[3] - 0.4) < 1e-6
        g.glUseProgram(p)
        g.glUniformMatrix4fv(
            g.glGetUniformLocation(p, b"shadowModelViewInverse"),
            1,
            0,
            (c.c_float * 16)(*([0.0] * 16)),
        )
        v = draw(p, sunPosition=(0, 0, 0), testId=32000, testFace=1)
        assert all(math.isfinite(x) and x >= 0 for x in v), (
            dimension,
            kind,
            profile,
            v,
        )
    # Exercise the actual depth-bridge macros with different Iris/Voxy camera
    # frames, not only identity matrices used by the fragment-colour fixtures.
    uniforms = (ROOT / "lib/uniforms.glsl").read_text()
    bridge = (
        uniforms[
            uniforms.index("#ifdef LUMINA_VOXY") : uniforms.index(
                "#else", uniforms.index("#ifdef LUMINA_VOXY")
            )
        ]
        + "\n#endif\n"
    )
    p = native_program(
        "#define LUMINA_VOXY\nuniform mat4 gbufferModelView,gbufferModelViewInverse;\n"
        + bridge
        + "out vec4 luminaVoxyColor;void main(){vec4 clip=vec4(.2,-.1,.7,1.);vec4 v=dhProjectionInverse*clip;luminaVoxyColor=abs(dhProjection*v-clip);}"
    )
    vi = (0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)
    vii = (0, -1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)
    vx = (0, 0, -1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1)
    vxi = (0, 0, 1, 0, 0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 0, 1)
    proj = (2, 0, 0, 0, 0, 3, 0, 0, 0, 0, 4, 0, 0, 0, 0, 1)
    proji = (0.5, 0, 0, 0, 0, 1 / 3, 0, 0, 0, 0, 0.25, 0, 0, 0, 0, 1)
    g.glUseProgram(p)
    for name, mat in (
        ("gbufferModelView", vi),
        ("gbufferModelViewInverse", vii),
        ("vxModelView", vx),
        ("vxModelViewInv", vxi),
        ("vxProj", proj),
        ("vxProjInv", proji),
    ):
        g.glUniformMatrix4fv(
            g.glGetUniformLocation(p, name.encode()), 1, 0, (c.c_float * 16)(*mat)
        )
    error = draw(p)
    assert max(error) < 1e-6, error
    print(
        "GPU Voxy depth bridge passed: different Iris/Voxy camera frames round-trip through actual projection aliases."
    )
    print(
        "Isolated native Voxy GPU passed: all dimensions/faces, dry/rain, solar phases, opaque/glass/water/emission IDs; finite bounded alpha. Not a Voxy runtime test."
    )
