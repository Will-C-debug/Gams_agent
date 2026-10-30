# Gams_agent

A subject-matter-expert agent for GAMS and CPLEX, built on GitHub Copilot in VS Code and targeting GAMS 53, with Jira and Confluence as context sources. It helps SMEs and code developers review and write the GAMS models we use internally.

- **Design and roadmap:** [PLAN.md](PLAN.md). Implementation status is in §16.
- **Next actions for admins and SMEs:** [docs/phase0-checklist.md](docs/phase0-checklist.md).

## What's in this repository

| Path | What it is |
|---|---|
| [`pack/`](pack/README.md) | The Copilot customization pack synced into GAMS repositories: instructions, skills, custom agents, prompt files, hooks, VS Code MCP/tasks config |
| [`mcp/gams-tools/`](mcp/gams-tools/README.md) | Python package: MCP server and CLI that compile, run allowlisted cases, analyze listings/logs/GDX, and validate CPLEX options against the installed GAMS release, with guardrails |
| `templates/` | Starting points for GAMS repositories: `.gams-agent.yaml`, the `gams-checks` caller workflow, `copilot-setup-steps.yml`, cloud-agent MCP config |
| `.github/` | CI for this repository, the reusable `gams-checks` workflow, the `setup-gams` action, pack sync and eval workflows |
| [`evals/`](evals/README.md) | Eval harness: unit commitment base model, 12 verified seeded defects, knowledge Q&A, Jira/Confluence context tasks, graders, runner |
| `sync/` | Pack sync to GAMS repositories, and the Confluence standards snapshot |
| `sandbox/` | Container image with pinned GAMS and gams-tools for CI and evals |
| `scripts/validate_pack.py` | Structural checks for the pack, run in CI |

## Try it locally

```bash
pip install -e "mcp/gams-tools[mcp,test]"
pytest mcp/gams-tools evals/tests                         # no GAMS needed
python scripts/validate_pack.py

# With a licensed GAMS 53 installation:
export GAMS_SYSDIR=/path/to/gams53
cd evals/models/uc_small && gams-tools check               # compile, option check, regression case
```

To use the agent in a GAMS repository:

1. Copy `pack/.github` and `pack/.vscode` into it (or let `sync-pack` open the PR).
2. Add a `.gams-agent.yaml` from `templates/`.
3. Install `gams-tools`.
4. Open the repository in VS Code and run `/gams-review` in Copilot Chat.
