# Slow MIPs

## Read the log before changing anything

`log_summary` (or `gams_run`) gives the facts to reason from:

- **Size:** rows, columns, non-zeros, discrete columns, and the reduced size after presolve. A big presolve reduction means the formulation has redundancy.
- **Range statistics** (RHS / Bound / Matrix). A large matrix range points to big-M or unit-scaling problems; see numerics.
- **Root bound vs. final solution.** Compare `root_bound` with the best integer solution.
  - **Large root gap:** weak formulation. Tighten big-M values, add valid inequalities, and use tighter unit commitment formulations.
  - **Small root gap but many nodes:** symmetry or branching issues. Try `symmetry`, priorities, and `mipemphasis 3`.
- **Incumbent timeline.** Late first incumbent → `mipemphasis 1` or 5, heuristics, or a MIP start from the previous run (`mipstart 1` with levels loaded). Incumbents early but the bound stalls → bound-focused settings.
- **Where time goes.** Root processing vs. branch and cut. A long root points to cuts and presolve; long branching points to the search strategy.

## Formulation beats parameters

Ask these before tuning:

- **Big-M.** Are big-M values derived from data and as small as possible? Would `indic` (indicator constraints) be better?
- **Redundant binaries.** Are there binaries that could be continuous (e.g. start-up indicators bounded by on/off logic)?
- **Identical units.** Are there identical units creating symmetry? Aggregate them or add ordering constraints.
- **Tight commitment constraints.** Are minimum up/down constraints in the tight window form (see `power-scheduling-domain`)?

## Running experiments safely

- **Use allowlisted cases.** Change one thing at a time and compare `gams_run` results: time, nodes, gap, objective.
- **Make timings comparable.** Set `threads` and `parallelmode 1`, or use `dettilim` (deterministic ticks), so timing comparisons are meaningful.
- **Tuning tool.** For CPLEX's tuning tool, write the problem file and run `tuning` with `tuningtilim` on 2–5 representative instances. Treat its output as a candidate to validate, not a final answer.
- **Report.** Report each experiment as a table (setting → time, nodes, final gap, objective) and recommend only what improved representative cases without changing results beyond the gap.
