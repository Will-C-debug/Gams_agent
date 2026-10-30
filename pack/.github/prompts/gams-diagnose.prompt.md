---
description: Triage a failed, infeasible, unbounded or slow GAMS/CPLEX run
agent: infeasibility-debugger
argument-hint: "<run folder | .lst | .log | test case name>"
---

Diagnose the run given after the command.

1. **Summarize the run.** Use `listing_summary` / `log_summary`, or `gams_run` for an allowlisted case: GAMS status, model and solver status, errors, model size and coefficient ranges.
2. **Route by symptom:**
   - **Compilation or execution errors:** explain each with `error_lookup` and point to `file:line`.
   - **Infeasible, integer infeasible or unbounded:** follow the infeasibility workflow (conflict refiner, mapping to data, Jira/Confluence history).
   - **Slow, or the gap won't close:** summarize the MIP progress and hand off to `cplex-performance-analyst` with the evidence.
3. **Finish** with the most likely cause, the evidence, ranked candidate fixes, and what is still unknown.
