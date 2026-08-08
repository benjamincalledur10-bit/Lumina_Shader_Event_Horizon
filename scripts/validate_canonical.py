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
    validate_repository_hygiene(errors)
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
