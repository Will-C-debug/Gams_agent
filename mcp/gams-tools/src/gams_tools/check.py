"""Deterministic checks for CI (`gams-tools check`): the merge gate that needs no AI."""

from __future__ import annotations

import os
from pathlib import Path

from . import service
from .config import Config


def _solver_for(option_file: str) -> str:
    name = Path(option_file).name.lower()
    return name.split(".", 1)[0] if "." in name else "cplex"


def run_checks(cfg: Config, changed: list[str] | None = None, run_tests: bool = True) -> dict:
    report: dict = {"ok": True, "environment": None, "compile": [], "options": [], "tests": [], "xref": []}

    env = service.environment(cfg)
    report["environment"] = env
    if not env.get("ok"):
        report["ok"] = False

    entries = [ep.path for ep in cfg.entry_points]
    if changed:
        affected: list[str] = []
        for f in changed:
            for ep in cfg.entry_points_for(str(cfg.root / f)):
                if ep.path not in affected:
                    affected.append(ep.path)
        entries = affected or entries

    for entry in entries:
        res = service.compile_entry(cfg, entry)
        report["compile"].append(res)
        report["ok"] &= bool(res.get("ok"))
        if res.get("ok"):
            report["xref"].append(service.symbol_xref(cfg, entry))

    for opt in cfg.option_files:
        res = service.option_validate(cfg, solver=_solver_for(opt), path=opt)
        report["options"].append(res)
        report["ok"] &= bool(res.get("ok"))

    if run_tests:
        for tc in cfg.test_cases:
            if tc.entry not in entries:
                continue
            res = service.run_case(cfg, tc.name)
            report["tests"].append(res)
            report["ok"] &= bool(res.get("ok"))
    return report


def to_markdown(report: dict) -> str:
    icon = lambda ok: "✅" if ok else "❌"  # noqa: E731
    env = report.get("environment") or {}
    out = [f"## GAMS checks {icon(report['ok'])}", ""]
    out.append(
        f"GAMS installed: `{env.get('installed_gams_version')}`, pinned: `{env.get('pinned_gams_version')}` {icon(env.get('ok'))}"
    )
    out += ["", "### Compile", "", "| Entry point | Result | Errors |", "|---|---|---|"]
    for c in report["compile"]:
        errs = "; ".join(f"{e.get('file')}:{e.get('line')} [{e.get('code')}] {e.get('message')}" for e in c.get("errors", [])[:5])
        out.append(f"| `{c.get('entry')}` | {icon(c.get('ok'))} | {errs or c.get('error', '')} |")
    if report["options"]:
        out += ["", "### Option files", "", "| File | Result | Problems |", "|---|---|---|"]
        for o in report["options"]:
            probs = "; ".join(f"line {ln['line']} `{ln['text']}`: {ln['message']}" for ln in o.get("lines", []) if ln["status"] != "ok")
            out.append(f"| `{o.get('source')}` | {icon(o.get('ok'))} | {probs or o.get('error', '')} |")
    if report["tests"]:
        out += ["", "### Regression cases", "", "| Case | Result | Solve status | Baseline |", "|---|---|---|---|"]
        for t in report["tests"]:
            solves = ", ".join(f"{s.get('model')}: {s.get('model_status_text')}" for s in t.get("solves", []))
            base = t.get("baseline") or {}
            if base.get("missing"):
                btxt = "baseline file missing"
            elif base:
                btxt = "equal" if base.get("equal") else "differs: " + ", ".join(s.get("symbol", "?") for s in base.get("symbols", [])[:8])
            else:
                btxt = "no baseline"
            out.append(f"| `{t.get('case')}` | {icon(t.get('ok'))} | {solves or t.get('gams_status', t.get('error', ''))} | {btxt} |")
    findings = [x for x in report["xref"] if x.get("findings")]
    if findings:
        out += ["", "### Cross-reference notes (informational)", ""]
        for x in findings:
            for kind, items in x["findings"].items():
                names = ", ".join(i["symbol"] for i in items[:10])
                out.append(f"- `{x['entry']}` **{kind}**: {names}")
    return "\n".join(out) + "\n"


def write_step_summary(markdown: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(markdown)
