# Vetting (1.5) — plan review

Load only when the draft's frontmatter says `vetting: on` (default: on for a
Lane-A surface, off otherwise). This is an optional, token-costing gate; never
run it implicitly.

## Fresh context

Run the critic in a **new, read-only context** — a new subagent/session, not the
conversation that authored the plan. The critic must not see the author's
reasoning, alternatives, or chat history; it sees the artifacts:

- the draft (`specs/temp/draft-plan.md`),
- the files listed in section 4 (read-only),
- the topic docs the plan touches (`docs/<name>.md`),
- the Outcomes table and section-5 task blocks.

The critic never edits anything. It returns exactly one verdict.

## Checklist

1. **Goal.** Section 1 states the change and why; no hidden scope.
2. **Affected files.** Section 4 lists every file/contract the plan touches; no
   missing caller, schema, or config.
3. **Tasks.** Each task has Target Files, `Depends On`, `Verify`/`Expect`;
   the DAG is acyclic and ordered; oracles can actually fail.
4. **Area & skills.** In a multi-area project every task names a declared `Area:`;
   every declared/inherited skill resolves to an installed `SKILL.md` and is the
   right domain skill (never a framework-process skill as build guidance).
5. **Hazards.** Walk the task-authoring hazard checklist: caller closure on a
   signature change (every caller owned, or `Compatibility: shim` with a visible
   follow-up), shared mutable state, schema/migration atomicity, generated artifacts,
   cross-file renames, new lockfile ownership, build-tree collisions, duplicated
   sources of truth, shared fixtures, and name-keyed registries. Each hazard either
   stays inside one task or gets an explicit `Depends On` edge.
6. **Outcomes.** Every `R#` is delivered by at least one task and is observable.
7. **Risks.** Section 3 names the real risks/open questions, not boilerplate.
8. **Rollback.** Section 8 is executable for this change.
9. **Guardrails.** No protected file (`.env*`, lockfiles, `specs/*`) is edited
   without explicit human confirmation; no topic reversal is silent; a
   `shim` compatibility has a named removal task.

## Verdict

Return `PASS` or `BLOCK` with a numbered issue list. A block names the exact
section/task and what must change; no general advice.

Record the verdict:

```bash
python .agents/scripts/devagent/main.py spec vetting specs/temp/draft-plan.md \
    --verdict pass --note "no blocking issues"
python .agents/scripts/devagent/main.py spec vetting specs/temp/draft-plan.md \
    --verdict block --note "1. section 5 Task 2 has no Target Files"
```

A block sets `Status: PLAN_REVISION_REQUIRED` and returns to the authoring
loop. A later pass (or a human `--accept`) returns the draft to `DRAFTED`. The
**3rd block** stays `PLAN_REVISION_REQUIRED` and hands back to the human; do not
loop a fourth time. A human may record `--accept` to override a block as-is.

On a pass (or accept), continue to `references/compiled.md`. Never build in the
same session.
