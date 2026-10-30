# CPLEX option files in GAMS

## Mechanics

- **Which file is read.** `m.optFile = 1;` reads `cplex.opt` from the working directory; `2` reads `cplex.op2`, `3` reads `cplex.op3`, and so on. `optFile = 0` (default) reads none.
- **Line format.** One option per line: `name value` or `name=value`. Comment lines start with `*`; `!` starts an end-of-line comment.
- **Dot options.** These apply to GAMS symbols: `x.feaspref 2`, `e.lazy 1`, `x.benderspartition 1`.
- **Indicator constraints.** Write `indic eq(i)$y(i) 1`: equation `eq(i)` is active when binary `y(i)` equals 1.
- **`readfile`.** Reads a secondary option file.
- **What GAMS reports.** In the log, GAMS echoes each `Setting 'x': v`, warns `Option 'mipgap' is deprecated`, and reports `Ignoring '...': invalid format or invalid option name`. An ignored option has no effect at all, so typos fail silently. `option_validate` catches them first.

## Precedence (verified)

Command line < `option` statement < model attribute (`m.optCR`) < solver option file.

`epgap 0.05` in `cplex.opt` overrides `option optCR = 0`, and `tilim` overrides `resLim`. Pick one place for each setting and keep it there.

## Review checklist for option files

- [ ] Every line passes `option_validate` against the installed GAMS 53 definitions.
- [ ] No deprecated synonyms (`mipgap` → `epgap`, `integraltol` → `epint`, ...).
- [ ] Each non-default option has a comment with its reason and evidence.
- [ ] No GAMS setting duplicated in the option file without a note saying which one is effective.
- [ ] No internal options that GAMS sets itself (`option_validate` flags them as "internal").
- [ ] Reproducibility: fixed `threads` and `parallelmode 1` when results must be deterministic.
- [ ] Marginals: `solvefinal` left at 1 (GAMS 53 default) when MIP marginals are reported.
- [ ] Diagnostics left on in production (`iis 1`, `writelp`, `quality 1`) are intended and documented.
- [ ] The model's `optFile` number matches the file name.
