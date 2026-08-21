# Chronos commit notes

This directory keeps a short Markdown handoff for every meaningful project
commit. The Git commit remains the source of truth; these notes capture the
reasoning, verification, and follow-up work that are useful to both partners.

## Naming convention

Use:

```text
YYYY-MM-DD-<short-scope>.md
```

Example:

```text
2026-08-21-sqlite-node-store.md
```

If a second note uses the same scope on the same day, append `-2`, `-3`, and so
on.

## Workflow

1. Copy `TEMPLATE.md` and rename it before creating the related Git commit.
2. Record the objective, implementation summary, tests, and known limitations.
3. Replace `PENDING` with the final short commit hash after committing.
4. Keep one note per meaningful commit; documentation-only typo fixes do not
   need separate notes.
5. Never include secrets, credentials, access tokens, or private datasets.

## Suggested commit sequence

Prefer small, independently verifiable commits:

```text
chore(repo): reconcile final-submission baseline
feat(core): add atomic incremental Chronos-H commits
feat(storage): persist content-addressed nodes and commits
feat(proofs): add verifiable Merkle diff certificates
feat(api): expose project, commit, diff, and checkout workflows
feat(ui): add the final Chronos workspace
perf(eval): add reproducible final benchmark suite
docs(final): add final report and demo instructions
fix(release): close final integration defects
```
