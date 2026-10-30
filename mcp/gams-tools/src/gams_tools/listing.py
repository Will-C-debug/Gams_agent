"""Parse GAMS listing (.lst) files into structured findings.

The parser targets listings written with `errMsg=1` (the GAMS default), where each
compilation error is followed by a `**** LINE <n> <TYPE> <file>` record that gives
the line number local to the file that contains the error (including include files).
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

_ECHO_RE = re.compile(r"^(\s*(\d+)\s\s)(.*)$")
_MARKER_RE = re.compile(r"^\*\*\*\*(\s+\$.*)$")
_LINE_REC_RE = re.compile(r"^\*\*\*\* LINE\s+(\d+)\s+(\S+)\s+(.+?)\s*$")
_MSG_RE = re.compile(r"^\*\*\*\*\s+(\d+)\s\s(.*)$")
_MSG_CONT_RE = re.compile(r"^\*\*\*\*\s{6,}(\S.*)$")
_COUNT_RE = re.compile(r"^\*\*\*\* (\d+) ERROR\(S\)\s+(\d+) WARNING\(S\)")
_EXEC_ERR_RE = re.compile(r"^\*\*\*\* Exec Error at line (\d+): (.*)$")
_INCLUDE_ROW_RE = re.compile(
    r"^\s+(\d+)\s+(\d+)\s+(INPUT|INCLUDE|BATINCLUDE|LIBINCLUDE|SYSINCLUDE|EXIT|CALL|GDXIN|IF EXIST|IF EXIST2)\s+(\d+)\s+(\d+)\s+(?:(\d+)\s+)?\.?(.+?)\s*$"
)
_SOLVER_STATUS_RE = re.compile(r"^\*\*\*\* SOLVER STATUS\s+(\d+)\s+(.*?)\s*$")
_MODEL_STATUS_RE = re.compile(r"^\*\*\*\* MODEL STATUS\s+(\d+)\s+(.*?)\s*$")
_OBJ_VALUE_RE = re.compile(r"^\*\*\*\* OBJECTIVE VALUE\s+(\S+)")
_RESOURCE_RE = re.compile(r"^\s*RESOURCE USAGE, LIMIT\s+(\S+)\s+(\S+)")
_ITER_RE = re.compile(r"^\s*ITERATION COUNT, LIMIT\s+(\S+)\s+(\S+)")
_REPORT_RE = re.compile(r"(\d+)\s+(NONOPT|INFEASIBLE|UNBOUNDED|ERRORS|REDEFINED|DEPENDENCY)")
_CONFLICT_HDR_RE = re.compile(r"^Number of (equations|variables) in conflict: (\d+)")
_CONFLICT_ROW_RE = re.compile(r"^(fixed|upper|lower|range|sos[12]?|indic\w*|equality|ge|le)\s*:\s+(\S+)\s*(.*)$")
_INFES_RE = re.compile(r"^(\S+?)\.\.\s.*\((LHS = .*?INFES = .*?)\)\s*$")

# Model status codes (GAMS User's Guide, model attribute modelStat).
MODEL_STATUS = {
    1: "Optimal",
    2: "Locally Optimal",
    3: "Unbounded",
    4: "Infeasible",
    5: "Locally Infeasible",
    6: "Intermediate Infeasible",
    7: "Feasible Solution",
    8: "Integer Solution",
    9: "Intermediate Non-Integer",
    10: "Integer Infeasible",
    11: "Licensing Problem",
    12: "Error Unknown",
    13: "Error No Solution",
    14: "No Solution Returned",
    15: "Solved Unique",
    16: "Solved",
    17: "Solved Singular",
    18: "Unbounded - No Solution",
    19: "Infeasible - No Solution",
}
USABLE_MODEL_STATUS = {1, 2, 7, 8, 15, 16, 17}


@dataclass
class CompileError:
    code: int
    message: str
    file: str | None
    line: int | None  # local to `file` when a LINE record is present
    column: int | None  # approximate: position of the `$` marker in the echo print
    listing_line: int | None  # global (echo-print) line number
    included_from: list[str] = field(default_factory=list)  # parent "file:line" chain for include files


@dataclass
class ExecError:
    message: str
    listing_line: int
    file: str | None = None
    line: int | None = None


@dataclass
class SolveSummary:
    model: str | None = None
    objective: str | None = None
    type: str | None = None
    direction: str | None = None
    solver: str | None = None
    from_line: int | None = None
    solver_status: int | None = None
    solver_status_text: str | None = None
    model_status: int | None = None
    model_status_text: str | None = None
    objective_value: float | None = None
    resource_usage: float | None = None
    resource_limit: float | None = None
    iterations: int | None = None
    report: dict[str, int] = field(default_factory=dict)

    @property
    def usable(self) -> bool:
        return self.model_status in USABLE_MODEL_STATUS


@dataclass
class Conflict:
    equations: list[dict] = field(default_factory=list)
    variables: list[dict] = field(default_factory=list)


@dataclass
class ListingSummary:
    error_count: int = 0
    warning_count: int = 0
    compile_errors: list[CompileError] = field(default_factory=list)
    exec_errors: list[ExecError] = field(default_factory=list)
    solves: list[SolveSummary] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)
    initial_point_infeasibilities: list[dict] = field(default_factory=list)
    include_files: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        for s, src in zip(d["solves"], self.solves):
            s["usable"] = src.usable
        return d


def parse_listing(text: str) -> ListingSummary:
    lines = text.splitlines()
    out = ListingSummary()
    out.include_files = _parse_include_summary(lines)

    last_echo: tuple[int, int] | None = None  # (global line, prefix width)
    pending: list[tuple[int, int | None, int | None]] = []  # (code, column, global line)
    pending_loc: tuple[str, int] | None = None
    pending_chain: list[str] = []
    messages: dict[int, str] = {}
    current_solve: SolveSummary | None = None
    conflict: Conflict | None = None
    conflict_kind = None
    last_msg_code: int | None = None

    def flush() -> None:
        nonlocal pending, pending_loc, pending_chain, messages
        for code, col, gline in pending:
            out.compile_errors.append(
                CompileError(
                    code=code,
                    message=messages.get(code, ""),
                    file=pending_loc[0] if pending_loc else None,
                    line=pending_loc[1] if pending_loc else None,
                    column=col,
                    listing_line=gline,
                    included_from=list(pending_chain),
                )
            )
        pending, pending_loc, pending_chain, messages = [], None, [], {}

    for raw in lines:
        m = _MARKER_RE.match(raw)
        if m:
            flush()
            prefix = last_echo[1] if last_echo else 6
            gline = last_echo[0] if last_echo else None
            for dm in re.finditer(r"\$([\d,]+)", raw):
                col = dm.start() - prefix + 1
                for code in dm.group(1).split(","):
                    if code:
                        pending.append((int(code), col if col > 0 else None, gline))
            continue
        m = _LINE_REC_RE.match(raw)
        if m and pending:
            # Innermost file first, then each parent's include statement.
            if pending_loc is None:
                pending_loc = (m.group(3), int(m.group(1)))
            else:
                pending_chain.append(f"{m.group(3)}:{m.group(1)}")
            continue
        m = _MSG_RE.match(raw)
        if m and pending:
            last_msg_code = int(m.group(1))
            messages[last_msg_code] = m.group(2).strip()
            continue
        m = _MSG_CONT_RE.match(raw)
        if m and pending and last_msg_code is not None:
            messages[last_msg_code] += " " + m.group(1).strip()
            continue
        if pending and not raw.startswith("****"):
            flush()
        m = _ECHO_RE.match(raw)
        if m and not raw.startswith("****"):
            last_echo = (int(m.group(2)), len(m.group(1)))
        m = _COUNT_RE.match(raw)
        if m:
            flush()
            out.error_count, out.warning_count = int(m.group(1)), int(m.group(2))
            continue
        m = _EXEC_ERR_RE.match(raw)
        if m:
            gline = int(m.group(1))
            f, ln = _map_global_line(out.include_files, gline)
            out.exec_errors.append(ExecError(message=m.group(2).strip(), listing_line=gline, file=f, line=ln))
            continue

        # Solve summaries
        stripped = raw.strip()
        if stripped.startswith("S O L V E      S U M M A R Y"):
            current_solve = SolveSummary()
            out.solves.append(current_solve)
            continue
        if current_solve is not None:
            _parse_solve_line(raw, current_solve)

        # Conflict refiner output (echoed from the solver log)
        m = _CONFLICT_HDR_RE.match(stripped)
        if m:
            if m.group(1) == "equations" or conflict is None:
                conflict = Conflict()
                out.conflicts.append(conflict)
            conflict_kind = m.group(1)
            continue
        if conflict is not None and conflict_kind:
            m = _CONFLICT_ROW_RE.match(stripped)
            if m:
                row = {"kind": m.group(1), "name": m.group(2), "detail": m.group(3).strip()}
                (conflict.equations if conflict_kind == "equations" else conflict.variables).append(row)
                continue
            if stripped == "":
                continue
            conflict_kind = None

        m = _INFES_RE.match(stripped)
        if m and "INFES" in stripped and len(out.initial_point_infeasibilities) < 50:
            out.initial_point_infeasibilities.append({"row": m.group(1), "detail": m.group(2)})
    flush()
    if not out.error_count and out.compile_errors:
        out.error_count = len(out.compile_errors)
    return out


def _parse_solve_line(raw: str, s: SolveSummary) -> None:
    stripped = raw.strip()
    if stripped.startswith("MODEL ") and s.model is None:
        parts = stripped.split()
        s.model = parts[1] if len(parts) > 1 else None
        if "OBJECTIVE" in parts:
            s.objective = parts[parts.index("OBJECTIVE") + 1]
    elif stripped.startswith("TYPE ") and s.type is None:
        parts = stripped.split()
        s.type = parts[1]
        if "DIRECTION" in parts:
            s.direction = parts[parts.index("DIRECTION") + 1]
    elif stripped.startswith("SOLVER ") and s.solver is None:
        parts = stripped.split()
        s.solver = parts[1]
        if "LINE" in parts:
            try:
                s.from_line = int(parts[parts.index("LINE") + 1])
            except (ValueError, IndexError):
                pass
    m = _SOLVER_STATUS_RE.match(raw)
    if m:
        s.solver_status, s.solver_status_text = int(m.group(1)), m.group(2)
    m = _MODEL_STATUS_RE.match(raw)
    if m:
        s.model_status, s.model_status_text = int(m.group(1)), m.group(2)
    m = _OBJ_VALUE_RE.match(raw)
    if m:
        s.objective_value = _num(m.group(1))
    m = _RESOURCE_RE.match(raw)
    if m:
        s.resource_usage, s.resource_limit = _num(m.group(1)), _num(m.group(2))
    m = _ITER_RE.match(raw)
    if m:
        v = _num(m.group(1))
        s.iterations = int(v) if v is not None else None
    if "REPORT SUMMARY" in raw or (s.report and _REPORT_RE.search(raw)):
        for count, kind in _REPORT_RE.findall(raw):
            s.report[kind] = int(count)


def _parse_include_summary(lines: list[str]) -> list[dict]:
    rows = []
    in_summary = False
    for raw in lines:
        if raw.strip() == "Include File Summary":
            in_summary = True
            continue
        if in_summary:
            m = _INCLUDE_ROW_RE.match(raw)
            if m:
                rows.append(
                    {
                        "seq": int(m.group(1)),
                        "global": int(m.group(2)),
                        "type": m.group(3),
                        "parent": int(m.group(4)),
                        "local": int(m.group(5)),
                        "file": m.group(7),
                    }
                )
            elif rows and raw.strip() and not raw.strip().startswith("SEQ"):
                in_summary = False
    return rows


def _map_global_line(rows: list[dict], gline: int) -> tuple[str | None, int | None]:
    """Map an echo-print line number to (file, local line) using the include summary.

    Lines of an included file start right after the include statement, so a line
    in a child file is `gline - row.global`. When an included file has ended, the
    parent's local line is recovered by subtracting the included files' lengths.
    Needs the files on disk for the lengths; returns (None, None) when ambiguous.
    Only top-level includes are handled exactly; nested includes are approximate.
    """
    if not rows:
        return None, None
    if len(rows) == 1:
        return rows[0]["file"], gline
    lengths: dict[int, int] = {}
    for r in rows:
        try:
            lengths[r["seq"]] = len(Path(r["file"]).read_text(errors="replace").splitlines())
        except OSError:
            return None, None
    for r in rows[1:]:
        if r["type"] == "EXIT":
            continue
        start = r["global"]
        end = start + lengths[r["seq"]]
        if start < gline <= end:
            return r["file"], gline - start
    # Not inside an include: subtract the lengths of includes that ended before gline.
    shift = sum(lengths[r["seq"]] for r in rows[1:] if r["type"] != "EXIT" and r["global"] + lengths[r["seq"]] < gline and r["parent"] == 1)
    return rows[0]["file"], gline - shift


def _num(token: str) -> float | None:
    token = token.strip()
    if token in ("NA", "UNDF", ""):
        return None
    try:
        return float(token.replace("+INF", "inf").replace("-INF", "-inf"))
    except ValueError:
        return None


def summarize_for_agent(summary: ListingSummary, limit: int = 30) -> dict:
    """A compact view suitable for returning to the model."""
    d = summary.to_dict()
    for key in ("compile_errors", "exec_errors", "initial_point_infeasibilities"):
        if len(d[key]) > limit:
            d[key] = d[key][:limit] + [{"truncated": len(d[key]) - limit}]
    return d
