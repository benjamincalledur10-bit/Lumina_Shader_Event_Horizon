#!/usr/bin/env python3
"""Expand beta.5 shader variants and optionally compile with glslangValidator."""

import itertools
import shutil
import subprocess
import tempfile
from pathlib import Path
import check_water_preprocess as water

compiler = shutil.which("glslangValidator")
count = 0


def check(dimension, stage, options, platform="mac"):
    global count
    path = water.ROOT / dimension / stage
    output = water.preprocess(path, options, platform)
    assert "#include" not in output
    if compiler:
        version = "430 compatibility" if platform != "mac" else "130"
        suffix = ".vert" if stage.endswith(".vsh") else ".frag"
        with tempfile.NamedTemporaryFile("w", suffix=suffix) as f:
            f.write("#version " + version + "\n" + output)
            f.flush()
            result = subprocess.run([compiler, f.name], text=True, capture_output=True)
            if result.returncode:
                raise AssertionError(
                    (dimension, stage, options, platform, result.stdout, result.stderr)
                )
    count += 1


for dimension, blur, focus, quality in itertools.product(
    ("world0", "world-1", "world1"), (0, 1, 2, 3), (0, 8, -1), (16, 64, 96)
):
    check(
        dimension,
        "composite3.fsh",
        water.profiles["HIGH"]
        | {"WORLD_BLUR": blur, "WB_DOF_FOCUS": focus, "WB_AF_QUALITY": quality},
    )
for quality, taa, smoke, platform in itertools.product(
    (1, 2, 3, 4), (None, 1), (None, 1), ("mac", "custom-images")
):
    check(
        "world0",
        "composite1.fsh",
        water.profiles["HIGH"]
        | {"LIGHTSHAFT_QUALI_DEFINE": quality, "TAA": taa, "LIGHTSHAFT_SMOKE": smoke},
        platform,
    )
for profile, stage, dimension in itertools.product(
    ("POTATO", "HIGH", "ULTRA"),
    (
        "gbuffers_terrain.fsh",
        "gbuffers_terrain.vsh",
        "dh_water.fsh",
        "deferred1.fsh",
        "shadow.vsh",
    ),
    ("world0", "world-1", "world1"),
):
    check(dimension, stage, water.profiles[profile])
print(
    f"Beta.5 shader variants passed: {count}; "
    + (
        "GLSL compilation included."
        if compiler
        else "GLSL compiler unavailable locally; CI performs compilation."
    )
)
