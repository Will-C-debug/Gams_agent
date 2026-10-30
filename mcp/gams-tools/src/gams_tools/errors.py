"""Look up GAMS error messages from gamserrs.txt in the GAMS system directory."""

from __future__ import annotations

import re
from pathlib import Path

_ROW_RE = re.compile(r"^\s*(\d+)\s(.*)$")

# Short, practical hints for errors that come up often in reviews. The message text
# itself always comes from the installed gamserrs.txt.
HINTS = {
    66: "A symbol is used before it has data. Check the data load and $include order, and spurious commas in explanatory text.",
    140: "Unknown symbol: a typo, a missing declaration, or a reserved word used as a name (e.g. 'logic').",
    141: "Declared but never assigned before use. Check the data load ($load/execute_load) and its domain filtering.",
    148: "Wrong number of indices for the symbol's declared dimension.",
    149: "An index is used that is not controlled by the equation domain or a sum/loop; add it to the domain or sum over it.",
    170: "Label not in the domain set. Check spelling/case of labels in data and use $loadDC to catch these at load time.",
    257: "Follows from earlier compilation errors; fix those first.",
    409: "GAMS lost track of the statement; often a missing ';' on the previous line.",
    542: "Blocked by execMode: $call/embedded code is not allowed for agent runs. Ask the user to run it, or adjust gams.exec_mode in .gams-agent.yaml.",
}


def load_errors(sysdir: Path) -> dict[int, str]:
    path = Path(sysdir) / "gamserrs.txt"
    return parse_errors(path.read_text(encoding="utf-8", errors="replace"))


def parse_errors(text: str) -> dict[int, str]:
    out: dict[int, list[str]] = {}
    for raw in text.splitlines():
        if raw.startswith("*"):
            continue
        m = _ROW_RE.match(raw)
        if not m:
            continue
        code, msg = int(m.group(1)), m.group(2).strip()
        out.setdefault(code, []).append(msg)
    return {code: " ".join(parts) for code, parts in out.items()}


def lookup(code: int, catalog: dict[int, str]) -> dict:
    return {"code": code, "message": catalog.get(code, "unknown error code"), "hint": HINTS.get(code)}
