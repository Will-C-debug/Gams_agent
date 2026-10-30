---
description: Implement a Jira issue in the GAMS model - plan, edit, compile, test, draft the PR description
agent: gams-developer
argument-hint: "<JIRA-KEY, e.g. UC-123>"
---

Implement the Jira issue given after the command. If no key was given, take it from the branch name, or ask.

1. **Read.** Read the issue, its acceptance criteria, comments and linked Confluence spec (`atlassian-context` skill). Search for closely related issues in the same project.
2. **Plan, then stop for approval.** Propose a plan: files, equations and data affected, the test case to add, and the verification steps. **Stop and wait for my approval.**
3. **Implement.** After approval, implement with minimal diffs and compile after each edit.
4. **Verify.** Run the relevant allowlisted cases and explain every baseline difference.
5. **Draft the PR description:** summary, Jira key, an acceptance-criteria checklist with evidence, the verification log, and the Confluence pages that need updates.
