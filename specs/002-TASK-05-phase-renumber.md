# TASK 002-05 — phase renumber + single `Status:` across `.agents`, `AGENTS.md`, `MAP.md`

## Role & rules
Implement ONLY this task. Obey the given signatures. Do not plan, do not touch files you
don't Own, do not commit.

## Project overview
Dev-agent: a portable meta-framework that drives coding tasks through a phase protocol
(1-Plan → 2-Handoff → 3-Build → 4-Review → 5-Done).

## Task
Rename the phases everywhere to the canonical `1-Plan`, `1.5-Vetting`, `2-Handoff`,
`3-Build`, `4-Review`, `4.5-Sign-off`, `5-Done`, and replace the `Phase:` header field with a
single `Status:` receipt field. Apply across `.agents/rules/system.md`,
`.agents/skills/phase-protocol/*`, `.agents/skills/auto-router/*`,
`.agents/skills/spec-builder/SKILL.md`, `.agents/skills/verification-runner/SKILL.md`,
`.agents/skills/task-cleaner/SKILL.md`, and `AGENTS.md`; then regenerate `.agents/MAP.md`. Do
not do the run-contract or branch work (later tasks).

### Progress
- [x] grep the old names (1.5-Handoff, 2-Build, 3-Review, `Phase:`) across the owned files
- [x] replace with the canonical names / a single `Status:`
- [x] update phase-protocol reference pointers if renamed
- [x] regenerate MAP.md
- [x] leave zero `Phase:` occurrences

## Owns
- `.agents/rules/system.md`
- `.agents/skills/phase-protocol/SKILL.md`
- `.agents/skills/phase-protocol/references/plan.md`
- `.agents/skills/phase-protocol/references/handoff.md`
- `.agents/skills/phase-protocol/references/build.md`
- `.agents/skills/phase-protocol/references/review.md`
- `.agents/skills/auto-router/SKILL.md`
- `.agents/skills/auto-router/references/lane-matrix.md`
- `.agents/skills/spec-builder/SKILL.md`
- `.agents/skills/verification-runner/SKILL.md`
- `.agents/skills/task-cleaner/SKILL.md`
- `AGENTS.md`
- `.agents/MAP.md`

## Reads / Context (read-only)
- `specs/002-SPEC-subagent-task-files-full-plan.md`

## Skills to use
- phase-protocol
- map-generator

## Upstream interfaces
(none)

## Verification
```bash
bash -c 'test -z "$(grep -rn "Phase:" .agents AGENTS.md)" && echo PHASE-AUDIT-OK'
```
**Expect:** `PHASE-AUDIT-OK`
