import json

import pytest

from gams_tools import hooks
from gams_tools.config import ConfigError, parse_config
from gams_tools.gams import build_command, version_matches


def test_limits_are_capped(repo):
    base = repo.test_case("dispatch-base")
    assert base.limits.reslim == 30
    assert base.limits.threads == 2  # capped by limits.threads
    assert repo.test_case("dispatch-peak").defines == {"peak": "300"}


def test_unknown_entry_and_case_are_refused(repo):
    with pytest.raises(ConfigError):
        repo.entry("models/other.gms")
    with pytest.raises(ConfigError):
        repo.test_case("prod-run")


def test_paths_outside_repo_or_protected_are_refused(repo):
    with pytest.raises(ConfigError):
        repo.resolve("../outside.gms")
    with pytest.raises(ConfigError):
        repo.resolve("data/prod/secret.gdx")
    assert repo.resolve("models/dispatch/main.gms").is_file()


def test_config_validation(tmp_path):
    with pytest.raises(ConfigError, match="gams.version"):
        parse_config({}, tmp_path)
    with pytest.raises(ConfigError, match="not listed in entry_points"):
        parse_config({"gams": {"version": "53"}, "test_cases": [{"name": "x", "entry": "a.gms"}]}, tmp_path)
    with pytest.raises(ConfigError, match="exec_mode"):
        parse_config({"gams": {"version": "53", "exec_mode": 9}}, tmp_path)


def test_version_matching():
    assert version_matches("53", "53.5.1")
    assert version_matches("53.5", "53.5.1")
    assert not version_matches("53", "54.6.1")
    assert not version_matches("53.5.1", "53.5.0")
    assert not version_matches("53", None)


def test_build_command_guards(tmp_path):
    from pathlib import Path

    from gams_tools.config import Limits

    cmd = build_command(
        Path("/opt/gams/gams"), Path("/r/m.gms"), tmp_path, action=None, defines={"peak": "300"},
        exec_mode=2, limits=Limits(reslim=30, threads=2), gdx=True, ref=False,
    )
    assert "execMode=2" in cmd and "resLim=30" in cmd and "threads=2" in cmd and "--peak=300" in cmd
    with pytest.raises(ConfigError):
        build_command(Path("g"), Path("m"), tmp_path, action="c", defines={"bad key": "1"}, exec_mode=2, limits=None, gdx=False, ref=False)


def _pre(repo, tool, args):
    return hooks.pre_tool_use(repo, {"tool_name": tool, "tool_input": args})


def test_pre_tool_use_blocks_raw_gams_and_protected_paths(repo):
    code, out, err = _pre(repo, "run_in_terminal", {"command": "cd models && gams main.gms lo=3"})
    assert code == 2 and "gams-tools" in err and json.loads(out)["permissionDecision"] == "deny"
    assert _pre(repo, "run_in_terminal", {"command": "gams-tools compile models/dispatch/main.gms"})[0] == 0
    assert _pre(repo, "run_in_terminal", {"command": "python make_gams_report.py"})[0] == 0
    assert _pre(repo, "read_file", {"filePath": "data/prod/secret.gdx"})[0] == 2
    assert _pre(repo, "run_in_terminal", {"command": "cat data/prod/secret.gdx"})[0] == 2
    assert _pre(repo, "read_file", {"filePath": "models/dispatch/main.gms"})[0] == 0


def test_pre_tool_use_copilot_cli_payload_shape(repo):
    payload = {"toolName": "bash", "toolArgs": json.dumps({"command": "gams main.gms"})}
    assert hooks.pre_tool_use(repo, payload)[0] == 2


def test_pre_tool_use_blocks_atlassian_writes_only(repo):
    assert _pre(repo, "atlassian/createJiraIssue", {})[0] == 2
    assert _pre(repo, "mcp_atlassian_addCommentToJiraIssue", {})[0] == 2
    assert _pre(repo, "atlassian/transitionJiraIssue", {})[0] == 2
    assert _pre(repo, "atlassian/getJiraIssue", {})[0] == 0
    assert _pre(repo, "atlassian/searchConfluenceUsingCql", {})[0] == 0
    assert _pre(repo, "atlassian/getConfluencePageFooterComments", {})[0] == 0


def test_post_tool_use_ignores_non_gams_edits(repo):
    code, out, err = hooks.post_tool_use(repo, {"tool_name": "edit", "tool_input": {"filePath": "README.md"}})
    assert (code, out, err) == (0, "", "")
