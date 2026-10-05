#!/usr/bin/env python3
"""Package only tracked canonical files and verify the ZIP against their bytes."""

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path
from validate_canonical import CANONICAL_ROOT, EXPECTED_PACKAGE_FILES, REPOSITORY_ROOT

parser = argparse.ArgumentParser()
parser.add_argument("--version", required=True)
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()
assert (
    json.loads((CANONICAL_ROOT / "shaders/pack.json").read_text())["version"]
    == args.version
)
tracked = subprocess.check_output(
    ["git", "ls-files", "--", str(CANONICAL_ROOT.relative_to(REPOSITORY_ROOT))],
    cwd=REPOSITORY_ROOT,
    text=True,
).splitlines()
files = [REPOSITORY_ROOT / p for p in tracked if not p.endswith(".DS_Store")]
assert len(files) == EXPECTED_PACKAGE_FILES
args.output.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(
    args.output, "w", zipfile.ZIP_DEFLATED, compresslevel=9
) as archive:
    for path in sorted(files):
        archive.write(path, path.relative_to(CANONICAL_ROOT).as_posix())
with zipfile.ZipFile(args.output) as archive:
    assert archive.testzip() is None
    assert len(archive.namelist()) == EXPECTED_PACKAGE_FILES
    assert "License.txt" in archive.namelist()
    for path in files:
        assert (
            archive.read(path.relative_to(CANONICAL_ROOT).as_posix())
            == path.read_bytes()
        )
digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
args.output.with_suffix(".zip.sha256").write_text(
    digest + "  " + args.output.name + "\n"
)
print(f"Verified {len(files)} files; SHA256 {digest}")
