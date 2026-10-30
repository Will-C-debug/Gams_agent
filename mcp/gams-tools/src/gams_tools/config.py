"""Load and validate the per-repository `.gams-agent.yaml`."""

from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

CONFIG_NAME = ".gams-agent.yaml"
SCRATCH_NAME = ".gams-agent"


class ConfigError(ValueError):
    """Raised when `.gams-agent.yaml` is missing or invalid."""


@dataclass
class Limits:
    reslim: float = 300.0  # seconds handed to GAMS as resLim
    threads: int = 2
    wallclock: float = 900.0  # hard kill of the GAMS process, seconds
    max_output_chars: int = 20000  # cap on text returned to the agent

    def capped_by(self, caps: "Limits") -> "Limits":
        return Limits(
            reslim=min(self.reslim, caps.reslim),
            threads=min(self.threads, caps.threads),
            wallclock=min(self.wallclock, caps.wallclock),
            max_output_chars=min(self.max_output_chars, caps.max_output_chars),
        )


@dataclass
class EntryPoint:
    path: str
    defines: dict[str, str] = field(default_factory=dict)
    workdir: str | None = None  # relative to repo root; defaults to the entry file's folder


@dataclass
class Tolerance:
    rel: float = 1e-6
    abs: float = 1e-6


@dataclass
class TestCase:
    name: str
    entry: str
    defines: dict[str, str] = field(default_factory=dict)
    baseline_gdx: str | None = None
    tolerance: Tolerance = field(default_factory=Tolerance)
    limits: Limits = field(default_factory=Limits)
    symbols: list[str] | None = None  # restrict the baseline comparison


@dataclass
class AtlassianConfig:
    jira_projects: list[str] = field(default_factory=list)
    issue_key_pattern: str | None = None
    confluence_spaces: list[str] = field(default_factory=list)
    spec_labels: list[str] = field(default_factory=list)
    runbook_labels: list[str] = field(default_factory=list)


@dataclass
class Config:
    root: Path
    gams_version: str
    cplex_version: str | None = None
    sysdir: str | None = None
    exec_mode: int = 2
    caps: Limits = field(default_factory=Limits)
    entry_points: list[EntryPoint] = field(default_factory=list)
    test_cases: list[TestCase] = field(default_factory=list)
    protected_paths: list[str] = field(default_factory=list)
    option_files: list[str] = field(default_factory=list)
    atlassian: AtlassianConfig = field(default_factory=AtlassianConfig)
    docs_dirs: list[str] = field(default_factory=list)

    @property
    def scratch_dir(self) -> Path:
        return self.root / SCRATCH_NAME

    def resolve(self, rel: str) -> Path:
        """Resolve a repo-relative path and refuse anything outside the repo or protected."""
        p = (self.root / rel).resolve()
        try:
            rel_posix = p.relative_to(self.root.resolve()).as_posix()
        except ValueError as exc:
            raise ConfigError(f"path {rel!r} is outside the repository") from exc
        if self.is_protected(rel_posix):
            raise ConfigError(f"path {rel!r} is protected by .gams-agent.yaml")
        return p

    def relpath(self, p: Path | str) -> str:
        p = Path(p).resolve()
        try:
            return p.relative_to(self.root.resolve()).as_posix()
        except ValueError:
            return p.as_posix()

    def is_protected(self, rel_posix: str) -> bool:
        return any(_glob_match(rel_posix, pat) for pat in self.protected_paths)

    def entry(self, path: str) -> EntryPoint:
        norm = PurePosixPath(path.replace("\\", "/")).as_posix()
        for ep in self.entry_points:
            if PurePosixPath(ep.path).as_posix() == norm:
                return ep
        known = ", ".join(ep.path for ep in self.entry_points) or "none"
        raise ConfigError(f"{path!r} is not an entry point in {CONFIG_NAME} (known: {known})")

    def test_case(self, name: str) -> TestCase:
        for tc in self.test_cases:
            if tc.name == name:
                return tc
        known = ", ".join(tc.name for tc in self.test_cases) or "none"
        raise ConfigError(f"test case {name!r} is not allowlisted in {CONFIG_NAME} (known: {known})")

    def entry_points_for(self, changed_file: str) -> list[EntryPoint]:
        """Entry points that may be affected by a changed source file.

        GAMS include graphs are only known after compiling, so an entry point is
        considered affected when the file is the entry itself or lives in the
        entry's folder tree. When nothing matches, every entry point is returned.
        """
        rel = self.relpath(changed_file)
        hits = []
        for ep in self.entry_points:
            folder = PurePosixPath(ep.path).parent.as_posix()
            if rel == ep.path or folder in ("", ".") or rel.startswith(folder + "/"):
                hits.append(ep)
        return hits or list(self.entry_points)


def _glob_match(rel_posix: str, pattern: str) -> bool:
    pattern = pattern.replace("\\", "/")
    if pattern.endswith("/**"):
        base = pattern[:-3]
        return rel_posix == base or rel_posix.startswith(base + "/")
    return fnmatch.fnmatch(rel_posix, pattern.replace("**", "*"))


def find_config(start: Path | None = None) -> Path:
    env = os.environ.get("GAMS_AGENT_CONFIG")
    if env:
        return Path(env)
    here = (start or Path.cwd()).resolve()
    for d in (here, *here.parents):
        candidate = d / CONFIG_NAME
        if candidate.is_file():
            return candidate
    raise ConfigError(f"no {CONFIG_NAME} found in {here} or its parents")


def load_config(path: Path | str | None = None) -> Config:
    cfg_path = Path(path) if path else find_config()
    try:
        raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"cannot read {cfg_path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"{cfg_path}: top level must be a mapping")
    return parse_config(raw, cfg_path.parent.resolve())


def parse_config(raw: dict[str, Any], root: Path) -> Config:
    gams = _mapping(raw.get("gams"), "gams")
    version = gams.get("version")
    if version is None:
        raise ConfigError("gams.version is required (e.g. \"53\")")
    exec_mode = int(gams.get("exec_mode", 2))
    if exec_mode not in range(0, 5):
        raise ConfigError("gams.exec_mode must be 0-4 (GAMS execMode)")

    caps = _limits(raw.get("limits"), Limits(), "limits")
    cfg = Config(
        root=root,
        gams_version=str(version),
        cplex_version=_opt_str(gams.get("cplex_version")),
        sysdir=_opt_str(gams.get("sysdir")),
        exec_mode=exec_mode,
        caps=caps,
        protected_paths=[str(p) for p in raw.get("protected_paths") or []],
        option_files=[str(p) for p in raw.get("option_files") or []],
        docs_dirs=[str(p) for p in _mapping(raw.get("docs"), "docs").get("dirs") or []],
    )

    for i, ep in enumerate(raw.get("entry_points") or []):
        ep = _mapping(ep, f"entry_points[{i}]")
        if "path" not in ep:
            raise ConfigError(f"entry_points[{i}].path is required")
        cfg.entry_points.append(
            EntryPoint(path=str(ep["path"]), defines=_defines(ep.get("defines")), workdir=_opt_str(ep.get("workdir")))
        )

    names = set()
    for i, tc in enumerate(raw.get("test_cases") or []):
        tc = _mapping(tc, f"test_cases[{i}]")
        for key in ("name", "entry"):
            if key not in tc:
                raise ConfigError(f"test_cases[{i}].{key} is required")
        if tc["name"] in names:
            raise ConfigError(f"duplicate test case name {tc['name']!r}")
        names.add(tc["name"])
        tol = _mapping(tc.get("tolerance"), f"test_cases[{i}].tolerance")
        cfg.test_cases.append(
            TestCase(
                name=str(tc["name"]),
                entry=str(tc["entry"]),
                defines=_defines(tc.get("defines")),
                baseline_gdx=_opt_str(tc.get("baseline_gdx")),
                tolerance=Tolerance(rel=float(tol.get("rel", 1e-6)), abs=float(tol.get("abs", 1e-6))),
                limits=_limits(tc.get("limits"), Limits(), f"test_cases[{i}].limits").capped_by(caps),
                symbols=[str(s) for s in tc["symbols"]] if tc.get("symbols") else None,
            )
        )

    at = _mapping(raw.get("atlassian"), "atlassian")
    cfg.atlassian = AtlassianConfig(
        jira_projects=[str(x) for x in at.get("jira_projects") or []],
        issue_key_pattern=_opt_str(at.get("issue_key_pattern")),
        confluence_spaces=[str(x) for x in at.get("confluence_spaces") or []],
        spec_labels=[str(x) for x in at.get("spec_labels") or []],
        runbook_labels=[str(x) for x in at.get("runbook_labels") or []],
    )

    entry_paths = {ep.path for ep in cfg.entry_points}
    for tc in cfg.test_cases:
        if tc.entry not in entry_paths:
            raise ConfigError(f"test case {tc.name!r} uses {tc.entry!r}, which is not listed in entry_points")
    return cfg


def _mapping(value: Any, where: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigError(f"{where} must be a mapping")
    return value


def _defines(value: Any) -> dict[str, str]:
    return {str(k): str(v) for k, v in (value or {}).items()}


def _opt_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _limits(value: Any, base: Limits, where: str) -> Limits:
    m = _mapping(value, where)
    try:
        return Limits(
            reslim=float(m.get("reslim", base.reslim)),
            threads=int(m.get("threads", base.threads)),
            wallclock=float(m.get("wallclock", base.wallclock)),
            max_output_chars=int(m.get("max_output_chars", base.max_output_chars)),
        )
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{where}: {exc}") from exc
