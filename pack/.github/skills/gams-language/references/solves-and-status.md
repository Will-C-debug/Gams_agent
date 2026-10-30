# Solves, status checks and option precedence

## Model status (`m.modelStat`)

| Code | Meaning | Usable result? |
|---|---|---|
| 1 | Optimal | yes |
| 2 | Locally Optimal | yes (NLP) |
| 3 | Unbounded | no |
| 4 | Infeasible | no |
| 5 | Locally Infeasible | no |
| 6 | Intermediate Infeasible | no |
| 7 | Feasible Solution | yes, but not proven optimal (limit reached) |
| 8 | Integer Solution | yes, within the gap or a limit |
| 9 | Intermediate Non-Integer | no |
| 10 | Integer Infeasible | no |
| 11 | Licensing Problem | no |
| 12 | Error Unknown | no |
| 13 | Error No Solution | no |
| 14 | No Solution Returned | no |
| 15–17 | Solved Unique / Solved / Solved Singular (CNS) | yes |
| 18 | Unbounded – No Solution | no |
| 19 | Infeasible – No Solution | no |

Use the compile-time constants instead of numbers: `%modelStat.optimal%`, `%modelStat.integerSolution%`, `%modelStat.infeasible%`, `%modelStat.integerInfeasible%`, and so on.

## Solver status (`m.solveStat`)

| Code | Meaning |
|---|---|
| 1 | Normal Completion |
| 2 | Iteration Interrupt |
| 3 | Resource Interrupt (time limit) |
| 4 | Terminated by Solver |
| 5 | Evaluation Interrupt |
| 6 | Capability Problems |
| 7 | Licensing Problems |
| 8 | User Interrupt |
| 9 | Setup Failure |
| 10 | Solver Failure |
| 11 | Internal Solver Failure |
| 12 | Solve Processing Skipped |
| 13 | System Failure |

A run can finish with solver status 1 and model status 19 (infeasible). Always check both.

Pattern:

```gams
solve uc using mip minimizing cost;
abort$(uc.modelStat <> %modelStat.optimal% and uc.modelStat <> %modelStat.integerSolution%)
   'unit commitment returned no usable solution', uc.modelStat, uc.solveStat;
```

## Option precedence (verified with GAMS/CPLEX)

From weakest to strongest:

1. **Command line.** `gams model.gms optCR=0.05`.
2. **`option` statements in the code.** `option optCR = 0;` overrides the command line.
3. **Model attributes.** `uc.optCR = 0.01;`.
4. **The solver option file read through `m.optFile`.** `epgap 0.05` in `cplex.opt` overrides GAMS `optCR`; `tilim` overrides `resLim`.

Keep one source of truth per setting. When both GAMS and the option file set a gap or limit, say which one is effective.

## Relevant GAMS 53 defaults (from optgams.def)

| Option | Default | Note |
|---|---|---|
| `optCR` | 1e-4 | relative MIP gap |
| `optCA` | 0 | absolute MIP gap |
| `resLim` | 1e10 s | wall-clock limit for the solver |
| `iterLim` | 2147483647 | |
| `threads` | 0 | solver decides; negative means leave n cores free |
| `solveLink` | 2 | solver spawned; `5` passes the model in memory (good for many small solves) |
| `holdFixed` | 0 | fixed variables are kept as variables |
| `solPrint` | 1 | solution listing on; `0` removes it |
| `limRow` / `limCol` | 3 | equation/variable listing size; set 0 in production |

## Loops of solves

- **State carries over.** Levels from the previous solve are the next starting point: `.l` values, and `.prior` for priorities. Bounds and `.fx` stay in force until reset.
- **Reset patterns.** `x.lo(i) = 0; x.up(i) = inf;` or re-fix from data at the top of each iteration.
- **Save results each iteration.** Store results into report parameters before the next solve overwrites them.
- **GUSS.** For many scenarios of the same model, use GUSS (`solve m using lp min z scenario dict;`): the model is generated once and only the scenario data change.
