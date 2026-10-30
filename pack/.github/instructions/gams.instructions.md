---
applyTo: "**/*.gms,**/*.inc"
description: GAMS coding rules for model and include files
---

# GAMS code rules (GAMS 53)

- **Domains.** Declare symbols with explicit domains. Use the universe `*` only with a comment explaining why.
- **Text.** Every declaration carries explanatory text with units, e.g. `Parameter cap(g) 'capacity MW';`.
- **Equation domains.** Condition equation domains on existing data, e.g. `maxOut(g,t)$active(g)..`. Exclude exactly the invalid tuples, then check row counts with `gams_run` or the listing.
- **Solve status.** Check status after every `solve` with the compile-time constants, e.g. `abort$(m.modelStat <> %modelStat.optimal% and m.modelStat <> %modelStat.integerSolution%) 'no usable solution';`. Never export results from an unchecked solve.
- **Data loads.** Use domain-checked loads: `$loadDC` / `execute_loadDC`. GAMS 53 defaults to filtered loads (`Filtered=on`), which silently drop records with unknown labels.
- **Arithmetic guards.** Guard division, `log` and power against zero or negative arguments.
- **Zero, missing and `eps`.** Zero is not stored, so `$` conditions on parameters skip zeros. Use `eps` when a zero must exist as a record.
- **Lag/lead.** Handle the first and last periods explicitly: initial status from data, terminal conditions, and linear (`t-1`) vs. circular (`t--1`) lags.
- **Loops of solves.** Reset or keep bounds (`.lo/.up/.fx`), levels and marginals on purpose; values carry over between solves.
- **Reserved words.** Don't name symbols after reserved words. `logic`, for example, starts a `Logic Equation` declaration and causes error 799.
- **Shell escapes.** Avoid `$call`, `execute` and embedded code in model logic. Agent runs use `execMode=2`, which blocks them (error 542).
- **Compile check.** After editing, compile the affected entry points with `gams_compile` and fix every error before continuing.
