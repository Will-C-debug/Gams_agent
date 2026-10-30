---
name: power-scheduling-domain
description: Power-system scheduling knowledge for our GAMS models - unit commitment, economic and intra-hour dispatch, redispatch, contract energy scheduling, reserves, ramping, cost curves and system lambda (marginal prices). Use when writing, explaining or reviewing scheduling formulations, or when an SME asks whether a model behaves correctly in power-system terms.
---

# Power-system scheduling models

> Inferred from our Jira projects (UC, IHP1, INTRA1, CES, GO) and Confluence spaces (AH, AVR, FOT). The SME council validates this skill in Phase 0. Where our models deliberately differ from the textbook forms below, the model and its Confluence spec win: flag the difference as a **Question**, not a defect.

## How to use

- **Writing or reviewing constraints.** Compare against the standard forms in [references/formulations.md](references/formulations.md), then run the domain checklist in [references/checklist.md](references/checklist.md).
- **Questions about prices or lambda.** Read [references/lambda.md](references/lambda.md), together with `cplex-via-gams/references/duals-and-marginals.md`.
- **Explaining results to SMEs.** Use power-system language (commitment, headroom, ramping, marginal unit, price-setting) and tie every statement to equation names and data.

## Quick sanity checks on any schedule

1. **Supply meets demand.** Generation + imports − exports (− losses) = demand in every interval.
2. **Commitment consistency.** Committed units produce between `pmin` and `pmax`; uncommitted units produce 0.
3. **Startups and shutdowns.** Each one corresponds to an on/off change, and respects the initial status.
4. **Reserves.** Covered by the headroom of committed units: `pmax·u − p`.
5. **Ramping.** Ramp limits hold between consecutive intervals, scaled to the interval length.
6. **Lambda.** It equals the marginal cost of the price-setting unit in uncongested, non-degenerate periods. Explain any period where it doesn't.
