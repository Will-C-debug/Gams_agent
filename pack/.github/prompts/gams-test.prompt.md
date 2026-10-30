---
description: Add or run GAMS regression tests for an entry point
agent: gams-developer
argument-hint: "<entry point or test case>"
---

Work on regression tests for the entry point or test case given after the command, following the `gams-testing` skill.

- **If the case exists:** run it with `gams_run` and report the solve status and the baseline comparison.
- **If it doesn't:** propose a small dataset and a `test_cases` entry for `.gams-agent.yaml` that cover the behavior in question. After I approve, create them, run the case, and explain why the values in the new baseline are right before saving it.
