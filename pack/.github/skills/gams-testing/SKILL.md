---
name: gams-testing
description: How to add and maintain GAMS regression tests - small datasets, allowlisted test cases in .gams-agent.yaml, golden GDX baselines, tolerance-based comparison with gams-tools, and CI wiring. Use when adding tests for a change, creating baselines, or explaining a baseline difference.
---

# GAMS regression tests

## Pattern

1. **Dataset.** Create a small dataset in `tests/data/<case>.gdx` (or `.inc`) that exercises the change. It should solve in seconds, use synthetic or approved data, and include the edge case the change is about: the first interval, a unit outage, a contract window boundary.
2. **Test case.** Register it in `.gams-agent.yaml`:

   ```yaml
   test_cases:
     - name: uc-small-outage
       entry: models/uc/main.gms
       defines: { data: tests/data/uc_small_outage.gdx }
       baseline_gdx: tests/baseline/uc_small_outage.gdx
       tolerance: { rel: 1.0e-6, abs: 1.0e-6 }
       symbols: [p, u, lambda, cost]      # compare key outputs only
       limits: { reslim: 60, threads: 2 }
   ```

3. **First run.** Run it with `gams_run`. It must end with a usable model status. Inspect the result with `gdx_inspect`.
4. **Baseline.** Create the baseline: copy the run's `results.gdx` (path in the `gams_run` result) to `baseline_gdx`, and say in the PR why these values are right.
5. **Later changes.** Rerun `gams_run`. The result includes the baseline comparison: equal, or the symbols and largest deviations that moved.

## Tolerances

- **LPs and fixed-commitment results.** The defaults (1e-6) work.
- **MIPs solved to a gap.** Objective values may differ within `optCR`. Compare `cost` with `rel` equal to the gap, and keep tight tolerances on quantities that must not move.
- **Marginals (lambda).** Compare them explicitly; they can move under degeneracy. Investigate before loosening.

## Bug-fix tests

Write the case first, show it fails or shows the wrong value on the old code, then fix. Mention both runs in the PR.

## CI

`gams-tools check` (run by the `gams-checks` workflow) compiles every entry point, validates option files, runs every test case and compares baselines. A baseline difference fails the check until the baseline is updated in the same PR, with an explanation.
