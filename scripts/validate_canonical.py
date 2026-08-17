#!/usr/bin/env python3
"""Validate the canonical Lumina Event Horizon shader package."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ROOT = REPOSITORY_ROOT / "Lumina_Event_Horizon_v1.3.7_Real_Extracted"
SHADER_ROOT = CANONICAL_ROOT / "shaders"
SHADER_SUFFIXES = {".csh", ".fsh", ".glsl", ".vsh"}
EXPECTED_SHADER_FILES = 379
EXPECTED_INCLUDES = 723
EXPECTED_PACKAGE_FILES = 399
HISTORICAL_ROOTS = (
    "Lumina_1.3.3_Extracted/",
    "Lumina_Event_Horizon/",
    "RealisticShader/",
    "True_v1.3.3_Lunar/",
)
AUTOMATION_PATHS = {
    ".github/workflows/validate-canonical.yml",
    "scripts/validate_canonical.py",
}
SHADER_RESOURCE_SUFFIXES = SHADER_SUFFIXES | {
    ".lang",
    ".mcmeta",
    ".placebo",
    ".png",
    ".properties",
    ".json",
}
INCLUDE_RE = re.compile(r'^\s*#include\s+["<]([^">]+)[">]', re.MULTILINE)
OPTION_RE = re.compile(
    r"^\s*#define\s+([A-Za-z_]\w*)\s+(\S+)\s*//\s*\[([^]]+)]",
    re.MULTILINE,
)
PREPROCESSOR_RE = re.compile(
    r"^\s*#\s*(if|ifdef|ifndef|elif|else|endif)\b", re.MULTILINE
)
UNSAFE_SHADER_PATTERNS = (
    (re.compile(r"normalize\(pow\(lightColor\b"), "unsafe zero-length light-color normalization"),
    (re.compile(r"frameCounter\s*%\s*int\("), "unsafe frame interval may evaluate to zero"),
    (re.compile(r"shadowDir\s*/=\s*abs\(shadowDir\.z\)"), "unsafe rainbow horizon division"),
    (
        re.compile(r"volumetricLight\s*\*=\s*pow\(totalSmoke\s*/\s*volumetricLight\.a"),
        "unsafe smoke normalization with zero accumulated alpha",
    ),
    (re.compile(r"normalize\(lightVec\s*-\s*viewPos\)"), "unsafe zero-length GGX half-vector normalization"),
    (re.compile(r"mat2\s+J\s*=\s*inverseM\(mat2\(dFdx\(uv\)"), "unguarded anisotropic derivative inversion"),
    (re.compile(r"texelFetch\(colortex3,\s*texelCoord\s*\+\s*ivec2"), "unclamped FXAA neighborhood fetch"),
)


def relative(path: Path) -> str:
    return path.relative_to(REPOSITORY_ROOT).as_posix()


def shader_files() -> list[Path]:
    return sorted(
        path
        for path in SHADER_ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in SHADER_SUFFIXES
    )


def strip_comments_and_strings(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"//.*", "", text)
    return re.sub(r'"(?:\\.|[^"\\])*"', '""', text)


def validate_counts(files: list[Path], errors: list[str]) -> None:
    package_files = sum(path.is_file() for path in CANONICAL_ROOT.rglob("*"))
    if len(files) != EXPECTED_SHADER_FILES:
        errors.append(
            f"expected {EXPECTED_SHADER_FILES} shader files, found {len(files)}"
        )
    if package_files != EXPECTED_PACKAGE_FILES:
        errors.append(
            f"expected {EXPECTED_PACKAGE_FILES} package files, found {package_files}"
        )


def validate_includes(files: list[Path], errors: list[str]) -> None:
    include_count = 0
    for path in files:
        text = path.read_text(encoding="utf-8-sig")
        for target in INCLUDE_RE.findall(text):
            include_count += 1
            resolved = (
                SHADER_ROOT / target.lstrip("/")
                if target.startswith("/")
                else path.parent / target
            )
            if not resolved.is_file():
                errors.append(f"{relative(path)}: unresolved include {target!r}")
    if include_count != EXPECTED_INCLUDES:
        errors.append(
            f"expected {EXPECTED_INCLUDES} includes, found {include_count}"
        )


def validate_json(errors: list[str]) -> None:
    for path in sorted(CANONICAL_ROOT.rglob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"{relative(path)}: invalid JSON: {exc}")


def validate_delimiters(files: list[Path], errors: list[str]) -> None:
    pairs = {"(": ")", "[": "]", "{": "}"}
    closing = {value: key for key, value in pairs.items()}
    for path in files:
        stack: list[tuple[str, int]] = []
        text = strip_comments_and_strings(path.read_text(encoding="utf-8-sig"))
        for line_number, line in enumerate(text.splitlines(), start=1):
            for character in line:
                if character in pairs:
                    stack.append((character, line_number))
                elif character in closing:
                    if not stack or stack[-1][0] != closing[character]:
                        errors.append(
                            f"{relative(path)}:{line_number}: unexpected {character!r}"
                        )
                        stack.clear()
                        break
                    stack.pop()
        for character, line_number in stack:
            errors.append(
                f"{relative(path)}:{line_number}: unclosed {character!r}"
            )


def validate_preprocessor(files: list[Path], errors: list[str]) -> None:
    for path in files:
        stack: list[tuple[str, int, bool]] = []
        text = strip_comments_and_strings(path.read_text(encoding="utf-8-sig"))
        for line_number, line in enumerate(text.splitlines(), start=1):
            match = PREPROCESSOR_RE.match(line)
            if not match:
                continue
            directive = match.group(1)
            if directive in {"if", "ifdef", "ifndef"}:
                stack.append((directive, line_number, False))
            elif directive in {"elif", "else"}:
                if not stack:
                    errors.append(
                        f"{relative(path)}:{line_number}: #{directive} without #if"
                    )
                elif stack[-1][2]:
                    errors.append(
                        f"{relative(path)}:{line_number}: #{directive} after #else"
                    )
                elif directive == "else":
                    kind, opening_line, _ = stack[-1]
                    stack[-1] = (kind, opening_line, True)
            elif not stack:
                errors.append(f"{relative(path)}:{line_number}: #endif without #if")
            else:
                stack.pop()
        for directive, line_number, _ in stack:
            errors.append(
                f"{relative(path)}:{line_number}: unclosed #{directive} block"
            )


def validate_option_defaults(files: list[Path], errors: list[str]) -> None:
    for path in files:
        text = path.read_text(encoding="utf-8-sig")
        for name, default, raw_options in OPTION_RE.findall(text):
            options = raw_options.split()
            if default not in options:
                errors.append(
                    f"{relative(path)}: default {name}={default} is not in "
                    f"[{raw_options}]"
                )


def validate_known_shader_hazards(files: list[Path], errors: list[str]) -> None:
    for path in files:
        text = strip_comments_and_strings(path.read_text(encoding="utf-8-sig"))
        for pattern, description in UNSAFE_SHADER_PATTERNS:
            if pattern.search(text):
                errors.append(f"{relative(path)}: {description}")


def changed_paths(base_ref: str, errors: list[str]) -> None:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--no-renames", base_ref, "--"],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        errors.append(f"could not compare changes with {base_ref!r}: {result.stderr.strip()}")
        return

    canonical_prefix = f"{CANONICAL_ROOT.name}/"
    for changed in filter(None, result.stdout.splitlines()):
        path = Path(changed)
        if changed.endswith(".DS_Store") or path.name == ".DS_Store":
            errors.append(f"forbidden macOS metadata changed: {changed}")
        if path.suffix.lower() == ".zip":
            errors.append(f"ZIP archives must not be committed: {changed}")
        if changed.startswith(HISTORICAL_ROOTS):
            errors.append(f"historical copy changed: {changed}")
        elif (
            path.suffix.lower() in SHADER_RESOURCE_SUFFIXES
            and not changed.startswith(canonical_prefix)
            and changed not in AUTOMATION_PATHS
        ):
            errors.append(f"shader resource changed outside canonical version: {changed}")


def validate_repository_hygiene(errors: list[str]) -> None:
    for path in CANONICAL_ROOT.rglob("*"):
        if path.name == ".DS_Store":
            errors.append(f"forbidden macOS metadata in canonical package: {relative(path)}")
        if path.is_file() and path.suffix.lower() == ".zip":
            errors.append(f"unexpected ZIP inside canonical package: {relative(path)}")


def validate_nether_features(errors: list[str]) -> None:
    common = (SHADER_ROOT / "lib/common.glsl").read_text(encoding="utf-8-sig")
    fog = (SHADER_ROOT / "lib/atmospherics/fog/mainFog.glsl").read_text(
        encoding="utf-8-sig"
    )
    storm = (SHADER_ROOT / "lib/atmospherics/netherStorm.glsl").read_text(
        encoding="utf-8-sig"
    )
    blocklight = (SHADER_ROOT / "lib/colors/blocklightColors.glsl").read_text(
        encoding="utf-8-sig"
    )
    lava = (
        SHADER_ROOT / "lib/materials/specificMaterials/terrain/lava.glsl"
    ).read_text(encoding="utf-8-sig")
    portal = (
        SHADER_ROOT
        / "lib/materials/specificMaterials/translucents/netherPortal.glsl"
    ).read_text(encoding="utf-8-sig")
    properties = (SHADER_ROOT / "shaders.properties").read_text(encoding="utf-8-sig")
    language = (SHADER_ROOT / "lang/en_US.lang").read_text(encoding="utf-8-sig")

    required = (
        (common, "#define NETHER_BIOME_FOG_STRENGTH 100", "Nether fog control default"),
        (common, "#ifdef NETHER", "Nether-only compilation guard"),
        (common, "#ifdef MC_OS_MAC", "macOS Nether compatibility path"),
        (common, "float GetNetherBiomeFogDensity()", "non-macOS Nether fog density function"),
        (fog, "lPos * GetNetherBiomeFogDensity() / farM", "biome fog density application"),
        (properties, "screen.NETHER_SETTINGS", "Nether settings screen"),
        (properties, "NETHER_BIOME_FOG_STRENGTH", "Nether fog control exposure"),
        (language, "option.NETHER_BIOME_FOG_STRENGTH", "Nether fog control label"),
        (storm, "stormBiomeIntensity", "biome storm intensity"),
        (storm, "basaltAsh", "Basalt ash adaptation"),
        (storm, "#ifdef MC_OS_MAC", "v1.3.7-compatible macOS storm path"),
        (portal, "float multiplier = 0.4 / (safePortalViewDepth * sampleCount)", "protected non-macOS portal projection"),
    )
    for text, snippet, description in required:
        if snippet not in text:
            errors.append(f"missing {description}: {snippet}")

    if re.search(r"\b(?:texture\w*|texelFetch)\s*\(", strip_comments_and_strings(fog)):
        errors.append("Nether fog must not add texture samples")

    global_density_names = (
        "netherBiomeDensityWeighted",
        "netherBiomeDensityRaw",
        "netherBiomeFogDensity",
    )
    for name in global_density_names:
        if re.search(rf"^\s*(?:const\s+)?float\s+{name}\b", common, re.MULTILINE):
            errors.append(f"forbidden global Nether fog calculation: {name}")

    mac_v137_signatures = (
        (common, "inWarpedForest * vec3(0.18, 0.1, 0.25)", "v1.3.7 macOS Nether color"),
        (common, "vec3 lavaLightColor = vec3(0.15, 0.06, 0.01)", "v1.3.7 macOS lava ambience"),
        (fog, "float fog = lPos / farM", "v1.3.7 macOS Nether fog"),
        (storm, "float stormSample = pow2(Noise3D(tracePosM + wind))", "v1.3.7 macOS storm sampling"),
        (storm, "netherStorm.a = min1(netherStorm.a * NETHER_STORM_I)", "v1.3.7 macOS storm opacity"),
        (blocklight, "vec3 lavaSpecialLightColor = vec3(3.25, 0.9, 0.2) * 3.9", "v1.3.7 macOS lava light"),
        (blocklight, "vec3 netherPortalSpecialLightColor = vec3(1.8, 0.4, 2.2) * 0.8", "v1.3.7 macOS portal light"),
        (blocklight, "if (mat == 13) return vec4(lavaSpecialLightColor, 0.8)", "v1.3.7 macOS lava floodfill"),
        (blocklight, "if (mat == 25) return vec4(netherPortalSpecialLightColor * 2.0, 0.4)", "v1.3.7 macOS portal floodfill"),
        (lava, "emission = GetLuminance(color.rgb) * 7.48 + 0.5", "v1.3.7 macOS lava emission"),
        (portal, "float multiplier = 0.4 / (-viewVector.z * sampleCount)", "v1.3.7 macOS portal projection"),
        (portal, "color.rgb *= color.rgb * vec3(1.25, 1.0, 0.65)", "v1.3.7 macOS portal color"),
        (portal, "emission = clamp(emission * 120.0, 0.03, 1.2) * 8.0", "v1.3.7 macOS portal emission"),
        (portal, "edgeColor.b *= 0.8", "v1.3.7 macOS portal edge color"),
        (portal, "emission = mix(emission, 5.0, edge)", "v1.3.7 macOS portal edge emission"),
    )
    for text, snippet, description in mac_v137_signatures:
        if snippet not in text:
            errors.append(f"missing {description}: {snippet}")


def validate_end_performance_guards(errors: list[str]) -> None:
    event_horizon = (
        SHADER_ROOT / "lib/atmospherics/eventHorizon.glsl"
    ).read_text(encoding="utf-8-sig")
    required = (
        (
            "float maxAngle = bhSize * EVENT_HORIZON_DISK_OUTER_RADIUS",
            "black-hole angular early rejection",
        ),
        (
            "backDisk.a *= 1.0 - smoothstep(R_out - 0.5, R_out, r)",
            "black-hole edge fade",
        ),
        ("float maxAngle = bhSize * 3.5", "white-hole angular early rejection"),
        ("if (r < 1.5)", "masked white-hole disk sampling guard"),
    )
    for snippet, description in required:
        if snippet not in event_horizon:
            errors.append(f"missing {description}: {snippet}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-ref",
        help="Git revision used to reject changes to historical shader copies",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    files = shader_files()

    validate_counts(files, errors)
    validate_includes(files, errors)
    validate_json(errors)
    validate_delimiters(files, errors)
    validate_preprocessor(files, errors)
    validate_option_defaults(files, errors)
    validate_known_shader_hazards(files, errors)
    validate_repository_hygiene(errors)
    validate_nether_features(errors)
    validate_end_performance_guards(errors)
    if args.base_ref:
        changed_paths(args.base_ref, errors)

    if errors:
        print(f"Canonical validation failed with {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        "Canonical validation passed: "
        f"{len(files)} shaders, {EXPECTED_INCLUDES} includes, "
        f"{EXPECTED_PACKAGE_FILES} package files."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
