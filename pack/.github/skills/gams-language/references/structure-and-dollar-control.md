# Structure and dollar control

## Includes and defines

- **`$include file.inc`.** Inserts a file. `$batInclude file.inc arg1 arg2` passes `%1`, `%2`.
- **Defines.** `--name=value` on the command line sets `%name%`. Give every define a default: `$if not set horizon $set horizon 24`.
- **`$set` vs. `$setGlobal`.** `$set` is local to the include file; `$setGlobal` is visible everywhere. Prefer `$set` with explicit defaults, and document every define at the top of the entry file.
- **Conditional compilation.** `$if`, `$ifThen ... $else ... $endIf` choose code paths at compile time; `$ifE` evaluates expressions. Keep these shallow.
- **Comments.** `*` in column 1, or `$onText ... $offText` blocks.

## Project layout we prefer

Our internal standard in `org-gams-standards` wins over this list where they differ.

```
models/<model>/
  main.gms          entry point: defines with defaults, includes in order, solve, report
  sets.inc          sets and aliases
  data.inc          parameters and data loading (domain-checked)
  model.inc         variables, equations, model statement
  report.inc        post-solve checks, reporting, unload
  cplex.opt         solver options, each with a justification comment
tests/
  data/             small datasets for regression cases
  baseline/         golden GDX files
```

## Redefinition and implicit assignment switches

- **`$onMulti`.** Allows data for a symbol to be redefined later; it hides accidental double definitions, so require a justification.
- **`$onImplicitAssign`.** Suppresses error 141 (symbol used before assignment); it often hides a missing data load.
- **`$onUNDF`.** Allows `UNDF` values in data, so require a justification.

## Listing control

- **Production runs.** `option limRow = 0, limCol = 0, solPrint = off;` keeps listings small; provide a `--debug=1` switch that turns listings back on.
- **`$offListing` / `$onListing`.** Hide echo-print sections; never hide the whole model, since error line context comes from the echo print.
