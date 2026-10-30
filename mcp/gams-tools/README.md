# gams-tools

Guarded, structured access to GAMS and CPLEX for the `gams-sme` Copilot agent. One Python package provides:

- **an MCP server** (`gams-tools mcp`) that VS Code agent mode, the Copilot cloud agent and Copilot CLI call
- **a CLI** (`gams-tools compile|run|...`), which the agent hooks, CI (`gams-tools check`) and the evals use

So the checks behave the same everywhere.

Everything is driven by the repository's `.gams-agent.yaml`; see the [template](../../templates/gams-agent.yaml).

## Install

```bash
pip install "gams-tools[mcp] @ git+https://github.com/Will-C-debug/Gams_agent#subdirectory=mcp/gams-tools"
```

The package needs a GAMS installation; its own Python dependencies are only PyYAML and, for the server, `mcp`. It finds GAMS in this order:

1. `gams.sysdir` in `.gams-agent.yaml`
2. the `GAMS_SYSDIR` environment variable
3. `gams` on `PATH`

## Tools

| MCP tool / CLI command | What it does |
|---|---|
| `gams_environment` / `env` | Installed vs. pinned GAMS version, exec mode, entry points, allowlisted test cases |
| `gams_compile` / `compile` | Compile an entry point (`action=c`) and return structured errors with file and *local* line, also inside include files |
| `gams_run` / `run` | Run an **allowlisted** test case and return solve statuses, objective, execution errors, conflict set, CPLEX log digest, numerics flags and baseline GDX differences |
| `listing_summary` / `listing` | Summarize a `.lst` file |
| `log_summary` / `log` | Summarize a GAMS/CPLEX log: model size, coefficient ranges, option-file handling, statuses, MIP progress, conflict |
| `gdx_inspect` / `gdx-inspect` | List symbols or sample one symbol (uses `gdxdump`) |
| `gdx_diff` / `gdx-diff` | Compare two GDX files with tolerances |
| `symbol_xref` / `xref` | Unused symbols, parameters used but never assigned, equations not in any solved model, symbols without explanatory text, where-used for one symbol |
| `option_validate` / `validate-options` | Validate an option file against `opt<solver>.def` of the installed release |
| `option_info` / `option-info` | Type, default, range, allowed values and deprecation of one option |
| `error_lookup` / `error` | Explain a GAMS error code from the installed `gamserrs.txt` |
| `docs_search` / `docs` | Keyword search over the documentation folders in `docs.dirs` |
| `check` (CLI only) | CI gate. Runs the environment check, then compiles, validates option files, runs regression cases and compares baselines. Prints Markdown (also written to `$GITHUB_STEP_SUMMARY`) and exits non-zero on failure. |
| `hook <event>` (CLI only) | Agent hook handlers: `session-start`, `pre-tool-use`, `post-tool-use` |

## Guardrails

- **Shell escapes blocked.** Every GAMS run uses `execMode` from `gams.exec_mode` (default `2`), which blocks `$call`, `execute` and embedded code. A blocked statement shows up as error 542.
- **Limits enforced by the tool.** `resLim`, `threads` and a hard wall-clock kill come from `limits`, and each test case's limits are capped by the global ones.
- **Only configured models run.** Only entry points and test cases listed in `.gams-agent.yaml` can be compiled or run.
- **Paths are confined.** Paths must stay inside the repository and outside `protected_paths`.
- **Outputs are contained.** GAMS writes only into `.gams-agent/runs/` (add `.gams-agent/` to `.gitignore`).
- **Every call is audited.** Each call is appended to `.gams-agent/audit.jsonl`.
- **Results stay compact.** Output is trimmed to `limits.max_output_chars` so the agent gets compact results.

## Development

```bash
pip install -e ".[mcp,test]"
pytest                                   # parser/config/hook tests use captured GAMS output
GAMS_SYSDIR=/path/to/gams53 pytest       # also runs the integration tests against real GAMS
```

The fixtures in `tests/fixtures/` are real GAMS/CPLEX output, with paths replaced:

- **Listings and logs:** produced by the GAMS 54.6.1 demo license. The demo license bundled with 53.5.1 has expired, and the listing and log formats are the same.
- **Option-definition and error-catalog excerpts:** taken from GAMS 53.5.1.

Regenerate the listings and logs with your licensed GAMS 53 build during Phase 0.
