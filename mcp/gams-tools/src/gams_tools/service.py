"""Operations shared by the CLI, the hooks, CI checks and the MCP server.

Every operation returns a JSON-serializable dict, is written to the audit log, and
keeps its output within the configured size cap so the agent gets compact results.
"""

from __future__ import annotations

import getpass
import json
import time
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Callable

from . import cplexlog, errors, gdx, listing, optdef, reffile
from .config import Config, ConfigError
from .gams import GamsNotFound, RunResult, installed_version, run_gams, sysdir, version_matches


def audited(tool: str) -> Callable:
    def deco(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(cfg: Config, *args, **kwargs):
            start = time.monotonic()
            outcome = "ok"
            try:
                result = fn(cfg, *args, **kwargs)
                if isinstance(result, dict) and result.get("ok") is False:
                    outcome = "failed"
                return limit_output(result, cfg.caps.max_output_chars)
            except (ConfigError, GamsNotFound) as exc:
                outcome = "refused"
                return {"ok": False, "error": str(exc)}
            except Exception as exc:  # noqa: BLE001 - reported to the agent and the audit log
                outcome = "error"
                return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
            finally:
                _audit(cfg, tool, args, kwargs, outcome, time.monotonic() - start)

        return wrapper

    return deco


def _audit(cfg: Config, tool: str, args, kwargs, outcome: str, seconds: float) -> None:
    try:
        cfg.scratch_dir.mkdir(parents=True, exist_ok=True)
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "user": getpass.getuser(),
            "tool": tool,
            "args": [str(a)[:200] for a in args],
            "kwargs": {k: str(v)[:200] for k, v in kwargs.items()},
            "outcome": outcome,
            "seconds": round(seconds, 3),
        }
        with open(cfg.scratch_dir / "audit.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
    except OSError:
        pass


def limit_output(obj, max_chars: int):
    """Trim long lists until the JSON form fits within max_chars."""
    if len(json.dumps(obj, default=str)) <= max_chars:
        return obj
    budget = 40
    while budget >= 1:
        trimmed = _trim(obj, budget)
        if len(json.dumps(trimmed, default=str)) <= max_chars:
            return trimmed
        budget //= 2
    return {"ok": False, "error": "output too large even after trimming", "hint": "narrow the request (symbol, section)"}


def _trim(obj, n: int):
    if isinstance(obj, dict):
        return {k: _trim(v, n) for k, v in obj.items()}
    if isinstance(obj, list):
        items = [_trim(v, n) for v in obj[:n]]
        if len(obj) > n:
            items.append({"truncated": len(obj) - n})
        return items
    if isinstance(obj, str) and len(obj) > 2000:
        return obj[:2000] + "...[truncated]"
    return obj


def _catalog(cfg: Config) -> dict[int, str]:
    try:
        return errors.load_errors(sysdir(cfg))
    except (OSError, GamsNotFound):
        return {}


def _run_payload(cfg: Config, rr: RunResult) -> dict:
    return {
        "returncode": rr.returncode,
        "gams_status": rr.status,
        "timed_out": rr.timed_out,
        "seconds": rr.seconds,
        "listing": cfg.relpath(rr.lst),
        "log": cfg.relpath(rr.log),
        "exec_mode": rr.extra.get("exec_mode"),
        "limits": rr.extra.get("limits"),
    }


@audited("gams_compile")
def compile_entry(cfg: Config, entry: str, defines: dict[str, str] | None = None) -> dict:
    ep = cfg.entry(entry)
    rr = run_gams(
        cfg, ep.path, label=f"compile-{Path(ep.path).stem}", action="c", defines={**ep.defines, **(defines or {})}, workdir_rel=ep.workdir
    )
    text = rr.lst.read_text(errors="replace") if rr.lst.exists() else ""
    lst = listing.parse_listing(text)
    catalog = _catalog(cfg)
    errs = []
    for e in lst.compile_errors:
        d = e.__dict__.copy()
        d["file"] = cfg.relpath(e.file) if e.file else None
        d["included_from"] = [cfg.relpath(x.rsplit(":", 1)[0]) + ":" + x.rsplit(":", 1)[1] for x in e.included_from]
        if not d["message"] and e.code in catalog:
            d["message"] = catalog[e.code]
        d["hint"] = errors.HINTS.get(e.code)
        errs.append(d)
    if rr.returncode == 7:
        errs.append({"code": None, "message": "GAMS licensing error: check the license file for this machine/runner"})
    return {
        "ok": rr.returncode == 0,
        "entry": ep.path,
        "action": "compile",
        **_run_payload(cfg, rr),
        "error_count": lst.error_count,
        "warning_count": lst.warning_count,
        "errors": errs,
    }


@audited("gams_run")
def run_case(cfg: Config, case: str) -> dict:
    tc = cfg.test_case(case)
    ep = cfg.entry(tc.entry)
    rr = run_gams(
        cfg,
        ep.path,
        label=f"run-{tc.name}",
        defines={**ep.defines, **tc.defines},
        workdir_rel=ep.workdir,
        limits=tc.limits,
        gdx=True,
    )
    lst = listing.parse_listing(rr.lst.read_text(errors="replace")) if rr.lst.exists() else listing.ListingSummary()
    log = cplexlog.parse_log(rr.log.read_text(errors="replace")) if rr.log.exists() else cplexlog.LogSummary()
    unusable = [s.model for s in lst.solves if not s.usable]
    result = {
        "ok": rr.returncode == 0 and not rr.timed_out and not unusable,
        "case": tc.name,
        "entry": ep.path,
        **_run_payload(cfg, rr),
        "gdx": cfg.relpath(rr.gdx) if rr.gdx and rr.gdx.exists() else None,
        "solves": [dict(s.__dict__, usable=s.usable) for s in lst.solves],
        "unusable_solves": unusable,
        "compile_errors": [e.__dict__ for e in lst.compile_errors],
        "exec_errors": [e.__dict__ for e in lst.exec_errors],
        "conflicts": [c.__dict__ for c in lst.conflicts],
        "solver": _log_brief(log),
        "numerics_flags": cplexlog.numerics_flags(log),
    }
    if tc.baseline_gdx and rr.gdx and rr.gdx.exists():
        base = cfg.resolve(tc.baseline_gdx)
        if base.exists():
            cmp = gdx.diff(sysdir(cfg), base, rr.gdx, tc.tolerance.rel, tc.tolerance.abs, tc.symbols)
            result["baseline"] = {"path": tc.baseline_gdx, "equal": cmp["equal"], "symbols": [s for s in cmp["symbols"] if s.get("status") != "equal"]}
            result["ok"] = result["ok"] and cmp["equal"]
        else:
            result["baseline"] = {"path": tc.baseline_gdx, "missing": True}
    return result


def _log_brief(log: cplexlog.LogSummary) -> dict:
    return {
        "gams_version": log.gams_version,
        "solver": log.solver,
        "solver_version": log.solver_version,
        "demo_license": log.demo_license,
        "models": log.models,
        "statuses": log.statuses,
        "options_set": log.options_set,
        "options_deprecated": log.options_deprecated,
        "options_ignored": log.options_ignored,
        "mip": {
            "root_bound": log.root_bound,
            "solution": log.mip_solution,
            "best_possible": log.best_possible,
            "relative_gap": log.relative_gap,
            "nodes": log.nodes,
            "incumbents": [i.__dict__ for i in log.incumbents],
        }
        if log.mip_solution is not None or log.incumbents
        else None,
        "cplex_seconds": log.cplex_seconds,
        "conflict": log.conflict,
        "errors": log.errors,
    }


@audited("listing_summary")
def listing_summary(cfg: Config, path: str) -> dict:
    p = cfg.resolve(path)
    return {"ok": True, "listing": path, **listing.summarize_for_agent(listing.parse_listing(p.read_text(errors="replace")))}


@audited("log_summary")
def log_summary(cfg: Config, path: str) -> dict:
    p = cfg.resolve(path)
    log = cplexlog.parse_log(p.read_text(errors="replace"))
    return {"ok": True, "log": path, **_log_brief(log), "numerics_flags": cplexlog.numerics_flags(log)}


@audited("gdx_inspect")
def gdx_inspect(cfg: Config, path: str, symbol: str | None = None, limit: int = 20) -> dict:
    return {"ok": True, **gdx.inspect(sysdir(cfg), cfg.resolve(path), symbol, limit)}


@audited("gdx_diff")
def gdx_diff(cfg: Config, a: str, b: str, rel: float = 1e-6, abs_: float = 1e-6, symbols: list[str] | None = None) -> dict:
    report = gdx.diff(sysdir(cfg), cfg.resolve(a), cfg.resolve(b), rel, abs_, symbols)
    report["symbols"] = [s for s in report["symbols"] if s.get("status") != "equal"] or "all compared symbols are equal"
    return {"ok": True, **report}


@audited("symbol_xref")
def symbol_xref(cfg: Config, entry: str, symbol: str | None = None) -> dict:
    ep = cfg.entry(entry)
    rr = run_gams(cfg, ep.path, label=f"xref-{Path(ep.path).stem}", action="c", defines=ep.defines, workdir_rel=ep.workdir, ref=True)
    if rr.returncode != 0 or not rr.ref or not rr.ref.exists():
        return {"ok": False, "entry": ep.path, **_run_payload(cfg, rr), "error": "compilation failed; run gams_compile for details"}
    syms = reffile.parse_reffile(rr.ref.read_text(errors="replace"))
    for s in syms.values():
        for r in s.refs:
            r.file = cfg.relpath(r.file)
    out = {"ok": True, "entry": ep.path, "symbols": len(syms), "findings": reffile.analyze(syms)}
    if symbol:
        out["xref"] = reffile.xref(syms, symbol) or f"symbol {symbol!r} not found"
    return out


@audited("option_validate")
def option_validate(cfg: Config, solver: str = "cplex", path: str | None = None, text: str | None = None) -> dict:
    if path is None and text is None:
        raise ConfigError("give an option file path or option text")
    defs = optdef.load_optdef(sysdir(cfg), solver)
    body = cfg.resolve(path).read_text(errors="replace") if path else text or ""
    checks = optdef.validate_option_text(body, defs)
    return {
        "ok": all(c.status != "error" for c in checks),
        "solver": solver,
        "source": path or "inline",
        "checked_against": f"opt{solver.lower()}.def in {cfg.relpath(sysdir(cfg))}",
        "lines": [c.__dict__ for c in checks],
    }


@audited("option_info")
def option_info(cfg: Config, name: str, solver: str = "cplex") -> dict:
    defs = optdef.load_optdef(sysdir(cfg), solver)
    od, canonical = defs.lookup(name)
    if od is None:
        close = sorted(k for k in defs.options if name.lower()[:4] in k)[:10]
        return {"ok": False, "error": f"{name!r} is not a {solver} option in this GAMS release", "similar": close}
    info = od.to_dict()
    if name.lower() in defs.deprecated:
        info["deprecated"] = defs.deprecated[name.lower()] or True
    return {"ok": True, "solver": solver, "canonical": canonical, **info}


@audited("error_lookup")
def error_lookup(cfg: Config, code: int) -> dict:
    return {"ok": True, **errors.lookup(int(code), _catalog(cfg))}


@audited("environment")
def environment(cfg: Config) -> dict:
    actual = installed_version(cfg)
    return {
        "ok": version_matches(cfg.gams_version, actual),
        "pinned_gams_version": cfg.gams_version,
        "installed_gams_version": actual,
        "pinned_cplex_version": cfg.cplex_version,
        "sysdir": str(sysdir(cfg)),
        "exec_mode": cfg.exec_mode,
        "entry_points": [ep.path for ep in cfg.entry_points],
        "test_cases": [tc.name for tc in cfg.test_cases],
    }
