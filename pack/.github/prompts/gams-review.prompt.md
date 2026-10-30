---
description: Review GAMS/CPLEX changes on this branch (or a path) with the full review contract
agent: gams-reviewer
argument-hint: "[path | base branch, default main]"
---

Review the GAMS/CPLEX changes on the current branch against `main`. If the user gave a path or a base branch after the command, use that instead.

Follow the `gams-review` skill:

- **Scope.** List the changed files.
- **Requirements.** Find the Jira issue from the branch name and pull its acceptance criteria and linked Confluence spec.
- **Verify.** Run `gams_compile` and `symbol_xref`, `option_validate` on changed option files, and `gams_run` on the covering allowlisted cases.
- **Check.** Apply the checklist, including the power-scheduling items.
- **Report.** Write the report in the output-contract format: Summary, Findings, Requirements traceability, Spec traceability, Verification log, Not checked.
