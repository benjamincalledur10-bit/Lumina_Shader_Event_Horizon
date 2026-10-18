#!/usr/bin/env python3
"""Compile rain, puddle and directional-shadow consumers across loader profiles."""

import itertools
import re
import shutil
import subprocess
import tempfile
import check_water_preprocess as water


def preprocess(path, options, platform="mac"):
    if platform == "mac":
        return water.preprocess(path, options, platform)
    # GLSL extension directives are not C directives. GLSL 430 already provides
    # the image/packing/storage capabilities enabled by these loader directives.
    expanded = re.sub(r"(?m)^\s*#extension[^\n]*", "", water.expand(path, options))
    return subprocess.run(
        water.command,
        input="#define MC_VERSION 260300\n#define DISTANT_HORIZONS\n#define IRIS_FEATURE_CUSTOM_IMAGES\n#define IS_IRIS\n#define MC_RENDER_STAGE_TERRAIN_SOLID 1\n#define MC_RENDER_STAGE_TERRAIN_TRANSLUCENT 2\n#define MC_RENDER_STAGE_TERRAIN_CUTOUT 3\n#define MC_RENDER_STAGE_TERRAIN_CUTOUT_MIPPED 4\n"
        + expanded,
        text=True,
        capture_output=True,
        check=True,
    ).stdout


for name, settings in water.profiles.items():
    expected = int(name in ("MEDIUM", "HIGH", "VERYHIGH", "ULTRA"))
    assert int(settings["RAIN_PUDDLES"]) == expected, (name, settings)

compiler = shutil.which("glslangValidator")
if not compiler:
    raise SystemExit("glslangValidator is required for full GLSL validation.")
count = 0
stages = (
    "gbuffers_terrain",
    "dh_terrain",
    "gbuffers_water",
    "dh_water",
    "gbuffers_weather",
    "gbuffers_entities",
    "gbuffers_hand",
    "gbuffers_block",
    "gbuffers_textured",
    "gbuffers_basic",
    "gbuffers_lightning",
    "shadow",
    "deferred1",
    "composite",
    "composite1",
)
for dimension, profile, stage, suffix in itertools.product(
    ("world0", "world-1", "world1"),
    ("POTATO", "MEDIUM", "HIGH", "ULTRA"),
    stages,
    ("fsh", "vsh"),
):
    path = water.ROOT / dimension / f"{stage}.{suffix}"
    if not path.exists():
        continue
    src = preprocess(path, water.profiles[profile])
    src = re.sub(r"/\*.*?\*/|//[^\n]*", "", src, flags=re.S)
    if stage.startswith("dh_") and suffix == "vsh":
        src = "in int dhMaterialId;\n" + src
    with tempfile.NamedTemporaryFile(
        "w", suffix=".vert" if suffix == "vsh" else ".frag"
    ) as f:
        f.write(
            "#version 150 compatibility\n#define DH_BLOCK_WATER 1\n#define DH_BLOCK_LEAVES 2\n#define DH_BLOCK_GRASS 3\n#define DH_BLOCK_LAVA 4\n#define DH_BLOCK_ILLUMINATED 5\n"
            + src
        )
        f.flush()
        result = subprocess.run([compiler, f.name], capture_output=True, text=True)
        assert result.returncode == 0, (
            dimension,
            profile,
            stage,
            suffix,
            result.stdout,
            result.stderr,
        )
    count += 1
# Explicit off, all puddle modes and custom-image/voxelized renderer paths.
for puddles, platform, stage in itertools.product(
    (0, 1, 2, 3, 4),
    ("mac", "other"),
    ("gbuffers_terrain.fsh", "dh_terrain.fsh", "shadow.vsh"),
):
    src = preprocess(
        water.ROOT / "world0" / stage,
        water.profiles["ULTRA"] | {"RAIN_PUDDLES": puddles},
        platform,
    )
    src = re.sub(r"/\*.*?\*/|//[^\n]*", "", src, flags=re.S)
    with tempfile.NamedTemporaryFile(
        "w", suffix=".vert" if stage.endswith("vsh") else ".frag"
    ) as f:
        version = "150 compatibility" if platform == "mac" else "430 compatibility"
        f.write(
            "#version "
            + version
            + "\n#define DH_BLOCK_WATER 1\n#define DH_BLOCK_LEAVES 2\n#define DH_BLOCK_GRASS 3\n#define DH_BLOCK_LAVA 4\n#define DH_BLOCK_ILLUMINATED 5\n"
            + src
        )
        f.flush()
        result = subprocess.run([compiler, f.name], capture_output=True, text=True)
        assert result.returncode == 0, (
            puddles,
            platform,
            stage,
            result.stdout,
            result.stderr,
        )
    count += 1
print(f"Rain/solar GLSL compilation passed: {count} variants.")
