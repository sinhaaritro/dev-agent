tags: [handoff, lifecycle, sdsc, two-step]

# 008: Post-Approval Handoff Guard

Status: APPROVED | Phase: 2-Build

## 1. Goal & Context

The two-step lifecycle (spec 007) still lets the spec-producing session
proceed in-session to Build - 007 D1 says "either proceed in-session to
`references/build.md`, or hand the spec to a separate implementing agent/session".
The birthday-tracker demo showed the agent coding immediately after approval,
defeating spec-first separation. This change makes handoff **mandatory**: a
session that produced an approved spec must stop at a new **Phase 1.5 (Handoff)**,
and implementation runs only in a new session that reads the promoted spec.
Applies to Lanes B and A (the two spec-producing lanes); Lanes C and D have no
plan/approval step, so no guard applies there (noted, not enforced).

## 2. Architectural Decisions & Trade-offs

- **D1. Mandatory handoff phase (amends 007 D1).** Remove the in-session
  proceed option from `plan.md` section 5; add a new `Phase 1.5 - Handoff`
  reference checklist that is read-only and forbids coding. Trade-off: one extra
  session per spec-producing task vs. guaranteed spec-first separation; spec
  sessions are cheap and the separation is the point of the lifecycle.
- **D2. Engine-recorded handoff + durable marker.** A new `handoff` mode in
  `promote_spec.py` validates the handoff (spec exists with `Status: APPROVED`;
  Lane A requires at least one ADR whose `Source:` points at the spec; Lane B
  allows zero since ADRs are optional there), writes `docs/temp/handoff.md`
  (ephemeral scratchpad), and stamps `Handoff: <YYYY-MM-DD>` onto the spec's
  status header (durable). Trade-off: one more engine mode and a header edit vs.
  an enforceable, verifiable handoff that a new session can confirm.
- **D3. Lane-scoped guard.** Enforced for B and A only. C and D are noted as
  approval-free so future agents never look for a handoff there.

## 3. Affected Files & Scope

- Created: .agents/skills/phase-protocol/references/handoff.md
- Modified: .agents/skills/phase-protocol/references/plan.md
- Modified: .agents/skills/phase-protocol/references/build.md
- Modified: .agents/skills/phase-protocol/SKILL.md
- Modified: .agents/skills/spec-builder/scripts/promote_spec.py
- Modified: .agents/skills/spec-builder/SKILL.md
- Modified: .agents/rules/system.md
- Modified: AGENTS.md
- Modified: docs/architecture/000-modular-agent-orchestration-v7.md
- Modified: engine `find_root` markers in all six `.agents/skills/*/scripts/*.py` (accept `AGENTS.md` as the repo-root marker alongside `AGENTS.md` - discovered during production when the root file was renamed; `promote_spec.py` already patched)
- Deleted: none

## 4. Actionable TODO Checklist

- [ ] Step 1: Create `.agents/skills/phase-protocol/references/handoff.md` (read-only checklist, STOP rules, handoff message, `[STATUS: 1.5-Handoff | ...]`).
- [ ] Step 2: Add the `handoff` mode to `promote_spec.py` (validate APPROVED + Lane A ADR source check, write `docs/temp/handoff.md`, stamp `Handoff:` on the spec header, `--handoff-dir` / `--dry-run`, idempotent re-run).
- [ ] Step 3: Edit `plan.md` section 5 (mandatory handoff, remove in-session proceed) and `build.md` (new-session only, verify the spec has a `Handoff:` marker).
- [ ] Step 4: Edit `phase-protocol/SKILL.md` (phase chain Plan -> 1.5-Handoff -> Build -> Review, read-only Handoff posture, C/D note).
- [ ] Step 5: Edit `spec-builder/SKILL.md`, `.agents/rules/system.md` section 2 step 4, `AGENTS.md` boot step 6.
- [ ] Step 6: Edit `docs/architecture/000-modular-agent-orchestration-v7.md` (section 10 diagram inserts the Phase 1.5 node; section 12 harness table).
- [ ] Step 7: Sweep the six engine scripts' `find_root` markers to accept `AGENTS.md` as the repo-root marker (all `.agents/skills/*/scripts/*.py`; `promote_spec.py` already patched) - required because the root file is now `AGENTS.md`.
- [ ] Step 8: Test the `handoff` mode in a sandbox (happy path, Lane A missing-ADR rejection, idempotent re-run, bad path).
- [ ] Step 9: Regenerate `MAP.md`, verify, `git status` scope check.

## 5. Verification Commands

- Build Command: python .agents/skills/spec-builder/scripts/promote_spec.py handoff --help
- Test Command: python .agents/skills/spec-builder/scripts/promote_spec.py handoff <spec> --lane A --handoff-dir <sandbox> (sandbox run)
- Test Command: python .agents/skills/map-generator/scripts/generate_map.py

## 6. Rollback Strategy

All modified files revert via `git checkout`; the created `handoff.md` reference
and any `handoff` engine additions are deleted. Filed ADRs are protected files
and are never edited (system.md section 3). If verification fails 3 consecutive
times, stop and report per the circuit breaker.