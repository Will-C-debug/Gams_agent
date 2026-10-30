---
description: Review CPLEX option files and solver logs, and propose evidence-backed performance changes
agent: cplex-performance-analyst
argument-hint: "<test case name or log file>"
---

Analyze CPLEX performance for the test case or log given after the command.

1. **Validate the option files** used by the model (`option_validate`), and explain each non-default option.
2. **Summarize the log.** Cover model size, reduced size, coefficient ranges, root bound vs. incumbent, the incumbent timeline, nodes, the gap and timing.
3. **Diagnose and propose.** Name the bottleneck and propose formulation changes first, then options, each validated with `option_info`.
4. **Experiment if asked.** Use allowlisted cases only, one change at a time, deterministic settings. Report a results table.
