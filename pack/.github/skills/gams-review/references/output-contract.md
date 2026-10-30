# Review output contract

Use this structure for every full review: from `/gams-review`, from the `gams-reviewer` agent, and for PR summaries.

```markdown
## Summary
<What changed, overall risk (low/medium/high), the top 3 issues.>

## Findings
| ID | Severity | Category | Location | Finding | Recommendation | Confidence | Verified by |
|---|---|---|---|---|---|---|---|
| R1 | Major | Formulation | `models/uc/model.inc:142` | ... | ... | High | gams_run uc-small: rows 412 → 388 |

## Requirements traceability (<JIRA-KEY>)
| Acceptance criterion | Status | Evidence |
|---|---|---|
| AC1: ... | covered / partially / not covered / not testable | file:line, test case |

## Spec traceability (<Confluence page title>, v<version>)
| Spec element | Code | Status |
|---|---|---|
| (3.2) capacity limit | `maxOut(g,t)` model.inc:40 | matches / differs / missing in code / extra in code |

## Verification log
- gams_compile models/uc/main.gms: ok (GAMS 53.x.y)
- gams_run uc-small: Optimal, objective 78640, baseline equal
- option_validate models/uc/cplex.opt: 1 warning (mipgap deprecated)

## Not checked
- <Everything not verified, and why.>
```

## Field rules

- **Severity.**
  - Blocker: wrong results or failure likely.
  - Major: wrong results in some cases, a significant performance or numerical risk, or a standards violation with downstream impact.
  - Minor: maintainability.
  - Nit: style.
  - Question: intent unclear.
- **Category.** Formulation, Data, Solve handling, Solver config, Performance, Numerics, Structure, Security, Testing, Traceability.
- **Location.** Repo-relative `file:line`, the innermost file for include files.
- **Recommendation.** A concrete change, preferably a small code snippet.
- **Confidence.** High / Medium / Low (see the review skill).
- **Verified by.** The tool and case that showed it, "code reading", or "hypothesis".

## Inline PR comments (Copilot code review)

`[<Severity>][<Category>] <finding>. <recommendation>. (Confidence: <H/M/L>; verified by: <...>)`
