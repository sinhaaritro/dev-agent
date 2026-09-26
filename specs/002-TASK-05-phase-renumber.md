# TASK 002-05 — phase renumber + single `Status:` across `.agents`, `AGENTS.md`, `MAP.md`

role & rules
  You are a coder. Implement ONLY this task. Obey the given signatures.
  Do not plan, do not touch files you don't Own, do not commit.

project overview
  Dev-agent: a portable meta-framework that drives coding tasks through a phase protocol
  (1-Plan → 2-Handoff → 3-Build → 4-Review → 5-Done).

this task
  05 phase renumber

task
  Rename the phases everywhere to the canonical `1-Plan`, `1.5-Vetting`, `2-Handoff`,
  `3-Build`, `4-Review`, `4.5-Sign-off`, `5-Done`, and replace the `Phase:` header field with
  a single `Status:` receipt field. Apply across `.agents/rules/system.md`,
  `.agents/skills/phase-protocol/*` (SKILL + all `references/*`), `.agents/skills/auto-router/*`,
  `.agents/skills/spec-builder/SKILL.md`, `.agents/skills/verification-runner/SKILL.md`,
  `.agents/skills/task-cleaner/SKILL.md`, and `AGENTS.md`; then regenerate `.agents/MAP.md`.
  Do not do the run-contract or branch work (later tasks).

  progress                      (this task only — the owning coder updates it)
    - grep for the old names (1.5-Handoff, 2-Build, 3-Review, "Phase:") across the owned files
    - replace with the canonical names / single Status
    - update the phase-protocol reference filenames/pointers if renamed
    - regenerate MAP.md
    - leave no `Phase:` occurrence behind

Owns
  .agents/rules/system.md
  .agents/skills/phase-protocol/SKILL.md
  .agents/skills/phase-protocol/references/plan.md
  .agents/skills/phase-protocol/references/handoff.md
  .agents/skills/phase-protocol/references/build.md
  .agents/skills/phase-protocol/references/review.md
  .agents/skills/auto-router/SKILL.md
  .agents/skills/auto-router/references/lane-matrix.md
  .agents/skills/spec-builder/SKILL.md
  .agents/skills/verification-runner/SKILL.md
  .agents/skills/task-cleaner/SKILL.md
  AGENTS.md
  .agents/MAP.md

Reads/Context                     (read-only)
  specs/002-subagent-task-files-phase-renumbering-and-full-plan-execution.md

Skills to use
  - phase-protocol
  - map-generator

upstream interfaces
  (none)

verification
  bash -c 'test -z "$(grep -rn "Phase:" .agents AGENTS.md)" && echo PHASE-AUDIT-OK'
  Expect: PHASE-AUDIT-OK
