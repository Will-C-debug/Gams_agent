---
description: Explain a GAMS model, include file or symbol in plain terms, with math and data flow
agent: formulation-auditor
argument-hint: "<file or symbol>"
---

Explain the file or symbol given after the command for an optimization SME.

- **For a model or file:**
  - its purpose
  - sets
  - data sources (how they are loaded, and whether domain-checked)
  - decision variables
  - each equation in math notation with `file:line`
  - the objective
  - solve and status handling
  - outputs
- **For a symbol:** where it is declared, defined, assigned and used (`symbol_xref`), its meaning and units, and which equations it affects.

If a Confluence page documents this model, cite it and point out where it differs from the code.
