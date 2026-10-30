---
name: gams-review
description: Procedure, checklist and output format for reviewing GAMS/CPLEX changes (formulation, data handling, solve handling, solver options, performance, structure, security, tests, and traceability to Jira acceptance criteria and Confluence specs). Use for /gams-review, PR reviews, and "review my branch" requests.
---

# Reviewing GAMS/CPLEX changes

## Procedure

1. **Scope.** List changed files (`git diff --name-only <base>...HEAD`) and group them: model code, data, option files, tests, other.
2. **Requirements.** Find the Jira issue from the branch name or PR title (`atlassian-context` skill). Pull its acceptance criteria and any linked Confluence spec. If there is none, say so and review against the code alone.
3. **Verify mechanically before judging:**
   - Run `gams_compile` on each affected entry point. Compilation errors are Blockers.
   - Run `symbol_xref` on each entry point. Look for unused symbols, parameters never assigned, equations not in any solved model, and missing explanatory text.
   - Run `option_validate` on each changed option file.
   - Run `gams_run` on the allowlisted cases that cover the change. Check solve statuses, row/column counts against the base branch, and the baseline diff.
4. **Read the diff against the checklist:** [references/checklist.md](references/checklist.md). Use the domain items (A.9) for scheduling models.
5. **Trace requirements and spec** with the `formulation-docs` skill: one row per acceptance criterion and per spec element.
6. **Write the review** in the output contract format: [references/output-contract.md](references/output-contract.md).

## Judgement rules

- **Severity follows impact on results.** A wrong sign in a balance equation is a Blocker even if the code is tidy.
- **Ask when intent is unclear.** If you cannot tell whether behavior is intended, file a **Question**, not a defect.
- **Confidence follows evidence.** High means tool output or an unambiguous reading of the code. Medium means a reasoned reading of the code. Low means a hypothesis.
- **Don't rewrite the model in a review.** Suggest the smallest change that fixes the finding.
- **Report what you couldn't check.** If GAMS is unavailable or a case can't run, list it under "Not checked". Never imply a check passed.
