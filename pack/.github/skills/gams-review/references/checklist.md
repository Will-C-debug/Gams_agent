# Review checklist (seed v0; owned by the SME council)

## A.1 Formulation correctness
- [ ] Each equation's algebra matches the spec: relation (`=e=` / `=l=` / `=g=`), signs, coefficients, units.
- [ ] Each equation is generated over exactly the intended domain. Its `$` conditions exclude exactly the invalid tuples. Check both over- and under-generation with row counts.
- [ ] The model statement includes every intended equation and no stray ones (`/all/` vs. an explicit list). `symbol_xref` lists equations not in any solved model.
- [ ] Sums and products run over the correct sets with the correct controlling indices. Aliases are used where a set appears twice; nothing is double counted.
- [ ] Lag/lead references handle the first and last periods on purpose: initial and terminal conditions, circular vs. linear.
- [ ] Variable types and bounds match their physical or business meaning. No variable is free by accident.
- [ ] Big-M values come from data and are as tight as possible. Indicator constraints were considered.
- [ ] The objective has the right sense, includes every cost or benefit term, and uses consistent units and discounting.

## A.2 Data handling
- [ ] Zero vs. missing vs. `eps` is handled correctly.
- [ ] Division, `log` and power are guarded against zero or negative arguments.
- [ ] External data loads are domain-checked (`$loadDC` / `execute_loadDC`). Filtered loads (the GAMS 53 default) are justified, and the records they drop are reported.
- [ ] Preconditions are asserted with `abort$(...)`.
- [ ] No magic numbers: constants are named, with explanatory text and units.

## A.3 Solve orchestration and robustness
- [ ] Every `solve` is followed by a `modelStat` / `solveStat` check using `%modelStat.*%` constants, and results are never used blindly.
- [ ] In loops of solves, bounds, levels and marginals left over from earlier iterations are reset or kept on purpose. GUSS was considered for sweeps.
- [ ] Solver choice and stopping criteria (`optCR`, `optCA`, `resLim`, `iterLim`) are explicit, justified and set in one place.
- [ ] Runs that must be reproducible use a fixed thread count and deterministic parallel mode.
- [ ] The `solveLink` mode suits the solve pattern.
- [ ] MIP marginals that are reported come from a deliberate fixed-problem solve (`solvefinal`), documented and covered by a test.

## A.4 Solver configuration (CPLEX)
- [ ] Every option is valid for GAMS 53 (`option_validate`), with no deprecated synonyms.
- [ ] Every non-default option carries a reason and evidence.
- [ ] Tolerances are not loosened to hide infeasibility or numerical trouble.
- [ ] Scaling was considered where coefficient ranges are wide.
- [ ] MIP starts and branching priorities, when supplied, are wired correctly and actually used.

## A.5 Performance
- [ ] Equations and assignments are sparse (conditioned on data), not dense cross-products.
- [ ] Parallel assignments are used instead of `loop` where possible.
- [ ] Generation and execution hot spots on large instances were checked with profiling.
- [ ] Production runs restrict listing output, and a debug switch can turn it back on.

## A.6 Code structure and maintainability
- [ ] Declarations have explicit domains; the universe `*` appears only with a justification.
- [ ] Every symbol declaration has explanatory text.
- [ ] Every define has a default and is documented.
- [ ] There are no unused or undefined symbols.
- [ ] `$onMulti`, `$onImplicitAssign` and `$onUNDF` are justified.
- [ ] No reserved words are used as names (e.g. `logic`).
- [ ] No constructs removed or deprecated in GAMS 53 (e.g. `=C=`), and no features that need a newer release.
- [ ] Include structure and naming follow `org-gams-standards`.

## A.7 Security and operations
- [ ] Shell escapes (`$call`, `execute`, `put_utility`, embedded code) are reviewed: no unsanitized inputs, credentials or user-specific absolute paths.
- [ ] Input and output paths are parameterized.
- [ ] Changes to output GDX or report schemas are flagged for downstream consumers.

## A.8 Testing and traceability
- [ ] Changed logic is covered by a regression case with a golden GDX and a tolerance-based diff.
- [ ] Objective and key KPIs are within tolerance on the baseline datasets; differences are explained in the PR.
- [ ] The PR references its Jira issue, and every acceptance criterion is covered or explicitly deferred.
- [ ] Needed Confluence spec or model-doc updates are listed in the PR.

## A.9 Power-system scheduling models
See the `power-scheduling-domain` skill, [checklist](../../power-scheduling-domain/references/checklist.md).
