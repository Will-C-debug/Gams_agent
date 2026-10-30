"""Parse GAMS reference files (`rf=`) into a cross-reference with simple checks."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

USE_KINDS = {"ref", "control", "impl-asn", "index"}
SET_KINDS = {"defined", "assigned", "impl-asn"}


@dataclass
class Reference:
    kind: str
    file: str
    line: int
    column: int


@dataclass
class Symbol:
    name: str
    type: str  # SETS, PARAMETERS, VARIABLES, EQUATIONS, MODELS, ...
    dim: int | None = None
    text: str = ""
    refs: list[Reference] = field(default_factory=list)

    def kinds(self) -> set[str]:
        return {r.kind for r in self.refs}

    def first(self, kind: str) -> Reference | None:
        return next((r for r in self.refs if r.kind == kind), None)


def parse_reffile(text: str) -> dict[str, Symbol]:
    symbols: dict[str, Symbol] = {}
    ids: dict[int, str] = {}
    lines = text.splitlines()
    i = 0
    # Reference section: "<seq> <id> <name> <TYPE> <kind> <gline> <lline> <col> <incl> <fileno> <file>"
    while i < len(lines):
        parts = lines[i].split(maxsplit=10)
        i += 1
        if len(parts) >= 3 and parts[0] == "0" and "symboltable" in lines[i - 1]:
            break
        if len(parts) < 11:
            continue
        try:
            sym_id, line, col = int(parts[1]), int(parts[6]), int(parts[7])
        except ValueError:
            continue
        name, typ, kind, file = parts[2], parts[3], parts[4], parts[10]
        ids[sym_id] = name
        sym = symbols.setdefault(name.lower(), Symbol(name=name, type=typ))
        sym.refs.append(Reference(kind=kind, file=file, line=line, column=col))
    # Symbol table: "<id> <name> <typecode> <TYPENAME> <dim> <count> <domain ids...> <text>"
    while i < len(lines):
        raw = lines[i]
        i += 1
        parts = raw.split()
        if len(parts) >= 3 and parts[0] == "0" and "size of" in raw:
            break
        if len(parts) < 6:
            continue
        try:
            sym_id, dim = int(parts[0]), int(parts[4])
        except ValueError:
            continue
        name = parts[1]
        if name.lower() not in symbols or ids.get(sym_id, "").lower() != name.lower():
            continue
        text_tokens = parts[6 + dim :]
        symbols[name.lower()].dim = dim
        symbols[name.lower()].text = " ".join(text_tokens)
    return symbols


def analyze(symbols: dict[str, Symbol], solved_model_symbols_only: bool = True) -> dict:
    """Checks used by reviews: unused symbols, missing explanatory text, equations not solved."""
    findings: dict[str, list[dict]] = defaultdict(list)
    for sym in symbols.values():
        if sym.type in ("FUNCTIONS", "FILES", "ACRONYMS"):
            continue
        kinds = sym.kinds()
        decl = sym.first("declared") or (sym.refs[0] if sym.refs else None)
        where = {"file": decl.file, "line": decl.line} if decl else {}
        if kinds <= {"declared"}:
            findings["declared_only"].append({"symbol": sym.name, "type": sym.type, **where})
        elif not kinds & USE_KINDS and sym.type != "MODELS":
            findings["never_used"].append({"symbol": sym.name, "type": sym.type, **where})
        if sym.type == "EQUATIONS" and "defined" in kinds and "impl-asn" not in kinds:
            findings["equation_not_in_solved_model"].append({"symbol": sym.name, **where})
        if sym.type == "PARAMETERS" and "ref" in kinds and not kinds & SET_KINDS:
            findings["used_but_never_assigned"].append({"symbol": sym.name, **where})
        if sym.type in ("SETS", "PARAMETERS", "VARIABLES", "EQUATIONS") and not sym.text and "declared" in kinds:
            findings["missing_explanatory_text"].append({"symbol": sym.name, "type": sym.type, **where})
    return dict(findings)


def xref(symbols: dict[str, Symbol], name: str) -> dict | None:
    sym = symbols.get(name.lower())
    if not sym:
        return None
    by_kind: dict[str, list[str]] = defaultdict(list)
    for r in sym.refs:
        by_kind[r.kind].append(f"{r.file}:{r.line}:{r.column}")
    return {"symbol": sym.name, "type": sym.type, "dim": sym.dim, "text": sym.text, "references": dict(by_kind)}
