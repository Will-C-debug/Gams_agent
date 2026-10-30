"""Parser tests against real GAMS output captured in tests/fixtures."""

import math

from gams_tools import cplexlog, errors, gdx, listing, optdef, reffile


def test_compile_errors_map_to_local_file_lines(fixture_text):
    s = listing.parse_listing(fixture_text("compile_errors.lst"))
    assert s.error_count == 4
    codes = [e.code for e in s.compile_errors]
    assert codes == [140, 140, 149, 257]
    first = s.compile_errors[0]
    assert first.file == "/work/dispatch/main.gms"
    assert first.line == 9  # local line, even though the echo print says 12 (include before it)
    assert first.listing_line == 12
    assert first.message == "Unknown symbol"
    assert first.column and first.column > 30
    assert s.compile_errors[2].message == "Uncontrolled set entered as constant"
    assert [r["type"] for r in s.include_files] == ["INPUT", "INCLUDE"]


def test_solve_summary_optimal(fixture_text):
    s = listing.parse_listing(fixture_text("lp_ok.lst"))
    assert len(s.solves) == 1
    sv = s.solves[0]
    assert (sv.model, sv.type, sv.direction, sv.solver, sv.from_line) == ("m", "LP", "MINIMIZE", "CPLEX", 18)
    assert (sv.solver_status, sv.model_status) == (1, 1)
    assert sv.objective_value == 13300.0
    assert sv.usable


def test_conflict_refiner_output(fixture_text):
    s = listing.parse_listing(fixture_text("lp_conflict.lst"))
    sv = s.solves[0]
    assert sv.model_status == 19 and not sv.usable
    assert s.conflicts and len(s.conflicts[0].equations) == 4
    assert s.conflicts[0].equations[0] == {"kind": "fixed", "name": "bal(t3)", "detail": "= 300"}


def test_exec_error(fixture_text):
    s = listing.parse_listing(fixture_text("exec_error.lst"))
    assert s.exec_errors and s.exec_errors[0].message == "division by zero (0)"
    assert s.exec_errors[0].listing_line == 3


def test_lp_log(fixture_text):
    log = cplexlog.parse_log(fixture_text("lp_ok.log"))
    assert log.gams_version == "54.6.1"
    assert log.status == "Normal completion"
    assert log.models[0]["rows"] == 17 and log.models[0]["columns"] == 13 and log.models[0]["nonzeros"] == 37
    assert log.models[0]["ranges"]["matrix"]["max"] == 50.0
    assert log.solver == "CPLEX" and log.solver_version == "22.2.0.0"
    assert log.options_set["iis"] == "1"
    assert log.options_deprecated == ["mipgap"]
    assert log.options_ignored[0]["text"] == "bogusopt 5"
    assert log.statuses[0] == {"kind": "LP", "code": 1, "text": "optimal"}
    assert log.demo_license


def test_mip_node_log(fixture_text):
    log = cplexlog.parse_log(fixture_text("mip_node_log.log"))
    assert log.root_bound == 344011.5149
    assert log.mip_solution == 351729.984984 and log.nodes == 836
    assert log.relative_gap == 0.0
    assert any(i.objective == 352399.985 for i in log.incumbents)
    assert log.statuses[-1]["code"] == 101
    assert log.models[0]["discrete_columns"] > 0


def test_mip_integer_infeasible(fixture_text):
    log = cplexlog.parse_log(fixture_text("mip_integer_infeasible.log"))
    assert log.statuses[-1]["code"] == 103
    assert any("1217" in e for e in log.errors)


def test_compile_log_errors_carry_location(fixture_text):
    log = cplexlog.parse_log(fixture_text("compile_errors.log"))
    assert log.status == "Compilation error(s)"
    assert log.errors[0].startswith("GAMS Error 140") and "main.gms line 9" in log.errors[0]


def test_numerics_flags():
    log = cplexlog.LogSummary(models=[{"name": "uc", "ranges": {"matrix": {"min": 1e-3, "max": 1e7, "orders_of_magnitude": 10.0}}}])
    flags = cplexlog.numerics_flags(log)
    assert any("orders of magnitude" in f for f in flags) and any("big-M" in f for f in flags)


def test_reffile(fixture_text):
    syms = reffile.parse_reffile(fixture_text("lp_ok.ref"))
    assert syms["cap"].dim == 1 and syms["cap"].text == "capacity MW"
    assert syms["cap"].first("declared").file.endswith("data.inc")
    findings = reffile.analyze(syms)
    assert {"symbol": "load", "type": "PARAMETERS", "file": "/work/dispatch/main.gms", "line": 5} in findings[
        "missing_explanatory_text"
    ]
    assert "equation_not_in_solved_model" not in findings
    x = reffile.xref(syms, "bal")
    assert "defined" in x["references"] and "impl-asn" in x["references"]


def test_optdef_parse_and_validate(fixture_text):
    defs = optdef.parse_optdef(fixture_text("optcplex_53_excerpt.def"), "cplex")
    assert defs.options["solvefinal"].default == "1"  # GAMS 53: MIP marginals by default
    assert defs.options["epgap"].min == 0.0 and defs.options["epgap"].max == 1.0
    assert defs.options["lpmethod"].values["2"] == "Dual Simplex"
    assert defs.lookup("mipgap")[1] == "epgap"
    assert "mipgap" in defs.deprecated
    assert defs.eol_comment == "!"

    text = "\n".join(
        [
            "* comment",
            "lpmethod 2",
            "lpmethod 9",
            "threads 4 ! inline comment",
            "mipgap 0.01",
            "reslim 100",
            "epgap 2",
            "bogusopt 5",
            "x.feaspref 2",
            "usebasis 1",
            "iis=1",
            "indic bal(t)$u(t) 1",
            "cuts 7",
        ]
    )
    res = {c.text: c for c in optdef.validate_option_text(text, defs)}
    assert res["lpmethod 2"].status == "ok"
    assert res["lpmethod 9"].status == "error"
    assert res["threads 4 ! inline comment"].status == "ok"
    assert res["mipgap 0.01"].status == "warning" and res["mipgap 0.01"].canonical == "epgap"
    assert res["reslim 100"].canonical == "tilim" and res["reslim 100"].status == "ok"
    assert res["epgap 2"].status == "error"
    assert res["bogusopt 5"].status == "error"
    assert res["x.feaspref 2"].status == "ok" and res["x.feaspref 2"].canonical == ".feaspref"
    assert res["usebasis 1"].status == "warning"
    assert res["iis=1"].status == "ok"
    assert res["indic bal(t)$u(t) 1"].status == "ok"
    assert res["cuts 7"].status == "error"


def test_error_catalog(fixture_text):
    cat = errors.parse_errors(fixture_text("gamserrs_excerpt.txt"))
    assert cat[149] == "Uncontrolled set entered as constant"
    assert cat[141].startswith("Symbol declared but no values have been assigned")
    assert "$onImplicitAssign" in cat[141]
    assert errors.lookup(542, cat)["hint"].startswith("Blocked by execMode")


def test_gdx_parsing_and_compare():
    syms = gdx.parse_symbols(
        "  Symbol Dim Type Records  Explanatory text\n1 e        1  Equ       3  \n4 s        0  Par       1  a scalar\n"
    )
    assert syms[1].name == "s" and syms[1].text == "a scalar"
    par = gdx.SymbolInfo("q", 1, "Par", 3)
    a = gdx.parse_symbol_csv('"i","Val"\n"a",Eps\n"b",NA\n"c",+Inf\n', par)
    assert a.rows[("a",)]["Val"] == 0.0 and ("a",) in a.eps_keys
    assert math.isnan(a.rows[("b",)]["Val"]) and a.rows[("c",)]["Val"] == math.inf
    b = gdx.parse_symbol_csv('"i","Val"\n"b",NA\n"c",+Inf\n', par)
    assert gdx.compare_symbol(a, b, 1e-6, 1e-6)["status"] == "equal"  # Eps vs missing both count as zero

    var = gdx.SymbolInfo("p", 1, "Var", 2)
    va = gdx.parse_symbol_csv('"g","Val","Marginal","Lower","Upper","Scale"\n"g1",100,0,0,+Inf,1\n"g2",50,-2,0,+Inf,1\n', var)
    vb = gdx.parse_symbol_csv('"g","Val","Marginal","Lower","Upper","Scale"\n"g1",100.00001,0,0,+Inf,1\n"g2",60,-2,0,+Inf,1\n', var)
    cmp = gdx.compare_symbol(va, vb, rel=1e-6, abs_=1e-3)
    assert cmp["status"] == "different" and cmp["differing_values"] == 1
    assert cmp["largest"][0]["key"] == ["g2"] and cmp["largest"][0]["abs_diff"] == 10.0
