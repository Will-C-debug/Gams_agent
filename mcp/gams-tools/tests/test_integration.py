"""End-to-end tests that call a real GAMS installation (skipped without one)."""

import json
import shutil

from conftest import requires_gams

from gams_tools import check, hooks, service

pytestmark = requires_gams


def test_environment_reports_installed_version(repo):
    env = service.environment(repo)
    assert env["installed_gams_version"] and env["installed_gams_version"].count(".") == 2


def test_compile_ok_and_errors(repo):
    res = service.compile_entry(repo, "models/dispatch/main.gms")
    assert res["ok"], res
    inc = repo.root / "models/dispatch/inc/data.inc"
    inc.write_text(inc.read_text() + "Parameter broken(g) 'oops' / g1 x(g) /;\n")
    res = service.compile_entry(repo, "models/dispatch/main.gms")
    assert not res["ok"] and res["errors"]
    assert res["errors"][0]["file"] == "models/dispatch/inc/data.inc"
    assert res["errors"][0]["line"] == 4
    assert res["errors"][0]["included_from"] == ["models/dispatch/main.gms:4"]


def test_exec_mode_blocks_call(repo):
    main = repo.root / "models/dispatch/main.gms"
    main.write_text("$call echo hi\n" + main.read_text())
    res = service.compile_entry(repo, "models/dispatch/main.gms")
    assert not res["ok"] and res["errors"][0]["code"] == 542


def test_run_case_and_conflict(repo):
    ok = service.run_case(repo, "dispatch-base")
    assert ok["ok"], ok
    assert ok["solves"][0]["model_status"] == 1 and ok["solves"][0]["objective_value"] == 13300.0
    (repo.root / "models/dispatch/cplex.opt").write_text("iis 1\n")
    bad = service.run_case(repo, "dispatch-peak")
    assert not bad["ok"] and bad["unusable_solves"] == ["m"]
    assert bad["solver"]["conflict"]["equations"][0]["name"] == "bal(t3)"


def test_baseline_diff(repo):
    first = service.run_case(repo, "dispatch-base")
    base = repo.root / "tests" / "baseline.gdx"
    base.parent.mkdir(exist_ok=True)
    shutil.copy(repo.root / first["gdx"], base)
    tc = repo.test_case("dispatch-peak")
    tc.baseline_gdx = "tests/baseline.gdx"
    tc.defines = {"peak": "210"}
    res = service.run_case(repo, "dispatch-peak")
    assert res["baseline"]["equal"] is False
    changed = {s["symbol"] for s in res["baseline"]["symbols"]}
    assert {"load", "p", "z"} <= changed


def test_xref_and_options(repo):
    res = service.symbol_xref(repo, "models/dispatch/main.gms", "cap")
    assert res["ok"] and res["xref"]["references"]["declared"][0].startswith("models/dispatch/inc/data.inc")
    (repo.root / "models/dispatch/cplex.opt").write_text("lpmethod 2\nmipgap 0.01\nnotanoption 1\n")
    opts = service.option_validate(repo, path="models/dispatch/cplex.opt")
    statuses = [ln["status"] for ln in opts["lines"]]
    assert statuses == ["ok", "warning", "error"] and not opts["ok"]
    info = service.option_info(repo, "solvefinal")
    assert info["ok"] and info["type"] == "boolean"


def test_post_tool_use_hook_reports_compile_errors(repo):
    main = repo.root / "models/dispatch/main.gms"
    main.write_text(main.read_text().replace("=l= cap(g)", "=l= capp(g)"))
    code, out, err = hooks.post_tool_use(repo, {"tool_name": "edit", "tool_input": {"filePath": str(main)}})
    assert code == 2 and "error 140" in err


def test_check_report(repo):
    report = check.run_checks(repo)
    md = check.to_markdown(report)
    assert "### Compile" in md and "dispatch-base" in md
    json.dumps(report, default=str)
    assert any(t["case"] == "dispatch-peak" and not t["ok"] for t in report["tests"])
