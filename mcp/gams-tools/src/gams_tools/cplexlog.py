"""Summarize GAMS/CPLEX log files (lo=2 log files or captured stdout)."""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field

_JOB_RE = re.compile(r"^--- Job (\S+) Start \S+ \S+ (\d+\.\d+\.\d+)")
_STATUS_RE = re.compile(r"^\*\*\* Status: (.*)$")
_GEN_RE = re.compile(r"^--- Generating (\w+) model (\S+)")
_STATS_RE = re.compile(r"^---\s+(\d+) rows\s+(\d+) columns\s+(\d+) non-zeroes")
_DISC_RE = re.compile(r"^---\s+(\d+) discrete-columns")
_RANGE_RE = re.compile(r"^--- (RHS|Bound|Matrix)\s+\[min, max\] : \[\s*(\S+),\s*(\S+)\](.*)$")
_EXEC_SOLVER_RE = re.compile(r"^--- Executing (\S+) \(Solvelink=(\d+)\)")
_VERSION_ID_RE = re.compile(r"^Version identifier: (\S+)")
_OPT_FILE_RE = re.compile(r"^--- Reading option file '(.*)")
_OPT_SET_RE = re.compile(r"^--- Setting '([^']+)': (.*)$")
_OPT_DEPR_RE = re.compile(r"^--- Option '([^']+)' is deprecated")
_OPT_IGN_RE = re.compile(r"^--- Ignoring '([^']+)': (.*)$")
_SOLVER_STATUS_RE = re.compile(r"^--- (Fixed MIP|LP|MIP|QP|QCP|MIQCP|MIQP|Barrier|Conflict Refiner) status \((\d+)\): (.*?)\.?$")
_CPX_TIME_RE = re.compile(r"^--- Cplex Time: (\S+)sec \(det\. (\S+) ticks\)")
_REDUCED_RE = re.compile(r"^Reduced (MIP|LP) has (\d+) rows, (\d+) columns, and (\d+) nonzeros\.")
_REDUCED_INT_RE = re.compile(r"^Reduced MIP has (\d+) binaries, (\d+) generals, (\d+) SOSs, and (\d+) indicators\.")
_NODE_RE = re.compile(
    r"^(?P<mark>[*H ]?)\s*(?P<node>\d+)(?P<plus>\+?)\s+(?P<left>\d+)\s+(?P<obj>\S+)?\s*(?P<rest>.*)$"
)
_MIP_SOL_RE = re.compile(r"^MIP Solution:\s+(\S+)\s+\((\d+) iterations, (\d+) nodes\)")
_BEST_POSS_RE = re.compile(r"^Best possible:\s+(\S+)")
_ABS_GAP_RE = re.compile(r"^Absolute gap:\s+(\S+)")
_REL_GAP_RE = re.compile(r"^Relative gap:\s+(\S+)")
_ELAPSED_RE = re.compile(r"^Elapsed time = (\S+) sec\. \((\S+) ticks")
_CONFLICT_HDR_RE = re.compile(r"^Number of (equations|variables) in conflict: (\d+)")
_CONFLICT_ROW_RE = re.compile(r"^(fixed|upper|lower|range|sos[12]?|indic\w*)\s*:\s+(\S+)\s*(.*)$")
_CPX_ERR_RE = re.compile(r"^CPLEX Error\s+(\d+): (.*)$")
_GAMS_ERR_RE = re.compile(r"^\*\*\* Error (\d+) in (.*)$")
_PROGRESS_RE = re.compile(r"^--- (?:> )*(\S+?)\((\d+)\)")


@dataclass
class Incumbent:
    node: int
    objective: float | None
    best_bound: float | None
    gap: str | None
    source: str  # '*' integral node, '+' heuristic, 'H' heuristic


@dataclass
class LogSummary:
    job: str | None = None
    gams_version: str | None = None
    status: str | None = None
    demo_license: bool = False
    models: list[dict] = field(default_factory=list)
    solver: str | None = None
    solver_version: str | None = None
    option_file: str | None = None
    options_set: dict[str, str] = field(default_factory=dict)
    options_deprecated: list[str] = field(default_factory=list)
    options_ignored: list[dict] = field(default_factory=list)
    statuses: list[dict] = field(default_factory=list)
    reduced: dict = field(default_factory=dict)
    root_bound: float | None = None
    incumbents: list[Incumbent] = field(default_factory=list)
    nodes: int | None = None
    iterations: int | None = None
    mip_solution: float | None = None
    best_possible: float | None = None
    absolute_gap: float | None = None
    relative_gap: float | None = None
    cplex_seconds: float | None = None
    deterministic_ticks: float | None = None
    conflict: dict | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def parse_log(text: str, max_incumbents: int = 20) -> LogSummary:
    s = LogSummary()
    in_node_log = False
    conflict_kind = None
    last_progress: tuple[str, int] | None = None
    current_model: dict | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if "runs with a demo license" in line or "Demo license" in line:
            s.demo_license = True
        if m := _JOB_RE.match(line):
            s.job, s.gams_version = m.group(1), m.group(2)
        elif m := _STATUS_RE.match(line):
            s.status = m.group(1)
        elif m := _GEN_RE.match(line):
            current_model = {"type": m.group(1), "name": m.group(2), "ranges": {}}
            s.models.append(current_model)
        elif (m := _STATS_RE.match(line)) and current_model is not None:
            current_model.update(rows=int(m.group(1)), columns=int(m.group(2)), nonzeros=int(m.group(3)))
        elif (m := _DISC_RE.match(line)) and current_model is not None:
            current_model["discrete_columns"] = int(m.group(1))
        elif (m := _RANGE_RE.match(line)) and current_model is not None:
            current_model["ranges"][m.group(1).lower()] = _range(m.group(2), m.group(3), m.group(4))
        elif m := _EXEC_SOLVER_RE.match(line):
            s.solver = m.group(1)
        elif m := _VERSION_ID_RE.match(line):
            s.solver_version = m.group(1)
        elif m := _OPT_FILE_RE.match(line):
            s.option_file = m.group(1).rstrip("':")
        elif m := _OPT_SET_RE.match(line):
            s.options_set[m.group(1)] = m.group(2).strip()
        elif m := _OPT_DEPR_RE.match(line):
            s.options_deprecated.append(m.group(1))
        elif m := _OPT_IGN_RE.match(line):
            s.options_ignored.append({"text": m.group(1), "reason": m.group(2)})
        elif m := _SOLVER_STATUS_RE.match(line):
            s.statuses.append({"kind": m.group(1), "code": int(m.group(2)), "text": m.group(3)})
            in_node_log = False
        elif m := _CPX_TIME_RE.match(line):
            s.cplex_seconds, s.deterministic_ticks = _f(m.group(1)), _f(m.group(2))
        elif m := _REDUCED_RE.match(line):
            s.reduced.update(rows=int(m.group(2)), columns=int(m.group(3)), nonzeros=int(m.group(4)))
        elif m := _REDUCED_INT_RE.match(line):
            s.reduced.update(binaries=int(m.group(1)), generals=int(m.group(2)), sos=int(m.group(3)), indicators=int(m.group(4)))
        elif stripped.startswith("Node  Left") and "Best Integer" in stripped:
            in_node_log = True
        elif m := _MIP_SOL_RE.match(line):
            s.mip_solution, s.iterations, s.nodes = _f(m.group(1)), int(m.group(2)), int(m.group(3))
            in_node_log = False
        elif m := _BEST_POSS_RE.match(line):
            s.best_possible = _f(m.group(1))
        elif m := _ABS_GAP_RE.match(line):
            s.absolute_gap = _f(m.group(1))
        elif m := _REL_GAP_RE.match(line):
            s.relative_gap = _f(m.group(1))
        elif m := _CONFLICT_HDR_RE.match(stripped):
            if s.conflict is None:
                s.conflict = {"equations": [], "variables": []}
            conflict_kind = m.group(1)
        elif conflict_kind and (m := _CONFLICT_ROW_RE.match(stripped)):
            s.conflict[conflict_kind].append({"kind": m.group(1), "name": m.group(2), "detail": m.group(3).strip()})
        elif m := _CPX_ERR_RE.match(stripped):
            s.errors.append(f"CPLEX Error {m.group(1)}: {m.group(2)}")
        elif m := _GAMS_ERR_RE.match(line):
            where = f" ({last_progress[0]} line {last_progress[1]})" if last_progress else ""
            s.errors.append(f"GAMS Error {m.group(1)} in {m.group(2)}{where}")
        elif m := _PROGRESS_RE.match(line):
            last_progress = (m.group(1), int(m.group(2)))
        elif in_node_log:
            _node_line(line, s)
        if "Warning" in line and len(s.warnings) < 20:
            s.warnings.append(stripped)
        if conflict_kind and not stripped:
            continue
    if len(s.incumbents) > max_incumbents:
        s.incumbents = s.incumbents[: max_incumbents // 2] + s.incumbents[-max_incumbents // 2 :]
    return s


def _node_line(line: str, s: LogSummary) -> None:
    if not line.strip() or line.strip().startswith(("Elapsed", "Root node", "Real time", "Sequential", "Parallel", "Total")):
        return
    m = _NODE_RE.match(line)
    if not m:
        return
    node = int(m.group("node"))
    mark = m.group("mark").strip()
    obj_tok = m.group("obj")
    rest = (m.group("rest") or "").split()
    if (
        s.root_bound is None
        and node == 0
        and not mark
        and not m.group("plus")
        and obj_tok
        and obj_tok not in ("integral", "infeasible", "cutoff")
    ):
        s.root_bound = _f(obj_tok)
    if mark or m.group("plus"):
        # Incumbent lines: '*  29  27  integral  0  354397.9850  348596.3456  415  1.64%'
        #                  '*   0+   0                95390.0000  45600.0000         52.20%'
        nums = [t for t in ([obj_tok] if obj_tok else []) + rest if t not in ("integral",)]
        gap = next((t for t in nums if t.endswith("%")), None)
        floats = [_f(t) for t in nums if not t.endswith("%")]
        floats = [f for f in floats if f is not None]
        best_int = best_bound = None
        if obj_tok == "integral" and len(floats) >= 3:
            best_int, best_bound = floats[1], floats[2]
        elif len(floats) >= 2:
            best_int, best_bound = floats[0], floats[1]
        s.incumbents.append(
            Incumbent(node=node, objective=best_int, best_bound=best_bound, gap=gap, source=mark or "+")
        )


def _range(lo: str, hi: str, note: str) -> dict:
    lo_f, hi_f = _f(lo), _f(hi)
    d: dict = {"min": lo_f, "max": hi_f, "zeros_observed": "Zero values observed" in note}
    if lo_f and hi_f and lo_f > 0 and hi_f > 0:
        d["orders_of_magnitude"] = round(math.log10(hi_f / lo_f), 1)
    return d


def _f(token: str) -> float | None:
    try:
        return float(token.rstrip("%"))
    except (ValueError, AttributeError):
        return None


def numerics_flags(summary: LogSummary) -> list[str]:
    """Heuristic warnings about coefficient ranges reported by GAMS before the solve."""
    flags = []
    for m in summary.models:
        for kind, r in m.get("ranges", {}).items():
            span = r.get("orders_of_magnitude")
            hi = r.get("max")
            if span is not None and span >= 6:
                flags.append(f"{m['name']}: {kind} values span {span} orders of magnitude; check scaling and big-M values")
            if hi is not None and hi >= 1e7:
                flags.append(f"{m['name']}: largest {kind} value {hi:g}; large coefficients often come from big-M constants")
    return flags
