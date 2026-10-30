# Diagnosing infeasibility

## 1. Establish what failed

From `gams_run` or `listing_summary`:

| Model status | Meaning | Next step |
|---|---|---|
| 4 / 19 Infeasible | LP or relaxation infeasible | conflict refiner |
| 10 Integer Infeasible | relaxation feasible, no integer solution | conflict refiner on the MIP, then relax integrality questions |
| 3 / 18 Unbounded | missing bound or sign error | check free variables and the objective direction |
| 7 / 8 with solver status 3 | hit a limit, not infeasible | performance, not feasibility |

The equation listing (`limRow`) marks rows `INFES` at the *starting point*, before solving. That is not evidence of infeasibility.

## 2. Find a minimal conflict

1. **Turn on the conflict refiner** in the option file for the diagnostic run: `iis 1` (after an infeasible solve) or `iis 2` (refine without solving first).
2. **Run the case** with `gams_run`. Its result includes the conflict set, also available from `log_summary`:

   ```
   Number of equations in conflict: 4
   fixed: bal(t3) = 300
   upper: lim(g1,t3) < 100
   upper: lim(g2,t3) < 80
   upper: lim(g3,t3) < 50
   ```

3. **Map each member back to the model.** Find the equation definition (`symbol_xref`), the index tuple, and the input data on its right-hand side or bounds. The example above reads: demand at `t3` (300) exceeds total capacity (230).
4. **Explain the conflict in domain terms** for the SME, and list candidate fixes ranked by plausibility. Is it a data error, a missing unit, a wrong sign, or a constraint that is too tight? Don't pick the fix yourself when it is a modeling decision.

The refiner finds one conflict per run. After fixing it, rerun: others may remain.

## 3. Quantify with FeasOpt (when the question is "how far off are we?")

- **Enable FeasOpt.** Set `feasopt 1` and choose `feasoptmode`: 0 minimizes the sum of relaxations; 1 does the same and then optimizes the original objective.
- **Weight what may be relaxed.** `.feaspref`: e.g. `bal.feaspref 1` and `lim.feaspref 100`, so demand balance relaxes before capacity.
- **Report the result.** Report which constraints were relaxed and by how much. That answer helps the SME decide what to change.

## 4. Common causes in scheduling models

- **Demand vs. capacity.** Demand or reserve exceeds the committed or available capacity in a period (check the data first).
- **Initial status.** Initial status conflicts with minimum up/down time at the start of the horizon.
- **Ramping.** Ramp limits make the first period unreachable from the initial output.
- **Bound conflicts.** A must-run or fixed unit conflicts with an outage or derate.
- **Units or interval length.** MW vs. MWh, or a 5- vs. 15-minute interval mismatch.
- **Filtered loads.** A filtered data load dropped a unit or period, which removes capacity.
