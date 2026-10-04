#!/usr/bin/env python3
"""Preprocess cloud/terrain/reflection integration on both loader/platform paths.

Reuses and also runs the water matrix to retain coverage for the shared sky code.
"""

import itertools
import check_water_preprocess as water

count = 0
for dimension, quality, platform, stage in itertools.product(
    ("world0", "world-1", "world1"),
    (0, 1, 2, 3),
    ("mac", "custom-images"),
    ("deferred1.fsh", "gbuffers_terrain.fsh", "gbuffers_water.fsh", "dh_water.fsh"),
):
    output = water.preprocess(
        water.ROOT / dimension / stage,
        water.profiles["HIGH"]
        | {
            "CLOUD_QUALITY": quality,
            "WATER_REFLECT_QUALITY": 3,
        },
        platform,
    )
    assert "#include" not in output
    if (
        quality
        and dimension == "world0"
        and stage in ("deferred1.fsh", "gbuffers_water.fsh", "dh_water.fsh")
    ):
        assert "float LuminaCloudShape(" in output, (dimension, quality, stage)
        assert "transmittance *= 1.0 - sampleAlpha" in output
        assert output.count("const float cloudStretch =") == 1
    count += 1
for quality, scale, altitude, speed in itertools.product(
    (1, 2, 3), (50, 100, 200), (-96, 192, 800), (0, 100)
):
    output = water.preprocess(
        water.ROOT / "world0/deferred1.fsh",
        water.profiles["HIGH"]
        | {
            "CLOUD_QUALITY": quality,
            "LUMINA_CLOUD_SCALE": scale,
            "CLOUD_ALT1": altitude,
            "CLOUD_SPEED_MULT": speed,
        },
    )
    assert "float LuminaCloudShape(" in output
    count += 1
print(
    f"Cloud preprocessing passed: {count} configurations, including disabled clouds, dimensions, reflections, scale, altitude and speed."
)
