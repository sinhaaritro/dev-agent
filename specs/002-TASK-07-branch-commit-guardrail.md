# TASK 002-07 — branch-per-spec, commit-terminal, never-merge guardrail

## Role & rules
Implement ONLY this task. Obey the given signatures. Do not plan, do not touch files you
don't Own, do not commit.

## Project overview
Dev-agent: a portable meta-framework that drives coding tasks through a phase protocol
(1-Plan → 2-Handoff → 3-Build → 4-Review → 5-Done).

## Task
Document the build/commit model in `system.md` and the phase references:
- specs are authored on `main`; a run creates **one branch per spec off `main` (+ worktree)**
  and **never edits `main`**; the worktree is a sibling directory named `<repo>-<worktree>`,
  never inside the repo;
- **commit is terminal** — at spec end the run commits on its branch and stamps `COMPLETED`
  immediately; there are no post-commit checks;
- **hard guardrail: never merge or push to the default/release branch** — merging is
  human-only, even for headless runs;
- on failure the spec parks as `ESCALATED` (not `ABORTED`) and the batch continues.

### Progress
- [x] add the branch rule + commit-terminal to build.md
- [x] add the never-merge guardrail to system.md
- [x] note `ESCALATED` vs `ABORTED` and batch-continue in build.md/review.md

## Owns
- `.agents/rules/system.md`
- `.agents/skills/phase-protocol/references/build.md`
- `.agents/skills/phase-protocol/references/review.md`

## Reads / Context (read-only)
- `specs/002-SPEC-subagent-task-files-full-plan.md`

## Skills to use
- phase-protocol

## Upstream interfaces
(none)

## Verification
```bash
bash -c 'grep -qi "never merge" .agents/rules/system.md && grep -qi "commit is terminal" .agents/skills/phase-protocol/references/build.md && echo BRANCH-GUARD-OK'
```
**Expect:** `BRANCH-GUARD-OK`
