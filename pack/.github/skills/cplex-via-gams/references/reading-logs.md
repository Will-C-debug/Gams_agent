# Reading GAMS/CPLEX logs and listings

## Log landmarks (lo=2/3)

| Line | Meaning |
|---|---|
| `--- Job x.gms Start <date> <time> 53.x.y` | GAMS version actually used |
| `--- Generating MIP model uc` + `--- 185 rows 97 columns 618 non-zeroes` + `--- 24 discrete-columns` | Model size as generated |
| `--- Range statistics` (RHS / Bound / Matrix) | Coefficient ranges; check for big-M and scaling issues |
| `--- Reading option file '...'` then `--- Setting 'x': v` | Options actually applied. `Ignoring '...'` means the option had no effect |
| `Version identifier: 22.1.x.x` | CPLEX library version |
| `Reduced MIP has ...` | Size after presolve |
| Node log columns `Node Left Objective IInf Best Integer Best Bound ItCnt Gap` | Search progress; `*` marks a new incumbent |
| `--- MIP status (101): integer optimal solution.` | CPLEX's own status (101 optimal, 102 optimal within tolerance, 103 integer infeasible, 107/108 time limit with/without a solution) |
| `Number of equations in conflict: n` | Conflict refiner result |
| `--- Solver did not provide marginals` | No duals for a MIP (see duals-and-marginals) |
| `*** Status: Normal completion` | GAMS job status; *not* the model status |

## Listing landmarks

| Section | Meaning |
|---|---|
| Echo print with `****  $140` markers | Compilation errors; with `errMsg=1` followed by `**** LINE n INPUT/INCLUDE file` (innermost file first) |
| `S O L V E      S U M M A R Y` | `SOLVER STATUS`, `MODEL STATUS`, `OBJECTIVE VALUE`, resource usage |
| `**** Exec Error at line n: ...` | Execution error, e.g. division by zero |
| Equation listing `(LHS = 0, INFES = 120 ****)` | Starting-point infeasibility before solving, not a diagnosis |

Use `listing_summary` and `log_summary` rather than reading multi-megabyte files directly.
