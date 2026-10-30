"""Agent hook handlers (VS Code agent hooks / Copilot CLI / cloud agent).

Hook payloads arrive as JSON on stdin. Field names differ a little between hosts
(`tool_name` vs `toolName`, `tool_input` vs `toolArgs`), so the handlers accept both.
A handler returns (exit_code, stdout, stderr). Exit code 2 blocks the action and
feeds stderr back to the agent; 0 lets it proceed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import service
from .config import Config
from .gams import GamsNotFound, installed_version, version_matches

GAMS_SOURCE_EXT = {".gms", ".inc"}
_GAMS_CMD_RE = re.compile(r"(^|[\s;&|(`'\"/\\])gams(\.exe)?(\s|$|['\"`])", re.IGNORECASE)
_ATLASSIAN_WRITE_RE = re.compile(r"^(create|edit|update|add|transition|delete|move|post|upload|set|assign)", re.IGNORECASE)
_ATLASSIAN_TOOL_RE = re.compile(r"(atlassian|jira|confluence)", re.IGNORECASE)
_PATH_KEYS = ("file_path", "filePath", "path", "paths", "files", "filePaths", "uri", "target_file", "targetFile")
_CMD_KEYS = ("command", "cmd", "commandLine", "script", "input")


def _tool(payload: dict) -> tuple[str, dict]:
    name = payload.get("tool_name") or payload.get("toolName") or payload.get("tool") or ""
    args = payload.get("tool_input") or payload.get("toolInput") or payload.get("toolArgs") or {}
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            args = {"input": args}
    return str(name), args if isinstance(args, dict) else {}


def _paths(args: dict) -> list[str]:
    out: list[str] = []
    for key in _PATH_KEYS:
        v = args.get(key)
        if isinstance(v, str):
            out.append(v)
        elif isinstance(v, list):
            out += [x for x in v if isinstance(x, str)]
    for v in args.values():  # e.g. apply_patch-style inputs that embed file names
        if isinstance(v, str):
            out += re.findall(r"[\w./\\-]+\.(?:gms|inc|opt|op\d|o\d\d)\b", v)
    return [p.replace("file://", "") for p in out]


def _commands(args: dict) -> list[str]:
    return [args[k] for k in _CMD_KEYS if isinstance(args.get(k), str)]


def _deny(reason: str) -> tuple[int, str, str]:
    decision = {"permissionDecision": "deny", "permissionDecisionReason": reason}
    return 2, json.dumps(decision), reason


def pre_tool_use(cfg: Config, payload: dict) -> tuple[int, str, str]:
    name, args = _tool(payload)
    short = re.split(r"[/.]", name)[-1].split("_")[-1]
    if _ATLASSIAN_TOOL_RE.search(name) and _ATLASSIAN_WRITE_RE.search(short):
        return _deny(f"{name}: writing to Jira/Confluence is not enabled for the gams-sme agent (read-only in v1).")
    for cmd in _commands(args):
        if _GAMS_CMD_RE.search(cmd) and "gams-tools" not in cmd:
            return _deny(
                "Run GAMS through gams-tools (gams_compile / gams_run, or `gams-tools compile|run`) so execMode, "
                "time/thread limits and allowlisted test cases apply."
            )
        for pat in cfg.protected_paths:
            base = pat.replace("/**", "").replace("**", "").rstrip("/")
            if base and base in cmd.replace("\\", "/"):
                return _deny(f"command touches protected path {pat!r} (see .gams-agent.yaml).")
    for p in _paths(args):
        try:
            rel = cfg.relpath(Path(p) if Path(p).is_absolute() else cfg.root / p)
        except OSError:
            continue
        if cfg.is_protected(rel):
            return _deny(f"{rel} is a protected path (see .gams-agent.yaml).")
    return 0, "", ""


def post_tool_use(cfg: Config, payload: dict) -> tuple[int, str, str]:
    _, args = _tool(payload)
    changed = [p for p in _paths(args) if Path(p).suffix.lower() in GAMS_SOURCE_EXT]
    if not changed:
        return 0, "", ""
    entries: list[str] = []
    for p in changed:
        for ep in cfg.entry_points_for(p if Path(p).is_absolute() else str(cfg.root / p)):
            if ep.path not in entries:
                entries.append(ep.path)
    problems = []
    for entry in entries:
        res = service.compile_entry(cfg, entry)
        if res.get("ok"):
            continue
        if "error" in res and "errors" not in res:
            return 0, "", f"gams-tools: compile check skipped: {res['error']}"
        lines = [f"{entry}: {res.get('error_count', '?')} compilation error(s)"]
        for e in res.get("errors", [])[:15]:
            loc = f"{e.get('file')}:{e.get('line')}" if e.get("line") else (e.get("file") or "?")
            hint = f" Hint: {e['hint']}" if e.get("hint") else ""
            lines.append(f"  {loc} col {e.get('column')}: error {e.get('code')}: {e.get('message')}.{hint}")
        problems.append("\n".join(lines))
    if problems:
        msg = "GAMS compile check failed after your edit. Fix these before continuing:\n" + "\n".join(problems)
        return 2, "", msg
    return 0, f"GAMS compile check passed for: {', '.join(entries)}", ""


def session_start(cfg: Config, payload: dict) -> tuple[int, str, str]:
    try:
        actual = installed_version(cfg)
    except GamsNotFound as exc:
        return 0, f"gams-sme: GAMS not found ({exc}). Compile checks and runs are unavailable in this session.", ""
    if version_matches(cfg.gams_version, actual):
        return 0, f"gams-sme: GAMS {actual} matches the pinned release {cfg.gams_version}.", ""
    return (
        0,
        f"gams-sme WARNING: installed GAMS {actual} does not match the pinned release {cfg.gams_version} in "
        ".gams-agent.yaml. Results and option checks may differ from production.",
        "",
    )


HANDLERS = {
    "pre-tool-use": pre_tool_use,
    "post-tool-use": post_tool_use,
    "session-start": session_start,
}
