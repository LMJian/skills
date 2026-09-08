#!/usr/bin/env python3
"""Build a reproducible archive with no caches, local state or repository history."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_distribution import validate


def build():
    errors = validate()
    if errors:
        raise ValueError("\n".join(errors))
    version = json.loads((ROOT / ".codex-plugin/plugin.json").read_text())["version"]
    output = ROOT / "dist" / f"harness-devflow-{version}.zip"
    output.parent.mkdir(exist_ok=True)
    ignored = {".git", ".harness", "dist", "__pycache__", ".pytest_cache", ".ruff_cache"}
    files = [p for p in sorted(ROOT.rglob("*")) if p.is_file() and
             not any(part in ignored for part in p.relative_to(ROOT).parts) and
             p.suffix not in {".pyc", ".pyo"} and p.name != ".DS_Store"]
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            entry = zipfile.ZipInfo(path.relative_to(ROOT).as_posix(), date_time=(2000, 1, 1, 0, 0, 0))
            entry.external_attr = 0o100644 << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, path.read_bytes())
    return {"archive": str(output), "files": len(files), "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
