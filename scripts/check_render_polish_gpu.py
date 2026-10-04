#!/usr/bin/env python3
"""Native macOS OpenGL regression checks using the actual shader calculation blocks.

Run from any directory: python3 scripts/check_render_polish_gpu.py
Exercises degenerate foam, DH reflection branches and pre-mipmap HDR extraction.
This is an isolated GPU check; Minecraft/loader integration still needs visual testing.
"""

import ctypes as c
import math
import sys
from pathlib import Path

if sys.platform != "darwin":
    raise SystemExit("This GPU check requires macOS and its native OpenGL framework.")
root = (
    Path(__file__).resolve().parents[1]
    / "Lumina_Event_Horizon_v1.3.7_Real_Extracted/shaders"
)
g = c.CDLL("/System/Library/Frameworks/OpenGL.framework/OpenGL")
pix = c.c_void_p()
count = c.c_int()
ctx = c.c_void_p()
g.CGLChoosePixelFormat.argtypes = [
    c.POINTER(c.c_int),
    c.POINTER(c.c_void_p),
    c.POINTER(c.c_int),
]
g.CGLCreateContext.argtypes = [c.c_void_p, c.c_void_p, c.POINTER(c.c_void_p)]
g.CGLSetCurrentContext.argtypes = [c.c_void_p]
assert (
    g.CGLChoosePixelFormat((c.c_int * 3)(99, 0x3200, 0), c.byref(pix), c.byref(count))
    == 0
)
assert g.CGLCreateContext(pix, None, c.byref(ctx)) == 0
assert g.CGLSetCurrentContext(ctx) == 0
g.glCreateShader.restype = c.c_uint
g.glShaderSource.argtypes = [
    c.c_uint,
    c.c_int,
    c.POINTER(c.c_char_p),
    c.POINTER(c.c_int),
]


def shader(kind, src):
    sid = g.glCreateShader(kind)
    v = c.c_char_p(src.encode())
    g.glShaderSource(sid, 1, c.byref(v), None)
    g.glCompileShader(sid)
    ok = c.c_int()
    g.glGetShaderiv(sid, 0x8B81, c.byref(ok))
    if not ok.value:
        buf = c.create_string_buffer(8192)
        g.glGetShaderInfoLog(sid, 8192, None, buf)
        raise RuntimeError(buf.value.decode())
    return sid


vs = shader(
    0x8B31,
    "#version 150\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.0-1.0,0,1);}",
)


def program(src):
    fs = shader(0x8B30, "#version 150\n" + src)
    p = g.glCreateProgram()
    g.glAttachShader(p, vs)
    g.glAttachShader(p, fs)
    g.glLinkProgram(p)
    ok = c.c_int()
    g.glGetProgramiv(p, 0x8B82, c.byref(ok))
    if not ok.value:
        buf = c.create_string_buffer(8192)
        g.glGetProgramInfoLog(p, 8192, None, buf)
        raise RuntimeError(buf.value.decode())
    return p


tex = c.c_uint()
fbo = c.c_uint()
vao = c.c_uint()
g.glGenTextures(1, c.byref(tex))
g.glBindTexture(0x0DE1, tex)
g.glTexImage2D(0x0DE1, 0, 0x8814, 1, 1, 0, 0x1908, 0x1406, None)
g.glTexParameteri(0x0DE1, 0x2801, 0x2600)
g.glTexParameteri(0x0DE1, 0x2800, 0x2600)
g.glGenFramebuffers(1, c.byref(fbo))
g.glBindFramebuffer(0x8D40, fbo)
g.glFramebufferTexture2D(0x8D40, 0x8CE0, 0x0DE1, tex, 0)
assert g.glCheckFramebufferStatus(0x8D40) == 0x8CD5
g.glGenVertexArrays(1, c.byref(vao))
g.glBindVertexArray(vao)
g.glViewport(0, 0, 1, 1)
g.glGetUniformLocation.argtypes = [c.c_uint, c.c_char_p]
g.glUniform1f.argtypes = [c.c_int, c.c_float]
g.glUniform3f.argtypes = [c.c_int, c.c_float, c.c_float, c.c_float]


def draw(p, **uniforms):
    g.glUseProgram(p)
    for name, v in uniforms.items():
        loc = g.glGetUniformLocation(p, name.encode())
        if isinstance(v, tuple):
            g.glUniform3f(loc, *v)
        else:
            g.glUniform1f(loc, v)
    g.glDrawArrays(4, 0, 3)
    out = (c.c_float * 4)()
    g.glReadPixels(0, 0, 1, 1, 0x1908, 0x1406, out)
    assert all(math.isfinite(v) for v in out)
    return tuple(out)


water = (root / "lib/materials/specificMaterials/translucents/water.glsl").read_text()
foam = water[
    water.index("                    float foam =") : water.index(
        "                    #ifndef END"
    )
]
p = program(
    "uniform float threshold,height;out vec4 result;float pow2(float x){return x*x;}void main(){float foamThreshold=threshold,yPosDif=height;"
    + foam
    + "result=vec4(foam);}"
)
for t in (0.0, 1e-12, 1e-7, 1e-6, 2e-6, 0.1, 1.2):
    for y in (-10.0, -t, 0.0, t, 10.0):
        v = draw(p, threshold=t, height=y)[0]
        assert 0 <= v <= 1
        expected = 0 if t <= 1e-6 else max(0, min(1, (t + y) / t)) ** 2
        assert abs(v - expected) < 1e-5, (t, y, v, expected)
print(
    "GPU foam: zero/near-zero thresholds finite; ordinary shoreline formula preserved.",
    flush=True,
)
dh = (root / "program/dh_water.glsl").read_text()
block = dh[
    dh.index("    // Refresh the wave-normal") : dh.index("    float lengthCylinder")
]
for wsr in (-1, 1):
    for quality in (1, 2, 3):
        p = program(
            f"#define WORLD_SPACE_REFLECTIONS_INTERNAL {wsr}\n#define WATER_MAT_QUALITY {quality}\n#define OVERWORLD\n#define DH_BLOCK_WATER 1\nuniform float angle,seed,reflectMult;uniform int mat,isEyeInWater;out vec4 result;float pow2(float x){{return x*x;}}float pow3(float x){{return x*x*x;}}void main(){{float fresnel=angle,fresnelM=seed;"
            + block
            + "result=vec4(fresnelM);}"
        )
        for mat in (0, 1):
            for underwater in (0, 1):
                g.glUseProgram(p)
                g.glUniform1i(g.glGetUniformLocation(p, b"mat"), mat)
                g.glUniform1i(g.glGetUniformLocation(p, b"isEyeInWater"), underwater)
                for angle in (0, 0.3, 1):
                    v = draw(p, angle=angle, seed=1, reflectMult=0.5)[0]
                    expected = (
                        (0.02 + 0.98 * angle**5) * 0.5
                        if mat == 1 and not underwater
                        else (
                            (
                                1
                                if mat == 1 and underwater and wsr > 0 and quality >= 2
                                else angle**3
                            )
                            * 0.85
                            + 0.15
                        )
                        * 0.5
                    )
                    assert abs(v - expected) < 1e-5, (
                        wsr,
                        quality,
                        mat,
                        underwater,
                        v,
                        expected,
                    )
print(
    "GPU DH reflection: underwater override preserved; wave Fresnel, Schlick and non-water branches verified.",
    flush=True,
)
s = (root / "program/composite3.glsl").read_text()
extraction = s[
    s.index("        vec3 bloomSource =") : s.index("        /* DRAWBUFFERS:08 */")
]
p = program(
    "#define BLOOM_THRESHOLD 1.0\nuniform vec3 inputColor;out vec4 result;void main(){vec3 color=inputColor;"
    + extraction
    + "result=vec4(bloomSource,1);}"
)
for val in (0, 0.25, 0.5, 0.75, 1, 2, 16):
    v = draw(p, inputColor=(val, val * 0.5, val * 0.25))
    assert all(x >= 0 for x in v)
    if v[0] > 0:
        assert abs(v[1] / v[0] - 0.5) < 1e-5 and abs(v[2] / v[0] - 0.25) < 1e-5
# Compile the actual bloom tile consumer in both selective and legacy modes.
tile_source = (root / "program/composite4.glsl").read_text()
tile = tile_source[
    tile_source.index("vec3 BloomTile(") : tile_source.index("//Includes//")
]
for selective in (False, True):
    program(
        ("#define BLOOM_SELECTIVE\n" if selective else "")
        + "#define texture2D texture\n"
        + "uniform sampler2D colortex0,colortex8;uniform float viewWidth,viewHeight;"
        + "float weight[7]=float[7](1,6,15,20,15,6,1);"
        + "vec2 view=vec2(viewWidth,viewHeight);"
        + tile
        + "out vec4 result;void main(){result=vec4(BloomTile(2.0,vec2(0),vec2(.125)),1);}"
    )
print("Native bloom tile compile/link passed: selective and legacy paths.", flush=True)

# Full-resolution extraction of one HDR pixel in a 16x16 image, then real GPU mipmaps.
g.glTexImage2D.argtypes = [
    c.c_uint,
    c.c_int,
    c.c_int,
    c.c_int,
    c.c_int,
    c.c_int,
    c.c_uint,
    c.c_uint,
    c.c_void_p,
]
g.glActiveTexture(0x84C1)
source = c.c_uint()
g.glGenTextures(1, c.byref(source))
g.glBindTexture(0x0DE1, source)
g.glTexImage2D(0x0DE1, 0, 0x881A, 16, 16, 0, 0x1908, 0x1406, None)
g.glTexParameteri(0x0DE1, 0x2801, 0x2702)
g.glTexParameteri(0x0DE1, 0x2800, 0x2600)
g.glFramebufferTexture2D(0x8D40, 0x8CE0, 0x0DE1, source, 0)
g.glViewport(0, 0, 16, 16)
p = program(
    "#define BLOOM_THRESHOLD 1.0\nout vec4 result;void main(){vec3 color=ivec2(gl_FragCoord.xy)==ivec2(8,8)?vec3(16,8,4):vec3(0);"
    + extraction
    + "result=vec4(bloomSource,1);}"
)
g.glUseProgram(p)
g.glDrawArrays(4, 0, 3)
g.glGenerateMipmap(0x0DE1)
g.glFramebufferTexture2D(0x8D40, 0x8CE0, 0x0DE1, tex, 0)
g.glViewport(0, 0, 1, 1)
p = program(
    "uniform sampler2D source;out vec4 result;void main(){result=textureLod(source,vec2(.5),4.0);}"
)
g.glUseProgram(p)
g.glUniform1i(g.glGetUniformLocation(p, b"source"), 1)
v = draw(p)
assert abs(v[0] - 15 / 256) < 0.0001 and abs(v[1] - 7.5 / 256) < 0.0001, v
print(
    "GPU bloom: hue preserved; isolated HDR light retains expected energy through four actual mip levels.",
    flush=True,
)
