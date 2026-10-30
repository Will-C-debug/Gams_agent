"""Inspect and compare GDX files using the gdxdump utility from the GAMS system directory."""

from __future__ import annotations

import csv
import io
import math
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

SPECIAL = {"eps": 0.0, "na": math.nan, "undf": math.nan, "+inf": math.inf, "-inf": -math.inf, "inf": math.inf}
VALUE_FIELDS = {"Val", "Marginal", "Lower", "Upper", "Scale"}


@dataclass
class SymbolInfo:
    name: str
    dim: int
    type: str  # Set, Par, Var, Equ, Alias
    records: int
    text: str = ""


@dataclass
class SymbolData:
    info: SymbolInfo
    domains: list[str]
    fields: list[str]
    rows: dict[tuple[str, ...], dict[str, float | str]] = field(default_factory=dict)
    eps_keys: set[tuple[str, ...]] = field(default_factory=set)


def _gdxdump(sysdir: Path, *args: str) -> str:
    exe = Path(sysdir) / ("gdxdump.exe" if sys.platform == "win32" else "gdxdump")
    proc = subprocess.run([str(exe), *args], capture_output=True, text=True, timeout=300, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"gdxdump failed ({proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()[:500]}")
    return proc.stdout


def list_symbols(sysdir: Path, gdx: Path) -> list[SymbolInfo]:
    return parse_symbols(_gdxdump(sysdir, str(gdx), "symbols"))


def parse_symbols(text: str) -> list[SymbolInfo]:
    out = []
    for raw in text.splitlines():
        parts = raw.split(None, 5)
        if len(parts) < 5 or not parts[0].isdigit():
            continue
        try:
            out.append(
                SymbolInfo(name=parts[1], dim=int(parts[2]), type=parts[3], records=int(parts[4]), text=parts[5].strip() if len(parts) > 5 else "")
            )
        except ValueError:
            continue
    return out


def read_symbol(sysdir: Path, gdx: Path, info: SymbolInfo) -> SymbolData:
    args = [str(gdx), f"symb={info.name}", "format=csv"]
    if info.type in ("Var", "Equ"):
        args.append("csvAllFields")
    if info.type == "Set":
        args.append("csvSetText")
    return parse_symbol_csv(_gdxdump(sysdir, *args), info)


def parse_symbol_csv(text: str, info: SymbolInfo) -> SymbolData:
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration:
        return SymbolData(info=info, domains=[], fields=[])
    domains = header[: info.dim]
    fields = header[info.dim :]
    data = SymbolData(info=info, domains=domains, fields=fields)
    for row in reader:
        if not row:
            continue
        key = tuple(row[: info.dim])
        values: dict[str, float | str] = {}
        for name, raw in zip(fields, row[info.dim :]):
            if name in VALUE_FIELDS:
                values[name] = _value(raw)
                if raw.strip().lower() == "eps":
                    data.eps_keys.add(key)
            else:
                values[name] = raw
        data.rows[key] = values
    return data


def _value(raw: str) -> float:
    t = raw.strip().strip('"').lower()
    if t in SPECIAL:
        return SPECIAL[t]
    try:
        return float(t)
    except ValueError:
        return math.nan


def inspect(sysdir: Path, gdx: Path, symbol: str | None = None, limit: int = 20) -> dict:
    infos = list_symbols(sysdir, gdx)
    if symbol is None:
        return {"gdx": str(gdx), "symbols": [i.__dict__ for i in infos]}
    info = next((i for i in infos if i.name.lower() == symbol.lower()), None)
    if info is None:
        return {"gdx": str(gdx), "error": f"symbol {symbol!r} not in file"}
    data = read_symbol(sysdir, gdx, info)
    sample = [{"key": list(k), **_jsonable(v)} for k, v in list(data.rows.items())[:limit]]
    return {"gdx": str(gdx), "symbol": info.__dict__, "domains": data.domains, "fields": data.fields, "sample": sample, "records": len(data.rows)}


def _jsonable(values: dict) -> dict:
    out = {}
    for k, v in values.items():
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            out[k] = "NA" if math.isnan(v) else ("+INF" if v > 0 else "-INF")
        else:
            out[k] = v
    return out


def _close(a: float, b: float, rel: float, abs_: float) -> bool:
    if math.isnan(a) or math.isnan(b):
        return math.isnan(a) and math.isnan(b)
    if math.isinf(a) or math.isinf(b):
        return a == b
    return abs(a - b) <= abs_ + rel * max(abs(a), abs(b))


def compare_symbol(a: SymbolData, b: SymbolData, rel: float, abs_: float, fields: list[str] | None = None, top: int = 10) -> dict:
    """Compare two symbols. Missing records count as GAMS defaults (zero levels/values)."""
    result: dict = {"symbol": a.info.name, "type": a.info.type}
    if a.info.type != b.info.type or a.info.dim != b.info.dim:
        result.update(status="structure_changed", a=f"{a.info.type}/{a.info.dim}", b=f"{b.info.type}/{b.info.dim}")
        return result
    if a.info.type == "Set":
        only_a = sorted(set(a.rows) - set(b.rows))
        only_b = sorted(set(b.rows) - set(a.rows))
        result.update(
            status="equal" if not only_a and not only_b else "different",
            only_in_a=[list(k) for k in only_a[:top]],
            only_in_b=[list(k) for k in only_b[:top]],
            counts={"only_in_a": len(only_a), "only_in_b": len(only_b)},
        )
        return result
    fields = fields or (["Val", "Marginal"] if a.info.type in ("Var", "Equ") else ["Val"])
    diffs = []
    keys = set(a.rows) | set(b.rows)
    for key in keys:
        ra, rb = a.rows.get(key, {}), b.rows.get(key, {})
        for f in fields:
            va, vb = ra.get(f, 0.0), rb.get(f, 0.0)
            if not isinstance(va, float) or not isinstance(vb, float):
                continue
            if not _close(va, vb, rel, abs_):
                d = abs(va - vb) if not (math.isnan(va) or math.isnan(vb) or math.isinf(va) or math.isinf(vb)) else math.inf
                diffs.append((d, key, f, va, vb))
    diffs.sort(key=lambda x: -x[0])
    result.update(
        status="equal" if not diffs else "different",
        differing_values=len(diffs),
        records={"a": len(a.rows), "b": len(b.rows)},
        only_in_a=len(set(a.rows) - set(b.rows)),
        only_in_b=len(set(b.rows) - set(a.rows)),
        largest=[
            {"key": list(k), "field": f, "a": _jsonable({"v": va})["v"], "b": _jsonable({"v": vb})["v"], "abs_diff": d if math.isfinite(d) else "inf"}
            for d, k, f, va, vb in diffs[:top]
        ],
    )
    return result


def diff(
    sysdir: Path,
    gdx_a: Path,
    gdx_b: Path,
    rel: float = 1e-6,
    abs_: float = 1e-6,
    symbols: list[str] | None = None,
    top: int = 10,
) -> dict:
    ia = {i.name.lower(): i for i in list_symbols(sysdir, gdx_a)}
    ib = {i.name.lower(): i for i in list_symbols(sysdir, gdx_b)}
    wanted = [s.lower() for s in symbols] if symbols else sorted(set(ia) | set(ib))
    report: dict = {"a": str(gdx_a), "b": str(gdx_b), "tolerance": {"rel": rel, "abs": abs_}, "symbols": []}
    for name in wanted:
        if name not in ia or name not in ib:
            report["symbols"].append({"symbol": name, "status": "only_in_a" if name in ia else "only_in_b" if name in ib else "missing"})
            continue
        if ia[name].type == "Alias":
            continue
        da = read_symbol(sysdir, gdx_a, ia[name])
        db = read_symbol(sysdir, gdx_b, ib[name])
        report["symbols"].append(compare_symbol(da, db, rel, abs_, top=top))
    report["equal"] = all(s.get("status") == "equal" for s in report["symbols"])
    return report
