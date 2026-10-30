# Evaluation harness

This measures how well the gams-sme agent performs, and gates changes to the pack, gams-tools or the model in use (plan §11).

| Set | Location | What it measures | Grader |
|---|---|---|---|
| Seeded defects | `seeded_defects/uc_small.yaml` (12 cases on `models/uc_small`) | Recall of known defects, severity agreement, extra findings for SME review | `runner/grade_review.py` |
| Knowledge Q&A | `knowledge_qa/questions.yaml` (12 seed questions) | Correct GAMS 53/CPLEX facts; every option named exists in the installed release | `runner/grade_qa.py` |
| Context tasks | `context_tasks/ctx-*/` | Jira/Confluence traceability, conflict reporting, resisting planted instructions, no write tools | `runner/grade_context.py` |
| Historical PRs, coding tasks, diagnosis tasks | to build in Phase 3 from GO/UC/IHP1/INTRA1/CES history | See plan §11 | SME rubric + gams-tools checks |

## The base model

`models/uc_small` is a small unit commitment MIP: 3 units, 8 hours, with reserve, ramping, minimum up/down time and start-up costs.

- **Optimum:** 78,640.
- **System lambda:** `[55, 55, 28, 28, 28, 28, 28, 18]`. In hour 1 it is 55 because coal1's ramp limit binds.
- **Option file:** `cplex.opt` sets `solvefinal 1` explicitly, so marginals exist on GAMS 53 and 54.

## Seeded defects are verified, not assumed

`runner/verify_seeds.py` compiles and runs the base model and every seeded variant with gams-tools. It records each defect's observable effect in `seeded_defects/effects.json`:

| Case | Defect | Observed effect |
|---|---|---|
| uc-001 | initial status dropped from commitment logic | objective 78,640 → 82,640; lambda h1 55 → 18 |
| uc-002 | ramp-up ignores initial output | integer infeasible |
| uc-003 | reserve from `pmin` instead of `pmax` | integer infeasible |
| uc-004 | start-up cost missing from objective | objective → 76,540 |
| uc-005 | model list omits `reserve` | objective → 76,960; `symbol_xref` flags the equation |
| uc-006 | solve status no longer checked | none on this data (code-reading defect) |
| uc-007 | minimum up-time window off by one | none on this data (code-reading defect) |
| uc-008 | lambda sign flipped | lambda negative |
| uc-009 | `solvefinal 0` | lambda NA in every hour |
| uc-010 | deprecated, loose `mipgap 0.05` overrides `optCR = 0` | deprecated option reported by GAMS |
| uc-011 | unit label typo in data | compilation errors 170/141/257 |
| uc-012 | `pmin > pmax` for ct1 | integer infeasible |

The committed `effects.json` was produced with the GAMS 54.6.1 demo, because the demo license bundled with 53.5.1 had expired. **Regenerate it with the licensed GAMS 53 build in Phase 0:**

```bash
GAMS_SYSDIR=/path/to/gams53 python evals/runner/verify_seeds.py
```

## Running an eval

```bash
pip install -e "mcp/gams-tools[test]"

# 1. Prepare workspaces (git repos with the pack; base on main, seeded change on a branch)
python evals/runner/run_evals.py --set seeded --out evals/results/<run>

# 2a. Run the agent from Copilot CLI (verify flags for your CLI version), or
python evals/runner/run_evals.py --set seeded --out evals/results/<run> \
    --agent-cmd 'copilot --agent gams-reviewer -p "{prompt}" --allow-all-tools'
# 2b. ...open each workspace in VS Code, run /gams-review, and save the answer as evals/results/<run>/<case>.md

# 3. Grade
python evals/runner/grade_review.py --results evals/results/<run>
GAMS_SYSDIR=/path/to/gams53 python evals/runner/grade_qa.py --results evals/results/<run>
python evals/runner/grade_context.py --results evals/results/<run>
```

Record the model, pack version and gams-tools version with every run (plan §11). `pytest evals/tests` checks the harness itself and runs in CI.
