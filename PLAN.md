# CPLEX & GAMS Subject-Matter-Expert Agent: Plan

| | |
|---|---|
| **Status** | Draft for review |
| **Date** | 2026-10-30 |
| **Audience** | Optimization SMEs, GAMS developers, engineering leads, security/IT reviewers |
| **Owner** | _TBD_ |

---

## 1. Summary

We will build **`gams-sme`**, an AI assistant that acts as a GAMS and CPLEX subject-matter expert inside the tools our modelers and developers already use. It will:

- review GAMS code and formulations
- write and refactor GAMS code to our standards
- diagnose failed, infeasible and slow solves
- explain models and solver behavior

Recommended shape:

1. **A Claude Code plugin.** It packages the expertise as skills (knowledge), subagents (reviewer roles), slash commands (repeatable workflows) and hooks (automatic compile checks and guardrails). We distribute it through an internal plugin marketplace hosted in this repository.
2. **A `gams-tools` MCP server.** It gives the agent safe, structured access to a real GAMS/CPLEX installation: compile, sandboxed runs, listing-file and GDX analysis, and CPLEX option validation. This way its answers are checked against the toolchain, not recalled from memory.
3. **CI review of pull requests.** Every PR that touches GAMS code first runs deterministic GAMS checks, then gets an agent review. Humans remain the approvers.
4. **An evaluation harness.** It holds seeded defects, historical PRs, and coding and diagnosis tasks. Every change to the agent must pass it, and it tracks quality over time.

We will deliver in phases over roughly **14–18 weeks to general availability**: discovery → MVP (knowledge + local review) → tooling → CI review in shadow mode → pilot → GA.

**The most important design principle:** the agent must back every claim with evidence it can show, and must say how it verified each finding. Evidence means a `file:line`, compiler or solver output, a validated option definition, or a cited doc section.

---

## 2. Goals and non-goals

### Goals

| # | Goal |
|---|---|
| G1 | Faster, more consistent reviews of GAMS changes, covering formulation, data handling, solver configuration, performance and code quality. |
| G2 | Better GAMS code from developers: it compiles first time, follows internal conventions, and comes with regression tests. |
| G3 | Faster diagnosis of compile and execution errors, infeasible or unbounded models, numerical trouble and slow MIP solves with CPLEX. |
| G4 | Capture our modeling knowledge (standards, pitfalls, lessons learned) and apply it the same way every time. |
| G5 | Make models easier to understand: explain legacy code, generate math documentation, and trace spec ↔ code. |

### Non-goals (v1)

- **Replacing human approval.** The agent never approves or merges. SMEs own modeling decisions.
- **Production use.** The agent never runs against production data or production schedules.
- **Autonomous tuning in production.** The agent recommends; humans apply.
- **Standalone CPLEX development.** OPL, docplex and the C/C++/Java/Python CPLEX APIs are a v2 candidate, depending on open question Q2.
- **A custom chat portal.** We revisit this only if users outside Claude Code need one (see §5.3).

---

## 3. Users and core use cases

| Persona | Typical request | What "good" looks like |
|---|---|---|
| **SME** (OR modeler / domain expert) | "Does this PR implement the formulation in spec X?" | A table that maps each spec equation to its GAMS equation, in math notation, with every difference tied to a `file:line`. |
| | "Why is scenario Y infeasible?" | The conflict set from the CPLEX conflict refiner / IIS, mapped back to GAMS equation names, index tuples and the input data behind them, plus candidate fixes. |
| | "Why did solve time triple after this change?" | A comparison of the before/after logs, the formulation or data change that caused the slowdown, and ranked option or formulation suggestions with evidence. |
| | "Explain what this legacy model does." | A structured walkthrough of sets, data flow, decision variables, constraints, objective and outputs. |
| | "Are these CPLEX settings sensible?" | An option-by-option review, checked against the installed option definitions, with a rationale for each non-default. |
| **Developer** | "Implement ramp-rate constraints per the spec." | A minimal diff that follows our conventions and compiles, with a new regression test that passes. |
| | "Fix this compilation / execution error." | The root cause explained, and the fix confirmed by recompiling or rerunning. |
| | "Refactor this include structure / move data I/O to GAMS Connect." | A change that keeps behavior the same, proven by a GDX diff on baseline datasets. |
| | "Write regression tests for this model." | Small datasets, golden outputs, and a tolerance-based comparison wired into CI. |
| | "Review my branch before I open a PR." | The same review contract as CI (§6.2), run locally. |
| **Both** | Questions on GAMS semantics or CPLEX behavior | Answers with doc citations and caveats where behavior depends on the release. |

---

## 4. Key assumptions

We will confirm these in Phase 0. Each maps to an open question in §14.

| # | Assumption |
|---|---|
| A1 | GAMS code lives in Git repositories on GitHub, and CI runs on GitHub Actions. |
| A2 | CPLEX is used mainly as a GAMS solver (GAMS/CPLEX), configured through option files. |
| A3 | Users can be licensed for Claude Code, through the terminal, IDE extension, desktop app or web. |
| A4 | We can provision a GAMS installation with a CPLEX license for a sandbox / CI environment. |
| A5 | We can create representative small datasets that are approved for use with the agent. |

---

## 5. Solution architecture

### 5.1 Recommendation and rationale

Build the agent as a **Claude Code plugin plus a GAMS tools MCP server**:

- **The hard parts already exist.** Claude Code provides repository search, file reading and editing, shell, git, permissions, subagents, and terminal / IDE / desktop / web front ends. We only add the GAMS/CPLEX expertise and tools.
- **Skills load only when needed.** A skill's detailed content loads only when relevant, so we can ship deep GAMS/CPLEX reference material without bloating every conversation.
- **Hooks enforce behavior.** For example, every edit to a `.gms` file triggers a compile check, whether or not the model "remembers" to do it.
- **Local and CI reviews match.** The same plugin runs on a laptop and in CI, so a local "review my branch" and the PR review apply the same checklist and output contract.
- **The MCP server is reusable.** Other clients can use it too: the Claude desktop app for SME Q&A, or a future custom service.

```
   Users:  SMEs (review, diagnosis, explanation)     Developers (coding, tests, fixes)
              |                                                  |
              | Claude Code (terminal / IDE / desktop / web)     | GitHub pull requests
              v                                                  v
   +----------------------------------+        +--------------------------------------+
   | gams-sme plugin                  |        | CI                                   |
   |  - skills     (knowledge)        |<-same--|  1. gams-checks (compile, regression,  |
   |  - subagents  (review roles)     | plugin |     GDX diff vs. baseline)           |
   |  - commands   (workflows)        |        |  2. agent review (read-only tools)   |
   |  - hooks      (compile check,    |        +--------------------------------------+
   |               guardrails)        |
   +----------------+-----------------+
                    | MCP
                    v
   +----------------------------------+     +-----------------------------------------+
   | gams-tools MCP server            |---->| Sandbox: pinned GAMS + CPLEX, no network,|
   |  compile / run / listing / GDX / |     | CPU/memory/time limits, allowlisted data |
   |  xref / options / errors / docs  |---->| Version-pinned docs index + internal docs|
   +----------------------------------+     +-----------------------------------------+
```

### 5.2 Components

| Component | Purpose | Location |
|---|---|---|
| `gams-sme` plugin | Skills, subagents, commands, hooks, MCP config | `plugins/gams-sme/` in this repo |
| Internal plugin marketplace | One-command install and update for users | `.claude-plugin/marketplace.json` in this repo |
| `gams-tools` MCP server | Structured, sandboxed access to GAMS/CPLEX | `mcp/gams-tools/` in this repo |
| Sandbox image | Pinned GAMS release and CPLEX, used locally and in CI | `sandbox/` (Dockerfile); license mounted at runtime |
| Per-repo config | Entry points, test cases, protected paths, GAMS version | `CLAUDE.md` + `.gams-agent.yaml` in each GAMS repo |
| CI workflows | Deterministic checks + agent PR review | Reusable workflow in this repo, called from GAMS repos |
| Eval harness | Quality gate for every agent change | `evals/` in this repo |

### 5.3 Alternatives considered

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **Claude Code plugin + MCP server** | Works where people already work; built-in coding tools; hooks; internal marketplace distribution; skills are portable | Needs Claude Code seats; SMEs who avoid the terminal need the IDE / desktop / web front ends and some onboarding | **Recommended** |
| Custom service on the Claude Agent SDK | Full control; can embed in an internal portal | We build and run UI, auth and sessions, duplicating Claude Code | Defer; reuse the same skills and MCP server if a portal is ever required |
| Custom app on the Claude API with tool use | Maximum control | Most code to own; we re-implement file editing, search and permissions | Not for v1 |
| Hosted managed agent with a cloud sandbox | Anthropic runs the loop and sandbox | Needs a GAMS install and license in a hosted container; proprietary code and data leave our network, which needs a policy review | Revisit after the Phase 0 data review |
| Chat-only assistant with uploaded docs | Almost nothing to build | Can't compile or run, no repo context; high risk of wrong option names and defaults | Supplement for Q&A only |

### 5.4 Model and reasoning settings

- **Default model.** Use the current most capable generally available Claude model (Opus class) for the main session and all review and diagnosis subagents, at high reasoning effort. Formulation review and infeasibility diagnosis are reasoning-heavy, and a missed defect costs more than the tokens.
- **Possible cost saving (team decision, based on data).** Run mechanical subagents, such as listing-file summarization and GDX-diff narration, on a smaller, cheaper model tier. Do this only if the eval suite (§10) shows no quality loss.
- **Pinning.** Pin the model ID per plugin release. Rerun the full eval suite before moving to a new model version.

---

## 6. Agent behavior specification

### 6.1 Operating principles

These become the core instructions of the plugin and are enforced by hooks and evals where possible.

1. **Evidence over recall.** Every finding cites a `file:line` and at least one of these:
   - compiler or run output
   - a listing or log excerpt
   - a GDX diff
   - a validated option definition
   - a doc section

   If none is available, the finding is labeled a *hypothesis*.
2. **Validate before recommending.** The agent checks every GAMS/CPLEX option name and value against the installed release's option definitions (through `gams-tools`) before putting it in an answer or in code.
3. **Compile before claiming done.** GAMS the agent writes or edits must compile (`action=c`) for every affected entry point. Where a test case exists, it must also run and match the baseline, or the agent explains the difference.
4. **Separate the layers.** Formulation (math), implementation (GAMS code), data and solver-configuration findings stay distinct, because each has a different owner and fix.
5. **SMEs own intent.** When the intended behavior is unclear, the agent asks or states its assumption. It never silently "fixes" a formulation to match a guess.
6. **Minimal, conventional diffs.** Follow the internal standards and the existing style of the file. No drive-by refactors inside feature changes.
7. **Version awareness.** State which GAMS/CPLEX release is assumed, and flag behavior that differs across releases.
8. **Respect boundaries.** The agent never:
   - reads protected data paths
   - runs code outside the sandbox
   - loosens tolerances or limits to make a problem go away without flagging it

### 6.2 Review output contract

Every review, local or CI, produces the same five sections.

**1. Summary:** what changed, the overall risk, and the top three issues.

**2. Findings table:** one row per finding. Example:

| ID | Severity | Category | Location | Finding | Recommendation | Confidence | Verified by |
|---|---|---|---|---|---|---|---|
| R1 | Major | Formulation | `models/dispatch/equations.gms:142` | `capLimit(g,t)` is generated for every `g`, including retired units. Spec §3.2 limits it to `active(g)`. | Add `$active(g)` to the equation's domain condition. | High | Compile + row count (412 → 388) on `dispatch-small` |
| R2 | Blocker | Solve handling | `models/dispatch/main.gms:310` | Results are written to the output GDX without checking `dispatch.modelStat`. An infeasible solve exports stale levels. | Check against `%modelStat.optimal%` (and the accepted alternatives), and `abort` or flag otherwise. | High | Code inspection |

**3. Spec traceability** (when a spec is provided): one row per spec element, with status *matches*, *differs*, *missing in code* or *extra in code*.

**4. Verification log:** what was compiled or run, with which data, defines and limits.

**5. Not checked:** an explicit list of what was not checked, so silence is never mistaken for approval.

Severities:

| Severity | Meaning |
|---|---|
| **Blocker** | Wrong results or failure likely. Examples: an equation missing from the model statement, a sign error, an unchecked failed solve used downstream. |
| **Major** | Wrong results in some cases, a significant performance or numerical risk, or a standards violation with downstream impact. |
| **Minor** | Maintainability or clarity issue. |
| **Nit** | Style. |
| **Question** | Needs SME confirmation of intent. |

### 6.3 Knowledge coverage

**GAMS language and runtime**

- **Language basics.** Sets, aliases, subsets and domains, dynamic sets, ordered sets, `ord`/`card`, and lag/lead (linear and circular).
- **Conditions and data semantics.** Dollar conditions (left vs. right side, equation domains), and zero vs. missing vs. `eps`.
- **Model statements and solves.** Model statements and model attributes (`modelStat`, `solveStat`, `optFile`, `solveLink`, `holdFixed`, `scaleOpt`, `resLim`, `optCR`/`optCA`, `threads`).
- **Compile-time features.** Dollar control options, `$include`/`$batInclude`, compile-time variables and `--` defines.
- **Data I/O.** Domain-checked loads, GDX, GAMS Connect, GAMS Transfer, embedded Python code.
- **Scenario patterns.** Loops of solves and the state they carry over (bounds, levels, marginals), and GUSS for scenario sweeps.
- **Reading output.** Listing-file anatomy: compile errors, equation and column listings, solve summary, `INFES` markers.
- **Performance and debugging.** Execution profiling, reference files and cross-referencing.
- **Python tooling.** GAMSPy and the GAMS Python API, if used internally (Q3).

**CPLEX through GAMS**

- **Option files.** Mechanics of `cplex.opt` and `optFile`.
- **Algorithm choice.** LP algorithm selection, barrier and crossover.
- **MIP search.** Gap and limit semantics, MIP emphasis, cuts, heuristics, MIP starts and branching priorities, the solution pool.
- **Reproducibility.** Determinism (threads, parallel mode).
- **Infeasibility.** Conflict refiner / IIS and FeasOpt.
- **Numerics.** Coefficient ranges, scaling, tolerances and condition numbers; when to prefer indicator constraints over big-M.
- **Duals from MIPs.** Getting marginals by re-solving the fixed problem.
- **Tuning.** The CPLEX tuning tool, run time-boxed on representative instances.
- **Logs.** Reading CPLEX logs: the node log, gap progress, and where time goes (root vs. tree).

**Internal (captured in Phase 0)**

- **Standards.** Coding standards and naming conventions, and the model catalog (purpose, owners, entry points).
- **Shared vocabulary and settings.** Domain glossary and approved option files with their rationale.
- **History.** Recurring review findings, and lessons learned from incidents.
- **Interfaces.** Downstream consumers of output GDX/report schemas.

The appendices hold the **seed review checklist** (A) and the **proposed repository layout** (B).

---

## 7. Component design

### 7.1 Skills (knowledge, loaded on demand)

| Skill | Contents | Primary sources |
|---|---|---|
| `gams-language` | Semantics and pitfalls, in reference files by topic: sets and domains, conditions, data semantics, loops and solves, dollar control, GDX/Connect, embedded code, performance | Version-pinned GAMS docs + SME review |
| `cplex-via-gams` | Option-file mechanics; options grouped by purpose; status codes; log interpretation; infeasibility workflow; numerics; tuning workflow | GAMS/CPLEX solver manual + CPLEX parameter reference for the bundled version |
| `gams-review` | Review procedure, checklist (Appendix A), severity rules, output contract (§6.2) | This plan + Phase 0 defect taxonomy |
| `org-gams-standards` | Internal conventions, model catalog, glossary, approved option-file patterns | Internal docs; owned by the SME council |
| `gams-testing` | Regression-test pattern: small datasets, golden GDX, tolerance-based diff, CI wiring | Built in Phase 2 |
| `formulation-docs` | Turning GAMS into math notation (LaTeX/Markdown), spec ↔ code traceability tables | Built in Phase 2 |

Each skill keeps a short `SKILL.md` that points to deeper `references/*.md` files, so only what a task needs gets loaded.

### 7.2 Subagents (roles with scoped tools)

| Subagent | Role | Tools | Notes |
|---|---|---|---|
| `gams-reviewer` | Code and formulation review against the checklist and standards | Read-only repo tools; `gams-tools` compile / xref / listing / GDX / options | No edit tools. Used locally and in CI. |
| `formulation-auditor` | Spec ↔ code traceability; renders equations in math notation | Read-only + compile + `docs_search` | Takes a spec path or URL as input |
| `cplex-performance-analyst` | Slow solves and numerics; option recommendations; time-boxed tuning | Read-only + `gams_run` (limits enforced) + option validation | Recommends; never commits option changes on its own |
| `infeasibility-debugger` | Runs with conflict refiner / FeasOpt and maps the conflict back to equations and data | Read-only + `gams_run` + listing/GDX tools | Output: conflict set, data drivers, candidate fixes ranked by plausibility |

The main session acts as the **developer**: it edits code, with the compile-check hook always on.

### 7.3 Slash commands (repeatable workflows)

| Command | What it does |
|---|---|
| `/gams-review [path\|branch\|PR]` | Runs the full review contract on a diff or path. Defaults to the current branch vs. `main`. |
| `/gams-explain <file\|symbol>` | Explains a model, include file or symbol: where it is defined and used, its role and the data feeding it. |
| `/gams-diagnose <run dir\|lst\|log>` | Triage for a failed, infeasible, unbounded or slow run. Routes to the right subagent. |
| `/cplex-tune <entry> [case]` | Reviews option files and solver logs. Optionally runs a time-boxed tuning session on an allowlisted case. |
| `/gams-test <entry>` | Scaffolds or runs regression tests for an entry point. |
| `/gams-doc <model>` | Generates model documentation: sets, parameters, variables, equations in math form, outputs. |

### 7.4 Hooks and permissions

- **PostToolUse compile check** (on edits to `*.gms`, `*.inc` and option files):
  1. Look up the affected entry points in `.gams-agent.yaml`. An include file can't be compiled on its own.
  2. Compile them with `action=c`.
  3. If errors occur, return them (file, line, code, message, short explanation) so the agent fixes them before going on.
- **PreToolUse guard:**
  - Blocks direct `gams` shell runs that bypass `gams-tools`, so the run limits always apply.
  - Blocks reads of protected paths (for example `data/prod/**`).
- **SessionStart check:** verifies that the GAMS system directory and version match `.gams-agent.yaml`, and warns on a mismatch.
- **Permission rules** (in managed / project settings):
  - deny reads of protected data paths
  - deny network tools in CI review jobs
  - the CI review agent gets read-only tools plus PR commenting only

### 7.5 `gams-tools` MCP server

**Why dedicated tools rather than raw shell:** typed tools let us enforce limits, return compact structured results instead of multi-megabyte listing files, and audit every run.

| Tool | Input | Output |
|---|---|---|
| `gams_compile` | entry point, defines | Structured errors: file, line, column, error code, message, explanation |
| `gams_run` | entry point, allowlisted test case, defines, limits | Solve status (`solveStat`, `modelStat`), objective, model statistics (rows, columns, non-zeros, discrete variables), time, artifact paths |
| `listing_summary` | `.lst` path, sections | Compile and execution errors, solve summaries, infeasibility markers, trimmed equation/column listing for named symbols |
| `log_summary` | `.log` path | CPLEX progress: root bound and gap, node throughput, incumbent timeline, warnings |
| `gdx_inspect` | GDX path, symbol, filter | Symbol table, record counts, sampled records |
| `gdx_diff` | two GDX paths, tolerances, symbols | Per-symbol differences within tolerance, largest deviations |
| `symbol_xref` | entry point | Symbols declared, defined, assigned, referenced and unused (from the GAMS reference file) |
| `option_validate` | solver, option file or name/value pairs | Valid/invalid, type and range, default, short description (from the installed option definitions) |
| `error_lookup` | GAMS error code | Explanation and typical causes |
| `docs_search` | query, scope (GAMS / CPLEX / internal) | Ranked passages with source and section, from a version-pinned index |

**Execution guardrails.** A GAMS program can run shell commands (`$call`, `execute`, `put_utility`, embedded code). So running GAMS code means running arbitrary code, and we treat it that way:

- **Isolation:** runs happen in a container with no network egress, the repository mounted read-only, and a scratch work directory.
- **Limits:** CPU, memory and wall-clock caps. The tool itself enforces `resLim` and `threads` caps; the prompt is not relied on.
- **Data and secrets:** only allowlisted test datasets, and no credentials in the environment beyond the GAMS license.
- **Audit:** every invocation is logged (who, what, inputs, duration, outcome).

**Implementation:** Python, using the GAMS Python API / GAMS Transfer for GDX and a standard MCP server library. The same server and image run locally and in CI.

### 7.6 Per-repository configuration

Each GAMS repository adopts a **`CLAUDE.md`**, generated from a template in this repo. It covers:

- purpose and model catalog
- how to compile, run and test
- data locations (allowed vs. protected)
- the GAMS/CPLEX release
- pointers to standards

It also adopts a **`.gams-agent.yaml`** read by the hooks, the MCP server and CI:

```yaml
gams:
  version: "<pinned release>"        # must match production
entry_points:
  - path: models/dispatch/main.gms
    defines: { scenario: base, horizon: 24 }
test_cases:
  - name: dispatch-small
    entry: models/dispatch/main.gms
    defines: { data: tests/data/dispatch_small.gdx }
    baseline_gdx: tests/baseline/dispatch_small.gdx
    tolerance: { rel: 1.0e-6, abs: 1.0e-6 }
    limits: { reslim: 120, threads: 2 }
protected_paths:
  - data/prod/**
option_files:
  - models/dispatch/cplex.opt
```

### 7.7 CI pull-request review

The workflow triggers on PRs that touch GAMS sources, option files, `.gams-agent.yaml` or test data.

1. **`gams-checks` (deterministic, no LLM).** It produces artifacts for the next step and fails the build on its own for compile errors or regression differences above tolerance.
   - compile all affected entry points
   - run the regression cases
   - `gdx_diff` against baselines from the target branch
   - check model statistics (row/column counts) against the target branch
   - validate option files
2. **`agent-review`.** Runs the `gams-reviewer` subagent with read-only tools, using the diff and the `gams-checks` artifacts.
   - posts one summary comment that follows §6.2
   - adds inline comments only for Blocker/Major findings with Medium or High confidence; minor items and nits go into the summary
3. **Humans approve.** Branch protection and CODEOWNERS (SMEs for model code) stay unchanged. Developers can ask follow-up questions by mentioning the agent on the PR.

**Shadow mode first.** For the first 2–3 weeks, reviews go to the CI job summary only and are compared with the human reviews. Comments are switched on once precision meets the target in §10.

---

## 8. Knowledge acquisition and curation

### External sources (version-pinned)

- **GAMS documentation** for our production release(s): language reference, dollar control options, the CPLEX solver manual, GDX / Connect / Transfer, and GAMSPy if used.
- **CPLEX parameter reference** for the CPLEX version bundled with that GAMS release.
- **GAMS Model Library**, as public examples for skills and evals.
- **Licensing check:** confirm the documentation license terms before mirroring it internally. If mirroring isn't allowed, index links and short summaries instead.

### Internal sources

- coding standards (drafted in Phase 0 if none exist)
- model catalog and glossary
- approved option files with their rationale
- incident write-ups
- **Review history.** We mine historical PR review comments on GAMS code into a defect taxonomy, and that taxonomy drives the checklist and the seeded-defect evals.

### Curation process

- **Ownership:** an SME council of 2–3 senior modelers owns `org-gams-standards` and the checklist, enforced through CODEOWNERS.
- **Learning from misses:** every agent miss or false positive reported during the pilot becomes an eval case. When it generalizes, it also becomes a checklist or skill update.
- **Upgrades:** on every GAMS/CPLEX upgrade, rebuild the docs index, rerun option validation on all approved option files, and rerun the evals.

---

## 9. Security, data and licensing

- **Data classification.** Classify model code and input data. Choose the approved way to access Claude (direct enterprise agreement or our cloud provider) and the data retention settings to match. Decide this in Phase 0, before any code is shared.
- **Data scope.** The agent works on code plus approved test or synthetic datasets only. Protected paths are denied by permission rules and the PreToolUse guard.
- **Execution.** All GAMS runs go through the sandbox described in §7.5.
- **Secrets.** The GAMS/CPLEX license is mounted as a CI secret. No other credentials go into the sandbox or the CI review job.
- **Licensing.** Confirm early that GAMS/CPLEX license terms allow CI and sandbox use, and how many runs may happen at once.
- **Untrusted input.** PR content and comments are untrusted input to the CI agent. That agent has read-only tools and can only post comments; it cannot push, approve or merge.
- **Audit.** We keep MCP tool-invocation logs and CI review outputs. Access is reviewed together with security.

---

## 10. Evaluation plan

### Eval sets

| Set | Construction | Graded by |
|---|---|---|
| **Seeded defects** | 10–20 base models (internal pilot models; GAMS Model Library if access is restricted) × ~15 defect classes from Appendix A and the Phase 0 taxonomy. Examples: missing equation in the model statement, wrong `$` condition, uncontrolled index, lag boundary error, sign flip, oversized big-M, unchecked `modelStat`, stale bounds in a solve loop, filtered load dropping records | Automatic: right location and category. SMEs judge findings not in the ground truth. |
| **Historical PRs** | 30–50 past GAMS PRs with human review comments | Recall against human findings; SMEs rate extra findings as valid or invalid |
| **Coding tasks** | 15–25 spec → implementation tasks on pilot models | Compiles; regression passes (GDX within tolerance); rubric review by an SME |
| **Diagnosis tasks** | 10–20 broken runs with a known root cause (infeasible, unbounded, numerical, slow, compile and execution errors) | Root cause identified; fix verified by rerun |
| **Knowledge Q&A** | 75–100 questions on GAMS semantics and CPLEX behavior, answers written by SMEs | Rubric (LLM judge calibrated on an SME-graded subset); every option name and value checked automatically |

### Targets for pilot → GA

These are proposals that leadership and the SME council agree on in Phase 0.

| Metric | Target |
|---|---|
| Recall on seeded Blocker/Major defects | ≥ 80% |
| Precision of findings (SME-rated valid) | ≥ 80% |
| Option names and values valid for the pinned release | 100% |
| Agent-written code that compiles | ≥ 95% |
| Coding tasks passing regression | ≥ 85% |
| Diagnosis tasks with the correct root cause | ≥ 75% |

### Cadence

- **Every change** to skills, prompts, hooks, the MCP server or the model version runs the fast subset in this repo's CI.
- **Each release** runs the full suite.
- **Results** are tracked over time so regressions show up.

---

## 11. Delivery roadmap

Durations are indicative for 1–2 engineers plus about 10–20% of the SME council's time.

| Phase | Duration | Deliverables | Exit criteria |
|---|---|---|---|
| **0. Discovery and decisions** | ~2 weeks | Inventory of GAMS repos, entry points, GAMS/CPLEX versions, CI and licenses; interviews with 4–6 SMEs and 4–6 developers; defect taxonomy mined from past reviews; draft internal standards; data classification and deployment decision; pilot repos chosen | Scope, version matrix, data policy and success metrics signed off; answers to the open questions in §14 |
| **1. Knowledge foundation and MVP** | ~3 weeks | Plugin skeleton and internal marketplace; `gams-language`, `cplex-via-gams`, `gams-review`, `org-gams-standards` v0; `CLAUDE.md` template and `.gams-agent.yaml` schema adopted in pilot repos; compile-check hook; `/gams-review`, `/gams-explain` | Pilot users can run local reviews; eval baseline v0 recorded |
| **2. Tooling** | ~4 weeks | `gams-tools` MCP server and sandbox image; four subagents; `/gams-diagnose`, `/cplex-tune`, `/gams-test`, `/gams-doc`; `gams-testing` and `formulation-docs` skills | Tool tests pass; measurable eval gain over v0 on coding and diagnosis sets |
| **3. Evaluation harness** | Starts in Phase 1, then continuous | All five eval sets; runner; CI gating in this repo; trend reporting | GA targets measured on every release |
| **4. CI PR review** | ~2–3 weeks | Reusable `gams-checks` + `agent-review` workflows; comment policy; shadow mode | In shadow mode, precision ≥ target over at least 20 PRs |
| **5. Pilot → GA** | ~4–6 weeks pilot | Pilot with the cohort; weekly triage; misses become evals and skill updates; onboarding guide; office hours | GA targets met; support and ownership model in place |

---

## 12. Rollout, ownership and operations

- **Roles:**
  - Product owner (engineering lead)
  - 1–2 engineers for the plugin, MCP server, CI and evals
  - SME council for standards, checklist and eval grading
  - Security and IT review at the Phase 0 and Phase 4 gates
- **Pilot cohort:** 3–5 SMEs and 3–5 developers across 1–2 model repositories.
- **Feedback loop:** low-friction feedback (reactions on review comments plus a `/gams-feedback` note), weekly triage, and a fixed path from each miss to an eval case and a skill update.
- **Release process:** semantic versioning of the plugin; a changelog; eval results attached to every release; users update through the marketplace.

### Ongoing metrics

| Area | Metrics |
|---|---|
| Quality | Eval scores over time, SME-rated precision of review findings, how often agent suggestions are accepted |
| Adoption | Weekly active users, share of GAMS PRs with an agent review, command usage |
| Impact | Review turnaround time, defects caught before merge vs. escaped to later runs, time to diagnose failed or infeasible runs |
| Cost | Spend per review and per active user |

---

## 13. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| **Wrong GAMS/CPLEX facts.** Option names and defaults change across releases. | Bad advice, loss of trust | Option validation against installed definitions; version-pinned docs; "verified by" field; Q&A eval set with automatic option checks |
| **Plausible but wrong formulation critiques** | SMEs lose trust; time wasted | Evidence and confidence required; shadow mode; precision tracked; SMEs stay approvers |
| **Noisy CI comments** | Reviews get ignored | Severity and confidence thresholds; batched minor findings; tuning in shadow mode |
| **Running agent-written GAMS is arbitrary code execution** | Security incident | Sandbox with no network, read-only mounts, allowlisted data, no credentials; limits enforced in the tool |
| **Proprietary data exposure** | Policy or legal breach | Phase 0 data decision; test and synthetic data only; deny rules; enterprise data controls |
| **Long or expensive solves started by the agent** | Wasted compute and licenses | `resLim` / `threads` / wall-clock caps in `gams_run`; tuning only on allowlisted cases |
| **Version drift** (GAMS and CPLEX upgrades) | Stale guidance | Version matrix in `.gams-agent.yaml`; upgrade checklist (§8); evals on upgrade |
| **Stale internal standards** | Agent enforces outdated rules | CODEOWNERS on standards; quarterly review; misses feed back into standards |
| **License limits for CI or sandbox** | Blocks Phases 2 and 4 | Confirm terms and concurrency in Phase 0; queue runs if seats are limited |
| **Over-reliance by junior developers** | Skills erode | The agent explains its reasoning and cites docs; humans approve; reviews are learning material |

---

## 14. Open questions (decisions needed in Phase 0)

1. **Q1:** Which GAMS and CPLEX releases are in production? Do several run at once across teams?
2. **Q2:** Is CPLEX used only through GAMS, or also directly (OPL, docplex, CPLEX APIs, LP/MPS workflows)? Is direct use in scope for v1?
3. **Q3:** Do any teams use GAMSPy, the GAMS Python API, GAMS MIRO or GAMS Engine?
4. **Q4:** Where is GAMS code hosted, and which CI system runs it? (GitHub Actions is assumed.)
5. **Q5:** What data classification applies to model code and input data? What is the approved way to access Claude, and which retention settings apply?
6. **Q6:** Do written internal GAMS coding standards exist, and who owns them?
7. **Q7:** Do our GAMS/CPLEX licenses allow CI and sandbox use? How many runs can happen at once?
8. **Q8:** Where do SMEs work today (GAMS Studio, VS Code, other)? How comfortable are they with a terminal?
9. **Q9:** Are there representative small datasets we can use freely, or must we build synthetic ones?
10. **Q10:** Who owns each success metric, and what are the final pilot → GA thresholds?
11. **Q11:** Where do formulation specs live (docs repo, wiki, documents)? Should the agent read them through a connector?

---

## Appendix A: Seed review checklist

This is a starting point for the `gams-review` skill. The SME council validates it in Phase 0 and extends it with internal standards and the mined defect taxonomy.

### A.1 Formulation correctness
- [ ] Each equation's algebra matches the spec: relation (`=e=` / `=l=` / `=g=`), signs, coefficients, units.
- [ ] Each equation is generated over exactly the intended domain. Its `$` conditions exclude exactly the invalid tuples; check for both over- and under-generation, using row counts.
- [ ] The model statement includes every intended equation, and no stray ones (`/all/` vs. an explicit list).
- [ ] Sums and products run over the correct sets with the correct controlling indices. Aliases are used where a set appears twice, and nothing is double counted.
- [ ] Lag/lead references handle the first and last periods on purpose: initial and terminal conditions, circular vs. linear.
- [ ] Variable types (`positive`, `free`, `binary`, `integer`, SOS, semi-continuous) and bounds match their physical or business meaning. No variable is free by accident.
- [ ] Big-M values come from data and are as tight as possible. Indicator constraints were considered.
- [ ] The objective has the right sense, includes every cost or benefit term, and uses consistent units and discounting.

### A.2 Data handling
- [ ] Zero vs. missing vs. `eps` is handled correctly. Zeros are not stored, which affects `$` conditions and GDX output.
- [ ] Division, `log`, power and similar operations are guarded against zero or negative arguments.
- [ ] External data loads are domain-checked (`$loadDC` / `execute_loadDC`). Filtered loads, which silently drop bad keys, are justified and their dropped counts reported.
- [ ] Preconditions are asserted, e.g. `abort$(...)` for non-negative demand or balanced totals.
- [ ] No magic numbers: constants are named scalars or parameters with explanatory text and units.

### A.3 Solve orchestration and robustness
- [ ] After every `solve`, `modelStat` / `solveStat` are checked against the `%modelStat.*%` / `%solveStat.*%` constants and handled. Results are never used blindly.
- [ ] In loops of solves, bounds (`.lo` / `.up` / `.fx`), levels and marginals left over from earlier iterations are reset or kept on purpose. GUSS was considered for scenario sweeps.
- [ ] Solver choice and stopping criteria (`optCR`, `optCA`, `resLim`, `iterLim`) are explicit and justified.
- [ ] Runs that must be reproducible use a fixed thread count and deterministic parallel mode.
- [ ] The `solveLink` mode suits the solve pattern (e.g. many small solves).
- [ ] If MIP marginals are reported, the fixed-problem re-solve is done on purpose and documented.

### A.4 Solver configuration (CPLEX)
- [ ] Option files are version-controlled and named by purpose. Every option is valid for the pinned release, with a comment on why it is set.
- [ ] Every non-default option has evidence behind it (a tuning run, a benchmark, or a documented rationale); no cargo-culting.
- [ ] Tolerances are not loosened to hide infeasibility or numerical trouble.
- [ ] Numerics: coefficient ranges are reasonable, and scaling (`.scale` + `scaleOpt`) was considered where ranges are wide.
- [ ] MIP starts and branching priorities, when supplied, are wired correctly and actually used.

### A.5 Performance
- [ ] Equations and assignments are sparse (conditioned on existing data), not dense cross-products.
- [ ] Parallel (vectorized) assignments are used instead of `loop` where possible.
- [ ] Generation and execution hot spots on large instances were checked with profiling.
- [ ] Production runs restrict listing output (`limRow`, `limCol`, `solPrint`), but a debug switch can turn it back on.

### A.6 Code structure and maintainability
- [ ] Declarations have explicit domains; the universe `*` is used only with justification.
- [ ] Every symbol declaration has explanatory text.
- [ ] Compile-time switches (`--name=value`, `$setGlobal`) have defaults (`$if not set`) and are documented.
- [ ] There are no unused or undefined symbols (checked with the reference file).
- [ ] Redefinition switches such as `$onMulti` are justified.
- [ ] Include structure and naming follow the internal standards.

### A.7 Security and operations
- [ ] Shell escapes (`$call`, `execute`, `put_utility`, embedded code) are reviewed: no unsanitized inputs, hard-coded credentials or user-specific absolute paths.
- [ ] Input and output paths are parameterized.
- [ ] Changes to output GDX or report schemas are flagged for downstream consumers.

### A.8 Testing
- [ ] Changed logic is covered by a regression case: a small dataset, a golden GDX, and a tolerance-based diff.
- [ ] Objective and key KPIs are within tolerance on the baseline datasets, and any differences are explained in the PR.

---

## Appendix B: Proposed repository layout (this repo)

```
Gams_agent/
├── PLAN.md                          # this document
├── README.md
├── .claude-plugin/
│   └── marketplace.json             # internal plugin marketplace
├── plugins/
│   └── gams-sme/
│       ├── .claude-plugin/plugin.json
│       ├── skills/
│       │   ├── gams-language/       # SKILL.md + references/*.md
│       │   ├── cplex-via-gams/
│       │   ├── gams-review/         # checklist.md, output-contract.md
│       │   ├── org-gams-standards/  # CODEOWNERS: SME council
│       │   ├── gams-testing/
│       │   └── formulation-docs/
│       ├── agents/
│       │   ├── gams-reviewer.md
│       │   ├── formulation-auditor.md
│       │   ├── cplex-performance-analyst.md
│       │   └── infeasibility-debugger.md
│       ├── commands/                # gams-review, gams-explain, gams-diagnose, cplex-tune, gams-test, gams-doc
│       ├── hooks/hooks.json         # compile check, guard, session-start version check
│       ├── scripts/                 # hook implementations
│       └── .mcp.json                # registers gams-tools
├── mcp/
│   └── gams-tools/                  # Python MCP server + tests
├── sandbox/
│   └── Dockerfile                   # pinned GAMS + CPLEX; license mounted at runtime
├── templates/
│   ├── CLAUDE.md                    # per-GAMS-repo template
│   └── gams-agent.yaml              # per-repo config template
├── .github/workflows/
│   ├── gams-pr-review.yml           # reusable: gams-checks + agent-review
│   └── evals.yml                    # gates changes to this repo
└── evals/
    ├── seeded_defects/
    ├── historical_prs/
    ├── coding_tasks/
    ├── diagnosis_tasks/
    ├── knowledge_qa/
    └── runner/
```
