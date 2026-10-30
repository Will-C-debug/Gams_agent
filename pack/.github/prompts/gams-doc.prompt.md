---
description: Generate model documentation in math notation and report drift against the model's Confluence page
agent: formulation-auditor
argument-hint: "<entry point>"
---

Document the model behind the entry point given after the command, following the `formulation-docs` skill:

- a notation table (symbol, meaning, units, source)
- every equation in the solved model as math, with `file:line`
- the objective
- data sources
- outputs

Then find the model's Confluence page (`atlassian-context` skill) and write a doc-drift report: what the page says that the code doesn't do, and the reverse. Include the page's last-updated date vs. the last commit to the model. Finish with proposed page text for a human to apply.
