# TASK 002-15 — update the docs reference series (001–007 + decision-records)

## Role & rules
Implement ONLY this task. Obey the given signatures. Do not plan, do not touch files you
don't Own, do not commit.

## Project overview
Dev-agent: a portable meta-framework that drives coding tasks through a phase protocol
(1-Plan → 2-Handoff → 3-Build → 4-Review → 5-Done).

## Task
Bring the existing reference series onto the new design (they still describe the old phases,
gates, circuit breaker, and worktree model):
- `001-framework-overview.md` — new phase sequence + single `Status:`.
- `003-triage-lane-taxonomy-and-escalation.md` — session type → run mode; `ESCALATED` vs
  `ABORTED`; escalation stops the spec's branch, batch continues.
- `004-phases-gates-and-autonomy.md` — 1-Plan…5-Done, the `vetting`/`signoff`/`review_revision`
  flags, run modes, autonomy.
- `005-docs-architecture-and-spec-lifecycle.md` — the `NNN-SPEC/TASK/REPORT/APPROVALS/ESCALATION`
  group, task-file compile, `purge`/`sync`, no auto-purge, `BACKLOG.md`.
- `006-verification-and-circuit-breakers.md` — root-cwd, hash evidence, `doctor`, run-to-exhaustion
  (no "3 consecutive" breaker), consolidated escalation.
- `007-parallel-execution-and-worktrees.md` — branch-per-spec, ownership lease, sole-writer.
- `002-skill-discovery-and-indexing.md`, `decision-records.md` — touch only where they reference
  the changed model.

### Progress
- [ ] update 001 (phases + Status)
- [ ] update 003 (run mode + escalation)
- [ ] update 004 (phases, gates, autonomy)
- [ ] update 005 (spec lifecycle + group files)
- [ ] update 006 (verification + exhaustion)
- [ ] update 007 (branch model)
- [ ] sweep 002 + decision-records for stale references

## Owns
- `docs/001-framework-overview.md`
- `docs/002-skill-discovery-and-indexing.md`
- `docs/003-triage-lane-taxonomy-and-escalation.md`
- `docs/004-phases-gates-and-autonomy.md`
- `docs/005-docs-architecture-and-spec-lifecycle.md`
- `docs/006-verification-and-circuit-breakers.md`
- `docs/007-parallel-execution-and-worktrees.md`
- `docs/decision-records.md`

## Reads / Context (read-only)
- `specs/002-subagent-task-files-phase-renumbering-and-full-plan-execution.md`
- `docs/lifecycle.md`
- `docs/run-contract.md`
- `docs/verification.md`

## Skills to use
- map-generator

## Upstream interfaces
(none)

## Verification
```bash
bash -c 'grep -q "1-Plan" docs/004-phases-gates-and-autonomy.md && test -z "$(grep -rln "1\.5-Handoff\|Phase: 2-Build\|Phase: 3-Review" docs/)" && echo REFDOCS-OK'
```
**Expect:** `REFDOCS-OK`
