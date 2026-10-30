# Numerical trouble

## Signals

- **Wide ranges.** GAMS range statistics before the solve: matrix values spanning 6+ orders of magnitude, or very large values (≥1e7). `gams_run` and `log_summary` flag both.
- **CPLEX warnings.** Messages such as "Detected ... numerical difficulties", unscaled infeasibilities, and solutions that violate constraints after unscaling.
- **Fragile results.** Results that change with thread count or tiny data changes, or slightly infeasible solutions reported as optimal.

## Causes and fixes

| Cause | Fix |
|---|---|
| Big-M constants much larger than needed | Derive M from data per constraint, or use indicator constraints (`indic`) |
| Mixed units (MW vs. kW, $ vs. k$) | Rescale data so typical values are within a few orders of magnitude; document units |
| Tiny coefficients from computed data (e.g. 1e-12 residues) | Round or zero them in the data step, e.g. with GAMS `zeroRes` |
| Badly scaled variables | GAMS scaling: `x.scale(i) = ...;` plus `m.scaleOpt = 1;`; or CPLEX `scaind` |

## Measuring

- **Solution quality.** `quality 1` writes solution quality statistics (max violations, condition numbers).
- **Condition numbers for MIPs.** `mipkappastats` reports these.
- **Data checks.** `datacheck 2` reports questionable data and modeling issues before solving.
- **Last resort.** `numericalemphasis 1` trades speed for care. Use it only after the cause is understood, and don't leave it on silently.

Loosening `eprhs` or `epopt` to make warnings go away is not a fix. Flag it in reviews.
