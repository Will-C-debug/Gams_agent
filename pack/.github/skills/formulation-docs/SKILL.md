---
name: formulation-docs
description: Turn GAMS models into readable math (LaTeX/Markdown), build spec-to-code traceability tables against Confluence specs and Jira acceptance criteria, and report drift between documentation and code. Use for /gams-doc, formulation audits, and SME questions like "does the code implement the spec?".
---

# Formulation documentation and traceability

## GAMS → math

For each equation, write the math with its domain and conditions, and cite the source line:

```markdown
**maxOut(g,t)**: `models/uc/model.inc:40`
$$ p_{g,t} \le P^{max}_g \, u_{g,t} \qquad \forall g \in G,\ t \in T \;:\; active_g $$
```

Rules:

- **Domain.** Write the domain and every `$` condition as quantifier conditions.
- **Notation.** Map GAMS symbols to notation consistently and list the mapping (symbol, meaning, units, source) in a table at the top.
- **Lags.** Show lag/lead terms and their boundary treatment explicitly, e.g. $u_{g,t-1}$ with $u_{g,0} = u^0_g$.
- **No guessing.** Don't simplify what the code doesn't simplify. If code and spec differ, show both.
- **Verify.** Use `symbol_xref` to make sure every equation in the solved model is covered, and that none is listed twice.

## Traceability table

| Spec element (page, section) | Math | GAMS | Status | Notes |
|---|---|---|---|---|
| Capacity limit (3.2) | $p \le P^{max} u$ | `maxOut` model.inc:40 | matches | |
| Reserve (3.4) | 10% of demand | `reserve` model.inc:52 | differs | code uses `reserveShare` from data |
| Ramp at horizon start (3.5) | uses $p^0$ | none | missing in code | |
| none | | `debugEq` model.inc:90 | extra in code | not in spec; in model `/all/` |

The status values are *matches*, *differs*, *missing in code* and *extra in code*. Cite the Confluence page title and version (from `getConfluencePage`) and the Jira key for acceptance criteria.

## Doc-drift report (`/gams-doc`)

Compare the model's Confluence page with the code:

- **Coverage.** Equations, variables and data the page describes that are missing or different in the code, and the reverse.
- **Freshness.** The page's last-updated date vs. the last commit that touched the model (`git log -1 --format=%cs -- <paths>`).
- **Output.** A proposed text update for the page. Humans apply it: the agent does not write to Confluence.
