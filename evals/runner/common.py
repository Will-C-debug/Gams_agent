"""Shared helpers for the eval runner and graders."""

from __future__ import annotations

import shutil
from pathlib import Path

import yaml

EVALS = Path(__file__).resolve().parents[1]
ROOT = EVALS.parent


def load_cases(path: Path) -> tuple[Path, list[dict]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    base = (path.parent / data["base"]).resolve()
    return base, data["cases"]


def materialize(base: Path, case: dict | None, dest: Path) -> Path:
    """Copy the base model to dest and apply the case's edits (each `find` must occur exactly once)."""
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(base, dest, ignore=shutil.ignore_patterns(".gams-agent"))
    for edit in (case or {}).get("edits", []):
        f = dest / edit["file"]
        text = f.read_text(encoding="utf-8")
        count = text.count(edit["find"])
        if count != 1:
            raise ValueError(f"{case['id']}: expected exactly one match in {edit['file']}, found {count}: {edit['find']!r}")
        f.write_text(text.replace(edit["find"], edit["replace"]), encoding="utf-8")
    return dest


def location_line(dest: Path, case: dict) -> str:
    loc = case["location"]
    lines = (dest / loc["file"]).read_text(encoding="utf-8").splitlines()
    n = loc["line"]
    return lines[n - 1] if 0 < n <= len(lines) else ""
