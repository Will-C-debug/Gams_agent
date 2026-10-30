# Duals and marginals from MIPs (system lambda)

A MIP has no duals. GAMS/CPLEX reports marginals for a MIP by fixing the discrete variables at their final values and solving the remaining LP (the "fixed problem"). The marginals of that LP are what models read as prices, e.g. `lambda(t) = balance.m(t);`.

## GAMS 53 behavior (verified)

- **Fixed problem solved by default.** CPLEX option `solvefinal` defaults to **1** in GAMS 53: the fixed problem is solved and marginals are returned.
- **Option file for the fixed solve.** `fixoptfile` names an option file read just before the fixed solve (e.g. to pick `lpmethod` there).

## GAMS 54 changes this (verified with 54.6.1)

- **No fixed solve by default.** `solvefinal` defaults to **0**, and there is a new GAMS option `RequestMarginals`. The log says "Solver did not provide marginals ... set option requestMarginals >= 1".
- **What it does to our models.** A unit commitment model reading `balance.m` after the MIP gets **NA for every period**, so system lambda is NA.

**Review rule:** any model that reports MIP marginals must:

1. state how it obtains them (`solvefinal 1` explicitly in the option file is the version-proof choice)
2. have a regression case asserting the marginals are not NA and match the baseline within tolerance

## Interpreting the prices

- **Sign and units.** For a minimization with `balance(t).. sum(g, p(g,t)) =e= demand(t);`, `balance.m(t)` is the change in cost per extra MW of demand in `t`. Check the sign convention against how the equation is written, and the units ($/MWh when costs are $/MWh and periods are hours; scale by interval length otherwise).
- **Commitment is fixed.** Prices from the fixed LP ignore commitment costs; start-up and no-load costs don't show up in lambda. That is a modeling choice the SME should confirm, not a bug.
- **Degeneracy.** Degenerate LPs can return different valid duals across runs or versions. Compare against baselines with a tolerance, and investigate jumps.
