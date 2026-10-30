---
name: org-gams-standards
description: Our internal GAMS coding standards, model catalog (Avalon modules and their GAMS models), naming conventions, approved option-file patterns and glossary. Use when writing or reviewing code to apply house style and conventions, or when asked which model does what. DRAFT v0 until the SME council publishes the GAMS standard in the Confluence STD space.
---

# Internal GAMS standards (DRAFT v0)

> **Status:** draft seeded from the agent plan. The SME council owns this skill. It will be replaced by a snapshot of the GAMS standard page in the Confluence **STD** space once that page exists (Phase 0). Until then, treat the conventions below as *proposed*: flag deviations as **Minor** or **Question**, never Blocker.

## Proposed conventions

| Area | Convention |
|---|---|
| Layout | `models/<model>/main.gms` entry point; `sets.inc`, `data.inc`, `model.inc`, `report.inc`; option files next to the entry point |
| Names | Sets: short lower-case nouns (`g`, `t`, `area`). Parameters: lowerCamelCase (`pmax`, `startupCost`). Variables: lower-case (`p`, `u`, `v`). Equations: lowerCamelCase verbs or nouns (`balance`, `rampUp`) |
| Text | Every declaration has explanatory text with units: `'MW'`, `'$/MWh'`, `'h'` |
| Defines | Declared at the top of `main.gms` with `$if not set x $set x <default>` and a comment |
| Data | Domain-checked loads; no production data in the repo; test data in `tests/data/` |
| Solve | Status check after each solve; `optCR` / `resLim` set in one place; option file justified line by line |
| Output | Explicit `execute_unload` symbol lists; output schema changes noted in the PR |
| Tests | Each entry point has at least one allowlisted case with a baseline GDX |

## Model catalog (to fill in with the SME council in Phase 0)

| Avalon module | GAMS model / entry point | Jira project | Confluence | Owner |
|---|---|---|---|---|
| Unit Commitment | _TBD_ | UC | _TBD_ | _TBD_ |
| Intra-hour (Phase 1 / implementation) | _TBD_ | IHP1, INTRA1 | _TBD_ | _TBD_ |
| Redispatch | _TBD_ | GO | AVR | _TBD_ |
| Contract Energy Scheduling | _TBD_ | CES | _TBD_ | _TBD_ |
| Lambda Policy Module | _TBD_ | GO | AH ("Benefits of Consistent Optimization Strategy with GAMS and the Lambda Policy Module") | _TBD_ |
| Fleet (FOT) | _TBD_ | GO | FOT (pending data decision) | _TBD_ |

## Glossary (seed)

| Term | Meaning |
|---|---|
| Avalon | Product family that embeds our GAMS models (to confirm) |
| Lambda / system lambda | Marginal energy price, from the power-balance marginals |
| UC | Unit commitment: on/off scheduling of generating units |
| Intra-hour | Scheduling within the hour (sub-hourly intervals) |
| Redispatch | Re-optimizing an existing schedule after changes |
| CES | Contract Energy Scheduling |
