---
applyTo: "tests/**"
description: Conventions for GAMS regression tests and baselines
---

# GAMS regression tests

- **Registration.** Every test case is listed under `test_cases` in `.gams-agent.yaml`, with its entry point, defines, limits and baseline GDX. `gams_run` runs only these.
- **Datasets.** Keep them small (seconds to solve), synthetic or approved for agent use, and in `tests/data/`. Never copy production data.
- **Baselines.** Baselines (`tests/baseline/*.gdx`) change only in a PR that explains the difference. Use `gdx_diff` and list the symbols that moved, and why.
- **Tolerances.** Default `rel: 1e-6, abs: 1e-6`. Loosen only with a reason, e.g. a MIP solved to a gap. Prefer comparing key outputs (`symbols:`) over every symbol.
- **What to cover.** Cover each bug fix with a case that failed before the fix. For MIPs, include at least one case that checks marginals or system lambda, if the model reports them.
