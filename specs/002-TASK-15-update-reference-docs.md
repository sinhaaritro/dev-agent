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
- [x] update 001 (phases + Status)
- [x] update 003 (run mode + escalation)
- [x] update 004 (phases, gates, autonomy)
- [x] update 005 (spec lifecycle + group files)
- [x] update 006 (verification + exhaustion)
- [x] update 007 (branch model)
- [x] sweep 002 + decision-records for stale references

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
- `specs/002-SPEC-subagent-task-files-full-plan.md`
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

<!-- VERIFY:EVIDENCE:START -->
```json
{
  "command": "grep -q \"1-Plan\" docs/004-phases-gates-and-autonomy.md && test -z \"$(grep -rln \"1\\.5-Handoff\\|Phase: 2-Build\\|Phase: 3-Review\" docs/)\" && echo REFDOCS-OK",
  "exit": 0,
  "expect": "REFDOCS-OK",
  "matched": true,
  "at": "2026-09-27T06:06:52",
  "output_sha256": "94fdf3132de0643f510ac1879d29747233412ef8183da13ec60a6c30ae61d9ef",
  "files": {
    "docs/001-framework-overview.md": "c109c065f72430d8e9e6d2119298956a188d77cd794957535e3e39fbdbaf3672",
    "docs/002-skill-discovery-and-indexing.md": "06320ea9cf13ac3498d4f9670c675546de9ff7372f10c90594124e82cf08369d",
    "docs/003-triage-lane-taxonomy-and-escalation.md": "1f76de570196f822a886a95881fcf5698da72e6a32b1fb7a3c55e1f4c2d4b52e",
    "docs/004-phases-gates-and-autonomy.md": "87e51651a6d35743ad25df8687b78c60fc34502774de35b5c9eb54cf27f83904",
    "docs/005-docs-architecture-and-spec-lifecycle.md": "9345956c892eafe6977e0c522c6e80d247d46dfc819e24a3a0aa66b059ee7f29",
    "docs/006-verification-and-circuit-breakers.md": "5853a9de761c14c1022994c6910ff0de2387445e517e7469807d8f0128dffb74",
    "docs/007-parallel-execution-and-worktrees.md": "eb9a18155a1dcf7168f4fbd845ad6f6fd52d535ffa3c11af4076cc6904455e3b",
    "docs/decision-records.md": "96b4d4281f262bfd2d1daf845174a36925094bff764d4a15cf0f066497ae0faf"
  }
}
```
<!-- VERIFY:EVIDENCE:END -->
