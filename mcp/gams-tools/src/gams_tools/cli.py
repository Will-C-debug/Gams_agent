"""Command-line entry point: `gams-tools <command>`."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__, check, docs, hooks, service
from .config import ConfigError, load_config


def _print(obj) -> None:
    print(json.dumps(obj, indent=2, default=str))


def _defines(pairs: list[str] | None) -> dict[str, str]:
    out = {}
    for p in pairs or []:
        if "=" not in p:
            raise SystemExit(f"--define expects key=value, got {p!r}")
        k, v = p.split("=", 1)
        out[k] = v
    return out


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="gams-tools", description="Guarded GAMS/CPLEX tooling for the gams-sme agent.")
    ap.add_argument("--config", help="path to .gams-agent.yaml (default: search upward from the current folder)")
    ap.add_argument("--version", action="version", version=f"gams-tools {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("compile", help="compile an entry point (action=c)")
    p.add_argument("entry")
    p.add_argument("--define", "-D", action="append", help="extra --key=value define, as key=value")

    p = sub.add_parser("run", help="run an allowlisted test case")
    p.add_argument("case")

    p = sub.add_parser("listing", help="summarize a listing (.lst) file")
    p.add_argument("path")

    p = sub.add_parser("log", help="summarize a GAMS/CPLEX log file")
    p.add_argument("path")

    p = sub.add_parser("gdx-inspect", help="list symbols or sample one symbol of a GDX file")
    p.add_argument("path")
    p.add_argument("--symbol")
    p.add_argument("--limit", type=int, default=20)

    p = sub.add_parser("gdx-diff", help="compare two GDX files with tolerances")
    p.add_argument("a")
    p.add_argument("b")
    p.add_argument("--rel", type=float, default=1e-6)
    p.add_argument("--abs", type=float, default=1e-6)
    p.add_argument("--symbol", action="append")

    p = sub.add_parser("xref", help="cross-reference and unused-symbol checks for an entry point")
    p.add_argument("entry")
    p.add_argument("--symbol")

    p = sub.add_parser("validate-options", help="validate a solver option file against the installed GAMS release")
    p.add_argument("path")
    p.add_argument("--solver", default="cplex")

    p = sub.add_parser("option-info", help="describe one solver option as defined by the installed GAMS release")
    p.add_argument("name")
    p.add_argument("--solver", default="cplex")

    p = sub.add_parser("error", help="explain a GAMS error code")
    p.add_argument("code", type=int)

    p = sub.add_parser("docs", help="search the configured documentation folders")
    p.add_argument("query")
    p.add_argument("--scope")

    sub.add_parser("env", help="show the GAMS installation and pinned versions")

    p = sub.add_parser("check", help="CI gate: compile, validate option files, run regression cases")
    p.add_argument("--changed", nargs="*", help="only check entry points affected by these files")
    p.add_argument("--no-tests", action="store_true")
    p.add_argument("--format", choices=["json", "md"], default="md")

    p = sub.add_parser("hook", help="agent hook handler; reads the hook payload from stdin")
    p.add_argument("event", choices=sorted(hooks.HANDLERS))

    sub.add_parser("mcp", help="start the MCP server on stdio")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.cmd == "mcp":
        from .mcp_server import serve

        serve(args.config)
        return 0

    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        if args.cmd == "hook":  # never break the agent session because of config problems
            print(f"gams-tools hook skipped: {exc}", file=sys.stderr)
            return 0
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.cmd == "hook":
        raw = sys.stdin.read()
        try:
            payload = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            payload = {}
        code, out, err = hooks.HANDLERS[args.event](cfg, payload)
        if out:
            print(out)
        if err:
            print(err, file=sys.stderr)
        return code

    if args.cmd == "check":
        report = check.run_checks(cfg, changed=args.changed, run_tests=not args.no_tests)
        md = check.to_markdown(report)
        check.write_step_summary(md)
        if args.format == "md":
            print(md)
        else:
            _print(report)
        return 0 if report["ok"] else 1

    dispatch = {
        "compile": lambda: service.compile_entry(cfg, args.entry, _defines(args.define)),
        "run": lambda: service.run_case(cfg, args.case),
        "listing": lambda: service.listing_summary(cfg, args.path),
        "log": lambda: service.log_summary(cfg, args.path),
        "gdx-inspect": lambda: service.gdx_inspect(cfg, args.path, args.symbol, args.limit),
        "gdx-diff": lambda: service.gdx_diff(cfg, args.a, args.b, args.rel, args.abs, args.symbol),
        "xref": lambda: service.symbol_xref(cfg, args.entry, args.symbol),
        "validate-options": lambda: service.option_validate(cfg, args.solver, path=args.path),
        "option-info": lambda: service.option_info(cfg, args.name, args.solver),
        "error": lambda: service.error_lookup(cfg, args.code),
        "docs": lambda: docs.search(cfg, args.query, args.scope),
        "env": lambda: service.environment(cfg),
    }
    result = dispatch[args.cmd]()
    _print(result)
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    sys.exit(main())
