"""Read GAMS solver option definitions (opt<solver>.def) and validate option files.

The definition file shipped in the GAMS system directory is the authority on which
options the installed solver link accepts, so validation always uses the installed
release (GAMS 53 for us) rather than documentation or memory.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

_SPECIAL = {
    "mindouble": -math.inf,
    "maxdouble": math.inf,
    "minint": -(2**31),
    "maxint": 2**31 - 1,
}
_OPTION_TYPES = {"boolean", "integer", "double", "enumint", "enumstr", "string", "strlist", "immediate"}


@dataclass
class OptionDef:
    name: str
    type: str
    default: str | None = None
    min: float | None = None
    max: float | None = None
    visible: bool = True
    group: int | None = None
    description: str = ""
    values: dict[str, str] = field(default_factory=dict)  # enum value -> description
    dot_option: bool = False

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "type": self.type,
            "default": self.default,
            "description": self.description,
            "dot_option": self.dot_option,
            "internal": not self.visible,
        }
        if self.min is not None or self.max is not None:
            d["range"] = [_fmt(self.min), _fmt(self.max)]
        if self.values:
            d["values"] = self.values
        return d


@dataclass
class OptionDefs:
    solver: str
    options: dict[str, OptionDef] = field(default_factory=dict)
    synonyms: dict[str, str] = field(default_factory=dict)
    deprecated: dict[str, str] = field(default_factory=dict)
    indicator_keywords: set[str] = field(default_factory=set)
    eol_comment: str | None = None
    groups: dict[int, str] = field(default_factory=dict)

    def lookup(self, name: str) -> tuple[OptionDef | None, str | None]:
        """Return (definition, canonical name) for an option or synonym."""
        key = name.lower()
        if key in self.options:
            return self.options[key], self.options[key].name
        if key in self.synonyms:
            target = self.synonyms[key]
            return self.options.get(target.lower()), target
        dot = "." + key
        if dot in self.options:
            return self.options[dot], self.options[dot].name
        return None, None


def _tokens(line: str) -> list[str]:
    return re.findall(r'"[^"]*"|\S+', line)


def _num(token: str) -> float | None:
    t = token.lower()
    if t in _SPECIAL:
        return float(_SPECIAL[t])
    try:
        return float(t)
    except ValueError:
        return None


def _fmt(v: float | None):
    if v is None:
        return None
    if math.isinf(v):
        return "+inf" if v > 0 else "-inf"
    return int(v) if float(v).is_integer() and abs(v) < 1e15 else v


def parse_optdef(text: str, solver: str) -> OptionDefs:
    defs = OptionDefs(solver=solver)
    current: OptionDef | None = None
    dep_section = False
    for raw in text.splitlines():
        if not raw.strip() or raw.startswith("*"):
            continue
        if raw[0].isspace():
            toks = _tokens(raw.strip())
            if dep_section and toks:
                defs.deprecated[toks[0].lower()] = " ".join(toks[1:])
            elif current is not None and toks:
                value = toks[0].strip('"')
                if current.type in ("enumint", "enumstr") and len(toks) >= 2 and toks[1] in ("0", "1"):
                    current.values[value] = " ".join(toks[2:])
                else:
                    current.values[value] = " ".join(toks[1:])
            continue
        toks = _tokens(raw)
        current, dep_section = None, False
        if len(toks) < 2:
            continue
        name, typ = toks[0], toks[1]
        if typ == "synonym" and len(toks) >= 3:
            defs.synonyms[name.lower()] = toks[2]
        elif typ == "indicator":
            defs.indicator_keywords.add(name.lower())
        elif typ == "EOLCOMM" and len(toks) >= 3:
            defs.eol_comment = toks[2]
        elif typ == "deprecated":
            dep_section = True
        elif typ == "group" and len(toks) >= 3:
            try:
                defs.groups[int(toks[2])] = " ".join(toks[4:])
            except ValueError:
                pass
        elif typ in _OPTION_TYPES:
            current = _parse_option(name, typ, toks[2:])
            defs.options[current.name.lower()] = current
    # Synonyms listed in a deprecated section are deprecated aliases.
    for syn, target in defs.synonyms.items():
        if syn in defs.deprecated and not defs.deprecated[syn]:
            defs.deprecated[syn] = f"use {target}"
    return defs


def _parse_option(name: str, typ: str, rest: list[str]) -> OptionDef:
    od = OptionDef(name=name, type=typ, dot_option=name.startswith("."))
    r = rest[1:]  # rest[0] is the solver's internal reference number
    try:
        if typ in ("integer", "double"):
            od.default, od.min, od.max = r[0], _num(r[1]), _num(r[2])
            od.visible, od.group, desc = r[3] == "1", int(r[4]), r[5:]
        elif typ in ("boolean", "enumint", "enumstr", "string"):
            od.default = r[0].strip('"')
            od.visible, od.group, desc = r[1] == "1", int(r[2]), r[3:]
        elif typ == "strlist":
            od.visible, od.group, desc = r[0] == "1", int(r[1]), r[2:]
        else:  # immediate: "<name> immediate <keyword> <vis> <group> <text>"
            od.visible, od.group, desc = r[0] == "1", int(r[1]) if len(r) > 1 else None, r[2:]
    except (IndexError, ValueError):
        desc = r
    od.description = " ".join(desc)
    if typ == "boolean":
        od.min, od.max = 0, 1
    return od


def load_optdef(sysdir: Path, solver: str = "cplex") -> OptionDefs:
    path = Path(sysdir) / f"opt{solver.lower()}.def"
    return parse_optdef(path.read_text(encoding="utf-8", errors="replace"), solver.lower())


@dataclass
class OptionCheck:
    line: int
    text: str
    status: str  # ok | warning | error | comment
    option: str | None = None
    canonical: str | None = None
    message: str = ""
    default: str | None = None
    description: str = ""


def validate_option_text(text: str, defs: OptionDefs) -> list[OptionCheck]:
    results = []
    for n, raw in enumerate(text.splitlines(), start=1):
        line = raw
        if defs.eol_comment and defs.eol_comment in line:
            line = line.split(defs.eol_comment, 1)[0]
        stripped = line.strip()
        if not stripped or stripped.startswith("*"):
            continue
        results.append(_check_line(n, raw.strip(), stripped, defs))
    return results


def _check_line(n: int, raw: str, stripped: str, defs: OptionDefs) -> OptionCheck:
    m = re.match(r"^([^\s=]+)\s*(?:=\s*|\s+)?(.*)$", stripped)
    name, value = (m.group(1), m.group(2).strip()) if m else (stripped, "")
    chk = OptionCheck(line=n, text=raw, status="ok", option=name)
    lname = name.lower()

    if lname in defs.indicator_keywords:
        chk.canonical, chk.message = name, "indicator constraint definition (checked by the solver link at run time)"
        return chk

    od, canonical = defs.lookup(lname)
    if od is None and "." in lname:
        # Dot options: <gams symbol>.<option>[(indices)] <value>, e.g. x.feaspref 2 or e.lazy 1
        suffix = re.sub(r"\(.*$", "", lname.rsplit(".", 1)[1])
        od = defs.options.get("." + suffix)
        if od is not None:
            chk.canonical = od.name
            chk.message = f"dot option {od.name} applied to GAMS symbol {name.split('.', 1)[0]}"
            chk.description = od.description
            return _check_value(chk, od, value)
    if od is None:
        chk.status = "error"
        chk.message = f"unknown {defs.solver.upper()} option; GAMS/{defs.solver.upper()} ignores it ('invalid option name')"
        return chk

    chk.canonical, chk.default, chk.description = canonical, od.default, od.description
    notes, warn = [], False
    if lname in defs.deprecated:
        notes.append(f"deprecated: {defs.deprecated[lname] or 'see solver manual'}")
        warn = True
    if lname != od.name.lower() and lname in defs.synonyms and not warn:
        notes.append(f"synonym for {od.name}")
    if not od.visible:
        notes.append("internal option normally set by GAMS (e.g. through model attributes); avoid setting it here")
        warn = True
    chk.message = "; ".join(notes)
    if warn:
        chk.status = "warning"
    return _check_value(chk, od, value)


def _check_value(chk: OptionCheck, od: OptionDef, value: str) -> OptionCheck:
    def fail(msg: str) -> OptionCheck:
        chk.status = "error"
        chk.message = (chk.message + "; " if chk.message else "") + msg
        return chk

    t = od.type
    if t in ("string", "strlist", "immediate"):
        return chk
    if value == "":
        return fail("missing value")
    if t in ("boolean", "integer", "enumint"):
        v = _num(value)
        if v is None or not float(v).is_integer():
            if t == "boolean" and value.lower() in ("yes", "no", "true", "false"):
                return chk
            return fail(f"expected an integer value, got {value!r}")
        if t == "enumint" and od.values and str(int(v)) not in od.values:
            return fail(f"value {int(v)} not allowed; allowed: {', '.join(od.values)}")
        if od.min is not None and v < od.min or od.max is not None and v > od.max:
            return fail(f"value {value} outside [{_fmt(od.min)}, {_fmt(od.max)}]")
        return chk
    if t == "double":
        v = _num(value)
        if v is None:
            return fail(f"expected a number, got {value!r}")
        if od.min is not None and v < od.min or od.max is not None and v > od.max:
            return fail(f"value {value} outside [{_fmt(od.min)}, {_fmt(od.max)}]")
        return chk
    if t == "enumstr":
        allowed = {k.lower() for k in od.values}
        if allowed and value.strip('"').lower() not in allowed:
            return fail(f"value {value!r} not allowed; allowed: {', '.join(od.values)}")
    return chk
