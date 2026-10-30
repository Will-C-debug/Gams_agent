# GAMS 53 specifics (verified)

These facts were checked against the files shipped in GAMS 53.5.1 (`optgams.def`, `optcplex.def`, `gamserrs.txt`) and against runs. Recheck them with `option_info` on your installed build.

| Topic | GAMS 53 | Notes |
|---|---|---|
| Bundled CPLEX | 22.1.2 (`libcplex2212`) in 53.5.1 | GAMS 54.6.1 bundles CPLEX 22.2.0 |
| CPLEX `solvefinal` | default **1**: after a MIP, the fixed problem is solved and marginals are returned | **GAMS 54.6.1: default 0**, plus a new GAMS option `RequestMarginals`. Without changes, MIP marginals (e.g. system lambda from `balance.m`) come back **NA** under 54 |
| `Filtered` | default `on` (filtered GDX loads) | use `$loadDC` / `execute_loadDC` |
| `ErrMsg` | default 1 (error messages next to the error) | gams-tools relies on it |
| `optCR` | default 1e-4 | |
| `execMode` | 0 = all allowed … 2 = no `$call`/`execute`/embedded code … 4 = no `$echo`/`put` | agent runs use 2 |
| `=C=` equations | error since GAMS 51 | conic code must be rewritten |
| License file | must use the 8-line format since GAMS 51 | matters for CI secrets |
| `mipgap` (CPLEX) | deprecated synonym of `epgap` | GAMS logs "Option 'mipgap' is deprecated" |
| `reslim` in `cplex.opt` | synonym of `tilim`, which overrides GAMS `resLim` | |

## Upgrade watch-list for GAMS 54

When the team moves to GAMS 54:

1. **MIP marginals.** Decide how MIP marginals are obtained (`solvefinal 1` in the option file, or `RequestMarginals`), and add a regression case that checks lambda is not NA.
2. **CPLEX 22.2.0.** Rerun all regression cases and compare against the 53 baselines with `gdx_diff`; MIP solutions may change within the gap.
3. **Option files.** Re-validate every option file with `option_validate` on the 54 installation.
4. **Release notes.** Read the 54 release notes for the remaining behavior changes and add them here.
