#!/usr/bin/env python3
"""Preprocess water shader variants across dimensions, profiles and reflection modes."""

import itertools
import re
import shutil
import subprocess
from pathlib import Path

ROOT = (
    Path(__file__).resolve().parents[1]
    / "Lumina_Event_Horizon_v1.3.7_Real_Extracted/shaders"
)
properties = (ROOT / "shaders.properties").read_text()
profiles = {
    name: dict(token.split("=", 1) for token in settings.split())
    for name, settings in re.findall(r"profile\.(\w+)\s*=([^\n]+)", properties)
}
compiler = Path("/Library/Developer/CommandLineTools/usr/bin/clang")
if compiler.exists():
    command = [str(compiler), "-E", "-P", "-C", "-x", "c", "-"]
else:
    cpp = shutil.which("cpp")
    if not cpp:
        raise SystemExit("A C preprocessor (cpp or native macOS clang) is required.")
    command = [cpp, "-P", "-C", "-"]


def expand(path, options):
    source = path.read_text()
    if path.name == "common.glsl":
        for key, value in options.items():
            source = re.sub(
                r"(?m)^\s*#define " + key + r"\b[^\n]*",
                "\n#define " + key + " " + str(value),
                source,
            )
    source = re.sub(r"(?m)^\s*#version[^\n]*", "", source)
    return re.sub(
        r'(?m)^\s*#include\s+"([^"]+)"',
        lambda match: expand(ROOT / match[1].lstrip("/"), options),
        source,
    )


def preprocess(path, options, platform="mac", version=260300):
    prelude = f"#define MC_VERSION {version}\n#define DISTANT_HORIZONS\n"
    if platform == "mac":
        prelude += "#define MC_OS_MAC\n"
    else:
        prelude += "#define IRIS_FEATURE_CUSTOM_IMAGES\n"
    result = subprocess.run(
        command,
        input=prelude + expand(path, options),
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout


count = 0
for dimension, profile, style, reflection, path, suffix in itertools.product(
    ("world0", "world-1", "world1"),
    ("POTATO", "MEDIUM", "HIGH", "ULTRA"),
    (1, 2, 3),
    (-1, 0, 1, 2),
    ("gbuffers_water", "dh_water"),
    ("fsh", "vsh"),
):
    options = profiles[profile] | {
        "WATER_STYLE_DEFINE": style,
        "WATER_REFLECT_QUALITY": reflection,
    }
    output = preprocess(ROOT / dimension / f"{path}.{suffix}", options)
    if suffix == "fsh" and dimension == "world0":
        assert "float waterColumnLength" in output, (profile, path)
        assert "float waterOpticalDepth" in output, (profile, path)
        if style >= 2 and profile == "POTATO":
            assert "vec2 normalBig = swell * 0.35" in output
        if reflection == 0:
            assert "// Method 1: Ray Marched Reflection" not in output
            assert "// Method 2: Mirorred Image Reflection" not in output
        if path == "dh_water" and reflection >= 1:
            assert "float z1R = texture2D(dhDepthTex1," in output
    count += 1

# Modern WSR/colored-lighting and legacy compatibility branches.
for platform, version, profile, style, path in itertools.product(
    ("mac", "other"),
    (10800, 11300, 260300),
    ("POTATO", "ULTRA"),
    (1, 3),
    ("gbuffers_water", "dh_water"),
):
    options = profiles[profile] | {"WATER_STYLE_DEFINE": style}
    preprocess(ROOT / "world0" / f"{path}.fsh", options, platform, version)
    count += 1
print(
    f"Water preprocessing passed: {count} configurations, including profile/sky-only/DH/legacy/WSR paths."
)
