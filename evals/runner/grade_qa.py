"""Grade knowledge Q&A answers: required/forbidden patterns plus option-name validity.

    GAMS_SYSDIR=/path/to/gams53 python evals/runner/grade_qa.py --results evals/results/<run>

Expects <results>/<question-id>.md. Without GAMS_SYSDIR the option check is skipped (reported as such).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import yaml
from common import EVALS

from gams_tools import optdef

_OPT_TOKEN_RE = re.compile(r"`([a-z][a-z0-9]{2,})(?:[ =][^`]*)?`")
_NOT_OPTIONS = {"gams", "cplex", "lambda", "balance", "optcr", "optca", "reslim", "threads", "execmode", "loaddc", "logic", "requestmarginals"}


def option_problems(text: str, defs: optdef.OptionDefs) -> list[str]:
    problems = []
    for name in {m.group(1) for m in _OPT_TOKEN_RE.finditer(text)} - _NOT_OPTIONS:
        od, _ = defs.lookup(name)
        if od is None and name not in defs.deprecated:
            problems.append(f"`{name}` is not a CPLEX option in this GAMS release")
    return problems


def grade(results: Path) -> dict:
    qs = yaml.safe_load((EVALS / "knowledge_qa" / "questions.yaml").read_text())["questions"]
    sysdir = os.environ.get("GAMS_SYSDIR")
    defs = optdef.load_optdef(Path(sysdir), "cplex") if sysdir else None
    rows = []
    for q in qs:
        f = results / f"{q['id']}.md"
        if not f.exists():
            rows.append({"id": q["id"], "status": "missing output"})
            continue
        text = f.read_text(encoding="utf-8")
        missing = [p for p in q.get("must_mention", []) if not re.search(p, text, re.IGNORECASE | re.DOTALL)]
        forbidden = [p for p in q.get("must_not_mention", []) if re.search(p, text, re.IGNORECASE | re.DOTALL)]
        opts = option_problems(text, defs) if defs else None
        rows.append(
            {
                "id": q["id"],
                "pass": not missing and not forbidden and not opts,
                "missing": missing,
                "forbidden": forbidden,
                "option_problems": opts if opts is not None else "skipped (no GAMS_SYSDIR)",
            }
        )
    graded = [r for r in rows if "pass" in r]
    checked = [r for r in graded if isinstance(r["option_problems"], list)]
    return {
        "summary": {
            "questions": len(qs),
            "graded": len(graded),
            "pass_rate": round(sum(r["pass"] for r in graded) / len(graded), 3) if graded else None,
            "option_validity": round(sum(not r["option_problems"] for r in checked) / len(checked), 3) if checked else "skipped",
        },
        "questions": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    args = ap.parse_args()
    report = grade(Path(args.results))
    (Path(args.results) / "grade_qa.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
