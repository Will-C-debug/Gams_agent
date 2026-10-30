# A.9 Power-system scheduling checklist (draft; the SME council validates)

- [ ] Power balance holds in every interval (and area, if modeled), with consistent signs for generation, load, imports/exports and losses.
- [ ] Commitment logic links the on/off, start-up and shut-down variables, including the first interval's initial status from data (`u0`).
- [ ] Minimum up/down times and start-up/shut-down limits honor each unit's initial status carried in from the previous horizon.
- [ ] Ramp limits apply between consecutive intervals and across the horizon boundary (`p0`), scaled to the interval length.
- [ ] MW ↔ MWh conversions use the interval duration consistently in energy, cost and contract terms.
- [ ] Reserve requirements are coupled to the headroom of committed units.
- [ ] Piecewise-linear cost curves are convex where the formulation assumes it; otherwise SOS2 or binaries are used.
- [ ] Outages, derates and must-run status come from data and appear in bounds or `$` conditions, not hard-coded values.
- [ ] System lambda comes from the power-balance marginals of a fixed-commitment LP re-solve (`solvefinal`). Sign and units are documented, it is consistent with the dispatch, and a regression case asserts it is not NA.
- [ ] Contract energy limits (minimum and maximum energy over a period) are enforced over the right windows.
