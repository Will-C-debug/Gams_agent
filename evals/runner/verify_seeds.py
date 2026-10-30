"""Check that every seeded defect is real: compile and run base and seeded models with gams-tools
and record the observable effect (compile errors, status, objective, lambda, xref findings).

    GAMS_SYSDIR=/path/to/gams53 python evals/runner/verify_seeds.py [--cases evals/seeded_defects/uc_small.yaml]

Writes evals/seeded_defects/effects.json. Needs a licensed GAMS installation.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from pathlib import Path

from common import EVALS, load_cases, location_line, materialize

from gams_tools import gdx, service
from gams_tools.config import load_config
from gams_tools.gams import installed_version, sysdir


def observe(model_dir: Path) -> dict:
    cfg = load_config(model_dir / ".gams-agent.yaml")
    comp = service.compile_entry(cfg, cfg.entry_points[0].path)
    if not comp.get("ok"):
        return {"compile_errors": sorted({e.get("code") for e in comp.get("errors", []) if e.get("code")})}
    xref = service.symbol_xref(cfg, cfg.entry_points[0].path)
    run = service.run_case(cfg, cfg.test_cases[0].name)
    obs: dict = {
        "returncode": run.get("returncode"),
        "model_status": [s.get("model_status_text") for s in run.get("solves", [])],
        "objective": next((s.get("objective_value") for s in run.get("solves", [])), None),
        "exec_errors": [e.get("message") for e in run.get("exec_errors", [])],
        "not_in_solved_model": [f["symbol"] for f in xref.get("findings", {}).get("equation_not_in_solved_model", [])],
        "options_deprecated": (run.get("solver") or {}).get("options_deprecated", []),
    }
    if run.get("gdx"):
        g = cfg.root / run["gdx"]
        infos = {i.name: i for i in gdx.list_symbols(sysdir(cfg), g)}
        if "lambda" in infos:
            data = gdx.read_symbol(sysdir(cfg), g, infos["lambda"])
            vals = [data.rows.get((f"h{i}",), {}).get("Val", 0.0) for i in range(1, 9)]
            obs["lambda"] = ["NA" if isinstance(v, float) and math.isnan(v) else v for v in vals]
    return obs


def effect(base: dict, seeded: dict) -> str:
    if "compile_errors" in seeded:
        return f"compilation error(s) {seeded['compile_errors']}"
    parts = []
    if seeded.get("exec_errors"):
        parts.append(f"execution error: {seeded['exec_errors'][0]}")
    if seeded.get("model_status") != base.get("model_status"):
        parts.append(f"model status {base.get('model_status')} -> {seeded.get('model_status')}")
    if seeded.get("objective") != base.get("objective"):
        parts.append(f"objective {base.get('objective')} -> {seeded.get('objective')}")
    if seeded.get("lambda") != base.get("lambda"):
        parts.append(f"lambda {base.get('lambda')} -> {seeded.get('lambda')}")
    if seeded.get("not_in_solved_model"):
        parts.append(f"equations not in solved model: {seeded['not_in_solved_model']}")
    if seeded.get("options_deprecated"):
        parts.append(f"deprecated options: {seeded['options_deprecated']}")
    return "; ".join(parts) or "no observable effect on this dataset (code-reading defect)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=str(EVALS / "seeded_defects" / "uc_small.yaml"))
    args = ap.parse_args()
    base_dir, cases = load_cases(Path(args.cases))
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        base_obs = observe(materialize(base_dir, None, tmp / "base"))
        cfg = load_config(tmp / "base" / ".gams-agent.yaml")
        report = {"gams_version": installed_version(cfg), "base": base_obs, "cases": {}}
        for case in cases:
            d = materialize(base_dir, case, tmp / case["id"])
            obs = observe(d)
            report["cases"][case["id"]] = {
                "title": case["title"],
                "location_text": location_line(d, case).strip(),
                "effect": effect(base_obs, obs),
                "observed": obs,
            }
            print(f"{case['id']}: {report['cases'][case['id']]['effect']}")
    out = EVALS / "seeded_defects" / "effects.json"
    out.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
