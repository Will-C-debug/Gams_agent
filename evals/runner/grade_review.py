"""Grade review outputs against seeded-defect ground truth.

A case counts as **detected** when some finding in the agent's output:
  1. names the ground-truth file (by path or basename) with a line within +/-LINE_TOL of the seeded line,
     or quotes the seeded line's code; and
  2. mentions at least one of the case's keywords in the same finding (table row or paragraph).
Severity agreement is reported separately. Findings that match no case are counted as "other findings";
SMEs label those valid/invalid to measure precision.

    python evals/runner/grade_review.py --results evals/results/<run> [--cases evals/seeded_defects/uc_small.yaml]

Expects one Markdown file per case: <results>/<case-id>.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from common import EVALS, load_cases

LINE_TOL = 3
SEVERITIES = ["nit", "minor", "question", "major", "blocker"]
_LOC_RE = re.compile(r"([\w./-]+\.(?:gms|inc|opt|op\d))(?::|\s+line\s+|\s*\(line\s*)(\d+)", re.IGNORECASE)


def split_findings(text: str) -> list[str]:
    """Table rows and paragraphs/bullets are treated as individual findings."""
    chunks: list[str] = []
    for block in re.split(r"\n\s*\n", text):
        lines = block.splitlines()
        if any(ln.strip().startswith("|") for ln in lines):
            chunks += [ln for ln in lines if ln.strip().startswith("|") and not set(ln.strip()) <= set("|-: ")]
        else:
            chunks += re.split(r"\n(?=\s*(?:[-*]|\d+\.)\s)", block)
    return [c for c in chunks if c.strip()]


def finding_matches(chunk: str, case: dict, seeded_line_text: str) -> bool:
    loc = case["location"]
    low = chunk.lower()
    located = False
    for path, line in _LOC_RE.findall(chunk):
        if Path(path).name.lower() == Path(loc["file"]).name.lower() and abs(int(line) - loc["line"]) <= LINE_TOL:
            located = True
    code = seeded_line_text.strip()
    if not located and code and len(code) > 12 and code[:40].lower() in low:
        located = True
    keyword = any(k.lower() in low for k in case.get("keywords", []))
    return located and keyword


def severity_of(chunk: str) -> str | None:
    low = chunk.lower()
    found = [s for s in SEVERITIES if re.search(rf"\b{s}\b", low)]
    return found[-1] if found else None


def grade(results: Path, cases_file: Path) -> dict:
    effects_path = EVALS / "seeded_defects" / "effects.json"
    effects = json.loads(effects_path.read_text())["cases"] if effects_path.exists() else {}
    _, cases = load_cases(cases_file)
    per_case = []
    for case in cases:
        out = results / f"{case['id']}.md"
        if not out.exists():
            per_case.append({"id": case["id"], "status": "missing output"})
            continue
        chunks = split_findings(out.read_text(encoding="utf-8"))
        line_text = effects.get(case["id"], {}).get("location_text", "")
        hits = [c for c in chunks if finding_matches(c, case, line_text)]
        sev = severity_of(hits[0]) if hits else None
        located_rows = [c for c in chunks if _LOC_RE.search(c)]
        per_case.append(
            {
                "id": case["id"],
                "detected": bool(hits),
                "expected_severity": case["severity"].lower(),
                "reported_severity": sev,
                "severity_ok": sev is not None and SEVERITIES.index(sev) >= SEVERITIES.index(case["severity"].lower()) - 1,
                "other_findings": max(0, len(located_rows) - (1 if hits else 0)),
            }
        )
    graded = [c for c in per_case if "detected" in c]
    blocker_major = [c for c in graded if c["expected_severity"] in ("blocker", "major")]
    summary = {
        "cases": len(cases),
        "graded": len(graded),
        "recall": round(sum(c["detected"] for c in graded) / len(graded), 3) if graded else None,
        "recall_blocker_major": round(sum(c["detected"] for c in blocker_major) / len(blocker_major), 3) if blocker_major else None,
        "severity_agreement": round(sum(c["severity_ok"] for c in graded if c["detected"]) / max(1, sum(c["detected"] for c in graded)), 3),
        "other_findings_for_sme_review": sum(c["other_findings"] for c in graded),
    }
    return {"summary": summary, "cases": per_case}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--cases", default=str(EVALS / "seeded_defects" / "uc_small.yaml"))
    args = ap.parse_args()
    report = grade(Path(args.results), Path(args.cases))
    (Path(args.results) / "grade.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
