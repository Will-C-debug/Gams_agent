---
applyTo: "**/*.opt,**/*.op2,**/*.op3,**/*.op4,**/*.op5,**/*.op6,**/*.op7,**/*.op8,**/*.op9"
description: Rules for GAMS/CPLEX solver option files
---

# CPLEX option files

- **Validate everything.** Check every line with `option_validate` (or `option_info` for one option) against the installed GAMS 53 definitions. Never add an option from memory.
- **Justify every non-default.** Put a comment line (`* ...`) above it: why it is set, and the evidence (tuning run, benchmark, incident). Remove options nobody can justify.
- **Canonical names only.** Use `epgap`, not the deprecated `mipgap`, and `tilim` or GAMS `resLim`, not both.
- **One source of truth for limits and gaps.** Use GAMS `optCR`/`optCA`/`resLim`, or the option-file `epgap`/`epagap`/`tilim`, not both. The option file wins when both are set.
- **Don't loosen tolerances to hide problems.** Never loosen `eprhs`, `epopt` or `epint` to get past infeasibility or numerical trouble; diagnose instead (`iis`, `feasopt`, `quality`).
- **Reproducibility.** When results must be reproducible, set a fixed `threads` count and `parallelmode 1` (deterministic).
- **Marginals and system lambda.** When the model reports these after a MIP, keep `solvefinal 1` (the GAMS 53 default) and say so in a comment. In GAMS 54 the default becomes 0.
- **Option file numbering.** `m.optFile = 1` reads `cplex.opt`; `2` reads `cplex.op2`, and so on. Check that the model's `optFile` matches the file you edit.
