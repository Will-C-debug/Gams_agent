# gams-sme customization pack

These files turn GitHub Copilot into the GAMS/CPLEX subject-matter expert described in [PLAN.md](../PLAN.md). The `sync-pack` workflow copies `pack/.github/` and `pack/.vscode/` into each GAMS repository. Copilot reads them in VS Code, in the cloud agent and in code review.

| Path | What it is | Used by |
|---|---|---|
| `.github/copilot-instructions.md` | Repo-wide principles; kept under ~4,000 characters for code review | All Copilot surfaces |
| `.github/instructions/*.instructions.md` | Path-specific rules for `.gms/.inc`, option files and tests | All Copilot surfaces |
| `.github/skills/*/SKILL.md` | Deep knowledge, loaded on demand: GAMS 53 language, CPLEX, review procedure, internal standards, power-scheduling domain, testing, formulation docs, Jira/Confluence | VS Code, cloud agent, CLI, code review |
| `.github/agents/*.agent.md` | Five custom agents with tool allowlists and handoffs | VS Code, cloud agent, CLI |
| `.github/prompts/*.prompt.md` | Slash commands: `/gams-review`, `/gams-implement`, `/gams-explain`, `/gams-diagnose`, `/cplex-tune`, `/gams-test`, `/gams-doc`, `/gams-feedback` | VS Code chat |
| `.github/hooks/gams-sme.json` | Compile check after edits, guardrails before tool calls, version check at session start (preview feature) | VS Code, cloud agent, CLI |
| `.github/gams-agent.schema.json` | JSON schema for `.gams-agent.yaml` (editor validation) | VS Code YAML extension |
| `.vscode/mcp.json` | MCP servers: `gams-tools` (local) and the Atlassian Rovo MCP server | VS Code |
| `.vscode/tasks.json` | "GAMS: compile all entry points" with a problem matcher; "GAMS: run checks" | VS Code |

## Prerequisites in each GAMS repository

1. **GAMS 53.** Installed locally, licensed, on `PATH` or set through `GAMS_SYSDIR`.
2. **gams-tools.** Install it (see [mcp/gams-tools](../mcp/gams-tools/README.md)) so that the `gams-tools` command is on `PATH`.
3. **Config.** A `.gams-agent.yaml` at the repository root; start from [templates/gams-agent.yaml](../templates/gams-agent.yaml).
4. **gitignore.** Add `.gams-agent/` to `.gitignore`.
5. **Org policies on.** MCP servers, custom agents, skills, prompt files and hooks; MCP restricted to `gams-tools` and Atlassian.

## Things to verify at build time

Copilot customization is moving quickly. Check these against the current docs when you first roll out, and when VS Code or Copilot release notes mention changes:

- **Tool identifiers in agent frontmatter.**
  - Built-in tool aliases: `read`, `search`, `edit`, `execute`, `todo`.
  - MCP tools: `gams-tools/*` and `atlassian/<tool>`.
  - Unknown tool names are ignored, so a renamed tool silently disappears from an agent.
- **Atlassian MCP tool names.** Check them against the server's tool list in VS Code. The PreToolUse hook blocks Atlassian write tools by name pattern, so even a mismatch can't enable writes.
- **Hook file format.** VS Code agent hooks are in preview. `gams-sme.json` includes both the VS Code field names (`command`, `timeout`) and the Copilot CLI/cloud agent field names (`bash`, `powershell`, `timeoutSec`).
- **Atlassian MCP endpoint.** Check the URL in `.vscode/mcp.json` against Atlassian's current getting-started page.
- **Model.** The agents don't pin a model. If the org standardizes on one, add `model:` to each agent's frontmatter.

`scripts/validate_pack.py` checks the structural rules (frontmatter, skill names, link targets, instruction length, JSON validity) in CI.
