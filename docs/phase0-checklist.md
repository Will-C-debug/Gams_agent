# Phase 0 checklist

These are the actions that need people with admin rights or SME knowledge before the pilot. Each item points back to [PLAN.md](../PLAN.md).

## GitHub / Copilot admin

- [ ] **Turn on the Copilot features the pack uses for the pilot repositories** (plan §4 C3, §7):
  - custom agents, agent skills, prompt files
  - agent hooks (preview)
  - MCP servers, restricted to `gams-tools` and the Atlassian Rovo MCP server
- [ ] **Turn on Copilot code review.** Add a ruleset that requests it automatically on GAMS PRs (plan §7.9).
- [ ] **Turn on the Copilot cloud agent** for the pilot repositories only (Phase 5).
- [ ] **Create the organization secret `GAMS_LICENSE`.** It holds the full GAMS license; GAMS 51+ requires the 8-line format. Scope it to the pilot repositories and to this repository.
- [ ] **Create the variable `GAMS_INSTALLER_URL`.** Point it at an internal mirror of the GAMS **53.5.1** Linux installer (`linux_x64_64_sfx.exe`). Without it, the workflows fall back to the GAMS system in the `gamspy-base` wheel. **Confirm with your GAMS license terms that this fallback is acceptable.**
- [ ] **Make this repository's reusable workflow and setup action usable from the GAMS repositories.**
  - Move `Gams_agent` into the organization, or
  - Set Settings → Actions → General → Access to allow it.
- [ ] **Create `PACK_SYNC_TOKEN`.** Use a GitHub App or a fine-grained token with contents and pull-request write access to the target repositories only. List the targets in `sync/targets.yaml`.

## Atlassian admin

- [ ] **Production read-only service account.**
  - Browse and read only.
  - Jira projects **GO, UC, IHP1, INTRA1, CES**.
  - Confluence spaces **DT, STD, AH, AVR**.
  - Add FOT only after the decision on customer data (Q16).
- [ ] **Eval service account.** Read-only, on a new **sandbox** Jira project and Confluence space.
- [ ] **Enable API-token authentication for the Rovo MCP server,** for the service accounts only. Confirm the endpoint and header format used in `templates/copilot-cloud-agent-mcp.json` and `pack/.vscode/mcp.json`.
- [ ] **Create the sandbox project and space,** and load `evals/context_tasks/ctx-001` (issue + spec page).
- [ ] **Store the service-account tokens as GitHub secrets.**
  - Production: the pilot repositories' `copilot` environment, and their repository MCP settings for code review.
  - Eval: this repository.
- [ ] **Agree a rotation schedule and owner** for the tokens.

## SME council

- [ ] **Confirm the domain reading** (power-system scheduling, Avalon modules), and fill in the model catalog in `pack/.github/skills/org-gams-standards/SKILL.md` (Q15).
- [ ] **Decide whether FOT customer/site pages may be read** by the service account and Copilot (Q16).
- [ ] **GAMS coding standard.** Decide whether one exists. If not, draft one in Confluence **STD**, then snapshot it with `sync/confluence_snapshot.py` (Q12).
- [ ] **Validate the checklists and seeded defects.** Review the review checklist (`pack/.github/skills/gams-review/references/checklist.md`), the domain items (`power-scheduling-domain/references/checklist.md`) and the seeded defects (`evals/seeded_defects/uc_small.yaml`).
- [ ] **Agree on Jira conventions** (§8.3): the `gams` label, Jira keys in branch names, and acceptance criteria in GAMS issues. Back-label past issues found by a broader Rovo search.
- [ ] **Set the pilot → GA thresholds** and name metric owners (Q14).

## Engineering lead

- [ ] **Confirm the exact production build.** 53.5.1 bundles CPLEX 22.1.2. Find out whether anyone runs another release (Q1).
- [ ] **Inventory developer machines.** OS, local GAMS 53 install, Docker/WSL (Q10). Install `gams-tools` for pilot users (`mcp/gams-tools/README.md`).
- [ ] **Data:** confirm the data classification (Q9), and pick or create small test datasets (Q13).
- [ ] **Verify on licensed GAMS 53:**
  - [ ] `GAMS_SYSDIR=<gams53> GAMS_TOOLS_TEST_VERSION=53 pytest mcp/gams-tools`
  - [ ] `GAMS_SYSDIR=<gams53> python evals/runner/verify_seeds.py`, then commit the regenerated `effects.json`
  - [ ] Regenerate the listing/log fixtures in `mcp/gams-tools/tests/fixtures/` from GAMS 53 runs
- [ ] **Verify the Copilot specifics** that couldn't be tested here (plan §16):
  - [ ] Agents load in VS Code. The built-in tool aliases (`read`, `search`, `edit`, `execute`, `todo`) and the `gams-tools/*` and `atlassian/*` tools appear in each agent's tool list.
  - [ ] Atlassian tool names in agent frontmatter match the server's tool list.
  - [ ] The hook file `pack/.github/hooks/gams-sme.json` is picked up. An edit to a `.gms` file triggers the compile check; a raw `gams` terminal command is blocked.
  - [ ] Copilot CLI flags for non-interactive runs, for `evals/runner/run_evals.py --agent-cmd`.
- [ ] **Dry run.**
  1. Prepare eval workspaces: `python evals/runner/run_evals.py --set seeded --out evals/results/dry-run`.
  2. Open two of them in VS Code, run `/gams-review`, and save the answers as `<case>.md`.
  3. Grade them with `evals/runner/grade_review.py`.
- [ ] **Pick the 1–2 pilot repositories.** Add their `.gams-agent.yaml` (from `templates/`), their entry points and test cases, the `gams-checks` caller workflow, and `copilot-setup-steps.yml`.
