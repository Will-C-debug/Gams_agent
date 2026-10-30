---
name: cplex-via-gams
description: Using CPLEX through GAMS 53 - option files, choosing and validating CPLEX options, reading CPLEX logs, solver and model statuses, diagnosing infeasibility (conflict refiner, FeasOpt), numerical trouble, slow MIPs, tuning, and getting marginals/duals from MIPs. Use when a question involves solver options, solve status, solve time, infeasibility or duals.
---

# CPLEX through GAMS (GAMS 53, CPLEX 22.1.x)

## Ground rules

1. **Never recommend an option from memory.** Call `option_info` for each option you mention, and `option_validate` for any option file you write or review. Report the type, the default and the allowed values exactly as returned.
2. **Base advice on the log.** Diagnose slow or failing solves from the log first (`log_summary` on the run's log, or `gams_run` on an allowlisted case), not from generic tuning lists.
3. **Every option change needs evidence.** A before/after run on a representative case, CPLEX tuning output, or a documented incident. Otherwise present it as an experiment to try, not a fix.
4. **Don't trade correctness for speed silently.** Loosening `eprhs`, `epint`, `epopt`, the gaps or the time limits changes results. Say so explicitly.

## Workflows

| Situation | Go to |
|---|---|
| Writing or reviewing an option file | [references/option-files.md](references/option-files.md) |
| Which option affects what | [references/options-by-purpose.md](references/options-by-purpose.md) |
| Model is infeasible / integer infeasible / unbounded | [references/infeasibility.md](references/infeasibility.md) |
| MIP is slow or the gap won't close | [references/mip-performance.md](references/mip-performance.md) |
| Strange results, warnings about conditioning, big-M | [references/numerics.md](references/numerics.md) |
| Need duals or marginals (e.g. system lambda) from a MIP | [references/duals-and-marginals.md](references/duals-and-marginals.md) |
| Reading the log and statuses | [references/reading-logs.md](references/reading-logs.md) |
