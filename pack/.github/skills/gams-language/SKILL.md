---
name: gams-language
description: GAMS 53 language semantics and pitfalls for writing, explaining and reviewing GAMS models. Covers sets and domains, dollar conditions, zero/missing/eps, lag/lead, loops of solves, model attributes and solve-status checks, data loading (GDX, $loadDC, Connect), dollar control, performance and reserved-word traps. Use for any work on .gms or .inc files.
---

# GAMS language (GAMS 53)

## Work from tools, not memory

| Need | Tool |
|---|---|
| Does it compile? Where exactly is the error? | `gams_compile` (errors carry the file and line *inside* include files, plus a hint) |
| What does error N mean? | `error_lookup` (reads the installed `gamserrs.txt`) |
| Where is a symbol declared, assigned and used? Is anything unused, or an equation left out of the model? | `symbol_xref` |
| Did a change alter results? | `gams_run` on an allowlisted case, then `gdx_diff` against the baseline |
| What do the GAMS 53 docs say? | `docs_search` |

## Rules that catch most defects

1. **Domains.** Prefer explicit domains over `*`. Domain violations at load time are silent with filtered loads (the GAMS 53 default, `Filtered=on`), so use `$loadDC` / `execute_loadDC`.
2. **Equation generation.** A `$` condition on the equation domain (`e(g,t)$active(g)..`) controls which rows exist. A `$` condition inside the body only changes coefficients. Over-generation adds useless or infeasible rows; under-generation silently drops constraints. Compare row counts before and after a change.
3. **Uncontrolled indices.** Error 149 means an index is neither in the equation domain nor summed over.
4. **Zero vs. missing vs. `eps`.** Parameters don't store zeros, so `p(i)$(data(i))` skips zero entries. GDX files don't hold zeros either. Use `eps` for a "present but zero" value.
5. **Lag/lead.** `x(t-1)` is outside the set at the first element, so the term vanishes. `x(t--1)` wraps around (circular). Initial conditions must come from data, e.g. `init_on(g)$(ord(t)=1)`.
6. **Model statement.** `Model m / all /` includes every equation declared so far, including scratch or debug equations. An explicit list silently omits new equations. `symbol_xref` reports equations that are defined but not in any solved model.
7. **Solve status.** Check status after every solve with the compile-time constants, e.g. `%modelStat.optimal%`, `%modelStat.integerSolution%`, `%solveStat.normalCompletion%`. A failed solve leaves the previous levels in place.
8. **Loops of solves.** Bounds, fixed values, levels and marginals persist across solves. Reset or keep them on purpose. Use GUSS for scenario sweeps of the same model.
9. **Reserved words.** `logic` (as in `Logic Equation`) is reserved and fails as an identifier (error 799). Avoid names that collide with keywords and functions.
10. **Shell escapes.** `$call`, `execute`, `put_utility` and embedded code run programs. Agent runs use `execMode=2`, which blocks them (error 542).

## References

- [references/sets-domains-conditions.md](references/sets-domains-conditions.md): sets, subsets, aliases, conditions, ord/card, lag/lead, sameas
- [references/data-and-gdx.md](references/data-and-gdx.md): loading and unloading data, filtered vs. domain-checked loads, special values
- [references/solves-and-status.md](references/solves-and-status.md): model attributes, status codes, option precedence, solveLink, loops of solves, GUSS
- [references/structure-and-dollar-control.md](references/structure-and-dollar-control.md): includes, defines, conditional compilation, project layout
- [references/performance.md](references/performance.md): generation speed, sparse assignments, profiling, listing size
- [references/gams53-specifics.md](references/gams53-specifics.md): verified GAMS 53 facts and what changes in GAMS 54
