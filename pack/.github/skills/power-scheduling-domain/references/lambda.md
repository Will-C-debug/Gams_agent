# System lambda (marginal price)

- **Definition.** Lambda in interval `t` is the marginal cost of serving one more MW of demand: the marginal of the power-balance equation in the LP with commitment fixed. GAMS: `lambda(t) = balance.m(t);` after the MIP, provided the fixed problem was solved. That is the GAMS 53 default (`solvefinal 1`); see `cplex-via-gams/references/duals-and-marginals.md` for GAMS 54.
- **Expected behavior.** In an uncongested, non-degenerate interval, lambda equals the marginal cost of the unit that can still move: the price-setting unit, between its output *and* ramp limits.

  Worked example from the eval model `evals/models/uc_small` (GAMS run, `solvefinal 1`). Units: coal1 at 18 $/MWh, ccgt1 at 28, ct1 at 55. Coal1 starts at 200 MW with a ramp limit of 80 MW/h.

  | Hour | Dispatch | Lambda | Why |
  |---|---|---|---|
  | h1 | coal1 280, ct1 20 | **55** | Coal1 is below capacity but at its *ramp* limit (200 + 80). The next MW comes from ct1, which sits at its minimum output. |
  | h3–h7 | ccgt1 between limits | **28** | Ccgt1 sets the price. |
  | h8 | coal1 270, ccgt1 at minimum | **18** | Coal1 is free to move. |

  "Lambda is high although cheap capacity is idle" is usually a binding ramp, minimum up/down or reserve constraint. Name the constraint, using its marginal, before calling it a bug.
- **Units.** With costs in $/MWh and the objective written in MWh (`p·dur`), `balance.m` comes out in $ per MW per interval. Divide by `dur(t)` to get $/MWh for sub-hourly intervals. Check the model's convention.
- **Sign.** With `sum(p) =e= demand` in a minimization, `balance.m` is positive. Writing the balance as `demand =e= sum(p)` flips the sign. Reports must document which convention they use.
- **Commitment costs.** Start-up and no-load costs do not appear in lambda from the fixed LP. Whether that is right is a market-design question for the SME, so state it, don't change it.
- **Degeneracy.** When several units sit exactly at their limits, the dual can be non-unique, and different CPLEX versions or settings may return different valid values. Compare to baselines with a tolerance and explain jumps.
- **Consistency.** The AH page "Benefits of Consistent Optimization Strategy with GAMS and the Lambda Policy Module" suggests lambda is meant to stay consistent with the dispatch from the same optimization. Check that both come from the same solve and data.
