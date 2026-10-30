# CPLEX options by purpose (names as defined in GAMS 53 `optcplex.def`)

This list is a map, not a recommendation. Confirm each option with `option_info` before suggesting it, and support the change with a run.

## Stopping criteria and limits

| Option | Meaning | GAMS equivalent |
|---|---|---|
| `epgap` | relative MIP gap (default 1e-4) | `optCR` |
| `epagap` | absolute MIP gap | `optCA` |
| `tilim` | time limit, overrides GAMS `resLim` | `resLim` |
| `dettilim` | deterministic time limit (ticks), reproducible across machines | |
| `nodelim` | node limit | |
| `itlim` | iteration limit | `iterLim` |

## Algorithm choice

| Option | Values (GAMS 53) |
|---|---|
| `lpmethod` | 0 automatic, 1 primal, 2 dual, 3 network, 4 barrier, 5 sifting, 6 concurrent |
| `startalg` / `subalg` | MIP root / node LP algorithm |
| `barcrossalg` | crossover after barrier |
| `mipsearch` | 0 automatic, 1 traditional branch and cut, 2 dynamic search |

## MIP strategy

| Option | Use |
|---|---|
| `mipemphasis` | 0 balance, 1 feasibility, 2 optimality, 3 best bound, 4 hidden feasible, 5 heuristic (find good solutions early) |
| `cuts` | global cut aggressiveness (`-1` off … `5`), or per-family options (e.g. `mircuts`, `flowcovers`, `zerohalfcuts`) |
| `heurfreq`, `rinsheur`, `fpheur`, `lbheur` | heuristics frequency / RINS / feasibility pump / local branching |
| `probe` | probing level |
| `varsel`, `nodesel`, `brdir` | branching variable selection, node selection, direction |
| `symmetry` | -1 automatic … 4 highly aggressive symmetry breaking (unit commitment with identical units often benefits) |
| `polishafterepgap`, `polishaftertime` | start solution polishing |
| `mipstart` | 0–6: use the variable levels as a MIP start (e.g. 1 = discrete values, auto effort) |
| `.prior` + `m.prioropt` | branching priorities from GAMS (`x.prior(i) = ...`) |

## Infeasibility and diagnostics

| Option | Use |
|---|---|
| `iis` | 0 off, 1 conflict refiner after an infeasible solve, 2 conflict refiner without solving |
| `feasopt` | minimum-cost relaxation; weights per symbol via `.feaspref`; `feasoptmode` 0–5 picks sum, count or squares of relaxations |
| `datacheck` | 0 off, 1 on, 2 data checking plus modeling assistance (warnings about questionable data) |
| `quality` | write solution quality statistics (condition numbers, residuals) |
| `mipkappastats` | condition-number statistics for the MIP |
| `writelp`, `writemps`, `writesav` | write the problem as CPLEX LP/MPS/SAV for inspection |
| `names` | pass GAMS names to CPLEX (default 1; needed for readable conflicts and LP files) |

## Numerics

| Option | Use |
|---|---|
| `numericalemphasis` | extra care on numerically difficult models (slower) |
| `scaind` | -1 off, 0 standard, 1 aggressive scaling |
| `eprhs`, `epopt` | feasibility / optimality tolerances (1e-6 defaults) |
| `epint` | integrality tolerance (1e-5) |
| `epmrk` | Markowitz tolerance |

## Parallelism and reproducibility

| Option | Use |
|---|---|
| `threads` | thread count (GAMS `threads` maps here) |
| `parallelmode` | -1 opportunistic, 0 automatic, 1 deterministic |
| `clocktype` | CPU vs. wall clock for limits |

## Tuning

| Option | Use |
|---|---|
| `tuning` | run the CPLEX tuning tool on the listed problem files; writes a recommended option file |
| `tuningtilim` | time limit per tuning run (always set it) |
| `tuningmeasure` | how results across instances are compared |
