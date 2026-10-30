"""Locate GAMS and run it with the guardrails from `.gams-agent.yaml`."""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .config import Config, ConfigError, Limits

# GAMS process return codes (GAMS User's Guide, "GAMS Return Codes").
RETURN_CODES = {
    0: "normal return",
    1: "solver is to be called, the system should never return this number",
    2: "compilation error",
    3: "execution error",
    4: "system limits reached",
    5: "file error",
    6: "parameter error",
    7: "licensing error",
    8: "GAMS system error",
    9: "GAMS could not be started",
    10: "out of memory",
    11: "out of disk",
}

_VERSION_RE = re.compile(r"--- Job \S+ Start \S+ \S+ (\d+\.\d+\.\d+)")
_DEFINE_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class GamsNotFound(RuntimeError):
    pass


@dataclass
class RunResult:
    command: list[str]
    returncode: int | None
    timed_out: bool
    seconds: float
    out_dir: Path
    lst: Path
    log: Path
    gdx: Path | None = None
    ref: Path | None = None
    extra: dict = field(default_factory=dict)

    @property
    def status(self) -> str:
        if self.timed_out:
            return "killed: wall-clock limit reached"
        return RETURN_CODES.get(self.returncode, f"return code {self.returncode}")


def find_gams(cfg: Config | None = None) -> Path:
    """Find the gams executable: config sysdir, then GAMS_SYSDIR, then PATH."""
    exe_name = "gams.exe" if sys.platform == "win32" else "gams"
    for d in (cfg.sysdir if cfg else None, os.environ.get("GAMS_SYSDIR")):
        if d:
            exe = Path(d) / exe_name
            if exe.is_file():
                return exe
            raise GamsNotFound(f"{exe} does not exist (check gams.sysdir / GAMS_SYSDIR)")
    found = shutil.which("gams")
    if found:
        return Path(found)
    raise GamsNotFound("GAMS not found: set gams.sysdir in .gams-agent.yaml, GAMS_SYSDIR, or put gams on PATH")


def sysdir(cfg: Config | None = None) -> Path:
    return find_gams(cfg).resolve().parent


def new_run_dir(cfg: Config, label: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", label)[:60]
    d = cfg.scratch_dir / "runs" / f"{stamp}-{safe}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def build_command(
    exe: Path,
    entry: Path,
    out_dir: Path,
    *,
    action: str | None,
    defines: dict[str, str],
    exec_mode: int,
    limits: Limits | None,
    gdx: bool,
    ref: bool,
) -> list[str]:
    cmd = [
        str(exe),
        str(entry),
        f"o={out_dir / 'run.lst'}",
        f"lf={out_dir / 'run.log'}",
        "lo=2",
        "errMsg=1",
        "pageSize=0",
        f"execMode={exec_mode}",
        f"procDir={out_dir / 'proc'}",
    ]
    if action:
        cmd.append(f"a={action}")
    if limits is not None:
        cmd += [f"resLim={limits.reslim:g}", f"threads={limits.threads}"]
    if gdx:
        cmd.append(f"gdx={out_dir / 'results.gdx'}")
    if ref:
        cmd.append(f"rf={out_dir / 'run.ref'}")
    for key, value in defines.items():
        if not _DEFINE_KEY_RE.match(key):
            raise ConfigError(f"invalid define name {key!r}")
        cmd.append(f"--{key}={value}")
    return cmd


def run_gams(
    cfg: Config,
    entry_rel: str,
    *,
    label: str,
    action: str | None = None,
    defines: dict[str, str] | None = None,
    workdir_rel: str | None = None,
    limits: Limits | None = None,
    gdx: bool = False,
    ref: bool = False,
) -> RunResult:
    """Run GAMS on a repo entry point with execMode, caps and a hard wall-clock kill."""
    exe = find_gams(cfg)
    entry = cfg.resolve(entry_rel)
    if not entry.is_file():
        raise ConfigError(f"{entry_rel} does not exist")
    workdir = cfg.resolve(workdir_rel) if workdir_rel else entry.parent
    out_dir = new_run_dir(cfg, label)
    (out_dir / "proc").mkdir(exist_ok=True)
    eff = (limits or cfg.caps).capped_by(cfg.caps)
    cmd = build_command(
        exe,
        entry,
        out_dir,
        action=action,
        defines=defines or {},
        exec_mode=cfg.exec_mode,
        limits=eff if action != "c" else None,
        gdx=gdx,
        ref=ref,
    )
    start = time.monotonic()
    timed_out = False
    popen_kw: dict = {"cwd": workdir, "stdout": subprocess.DEVNULL, "stderr": subprocess.PIPE}
    if os.name == "posix":
        popen_kw["start_new_session"] = True
    proc = subprocess.Popen(cmd, **popen_kw)
    try:
        _, err = proc.communicate(timeout=eff.wallclock)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_tree(proc)
        _, err = proc.communicate()
    seconds = time.monotonic() - start
    shutil.rmtree(out_dir / "proc", ignore_errors=True)
    return RunResult(
        command=cmd,
        returncode=proc.returncode,
        timed_out=timed_out,
        seconds=round(seconds, 3),
        out_dir=out_dir,
        lst=out_dir / "run.lst",
        log=out_dir / "run.log",
        gdx=(out_dir / "results.gdx") if gdx else None,
        ref=(out_dir / "run.ref") if ref else None,
        extra={"stderr": (err or b"").decode(errors="replace")[-2000:], "limits": eff.__dict__, "exec_mode": cfg.exec_mode},
    )


def _kill_tree(proc: subprocess.Popen) -> None:
    try:
        if os.name == "posix":
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            proc.kill()
    except ProcessLookupError:
        pass


def installed_version(cfg: Config) -> str | None:
    """Return the GAMS version (e.g. 53.5.1) by compiling an empty program."""
    exe = find_gams(cfg)
    d = new_run_dir(cfg, "version")
    probe = d / "probe.gms"
    probe.write_text("* version probe\n", encoding="utf-8")
    (d / "proc").mkdir(exist_ok=True)
    subprocess.run(
        [str(exe), str(probe), "a=c", f"o={d / 'probe.lst'}", f"lf={d / 'probe.log'}", "lo=2", f"procDir={d / 'proc'}"],
        cwd=d,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=60,
        check=False,
    )
    shutil.rmtree(d / "proc", ignore_errors=True)
    log = d / "probe.log"
    text = log.read_text(errors="replace") if log.exists() else ""
    m = _VERSION_RE.search(text)
    return m.group(1) if m else None


def version_matches(pinned: str, actual: str | None) -> bool:
    """`53` matches 53.x.y; `53.5` matches 53.5.y; `53.5.1` must match exactly."""
    if actual is None:
        return False
    want = pinned.split(".")
    have = actual.split(".")
    return have[: len(want)] == want
