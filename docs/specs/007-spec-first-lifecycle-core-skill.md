# 007: Spec-First Lifecycle — Two-Step Approval/Implementation

Status: APPROVED | Phase: 2-Build

> **Derived from:** user requirement (2026-08-18): split plan approval from implementation; on approval, move the draft to a permanent spec in `docs/specs/` and write ADRs for any architectural decision at any lane; the spec is the contract the implementing agent builds from. Decisions locked with the user: two-step lifecycle, ADR rule by decision-not-lane, ADRs agent-drafted + engine-filed, spec status stays `APPROVED` tracked via the `Phase:` field, Lane B also promotes an abbreviated spec.

## 1. Goal & Context

The framework currently promotes the draft plan to `docs/specs/` only at Phase 3-Review, after build and verification (000 §10: the spec is born at the human acceptance gate). This makes the spec a post-hoc record of what was built. Teams that want a spec-first workflow — approve the plan, receive a permanent spec plus ADRs, then hand implementation to a separate agent — cannot express it. This change splits approval from implementation into two explicit steps: **Step 1 (spec production)** approves the draft and promotes it to a permanent spec with its ADRs, then stops; **Step 2 (implementation)** is a separate session/agent that builds from the promoted spec and finalizes it.

## 2. Architectural Decisions & Trade-offs

- **D1. Two-step lifecycle (approval -> spec + ADRs; implementation separate).** The acceptance gate fires at the end of planning, not review. The promoted spec in `docs/specs/` becomes the working contract; `docs/temp/draft-plan.md` no longer drives the build. Trade-off: the spec can drift from the final implementation, so Phase 3-Review becomes a **finalize** step (drift check, checkbox sync, verification evidence) instead of the birth of the spec. Selected to support spec-first workflows and clean agent handoff.
- **D2. ADRs are triggered by the decision, not the lane.** Any architectural decision at any lane gets a permanent ADR in `docs/decisions/` — Lane A mandatory (one per spec §2 decision); Lane B optional (only if a gate or the task surfaces a schema/API/auth/dependency choice, since the abbreviated plan has no §2). Trade-off: more durable records to maintain vs. losing decisions from small tasks. Selected because decisions are durable knowledge regardless of task size.
- **D3. ADRs are agent-drafted and engine-filed.** The agent extracts each decision and drafts it against a new `references/adr-template.md`; the engine (`promote_spec.py adr` mode) validates the required sections, derives the next `NNN` by scanning `docs/decisions/`, refuses overwrite (ADRs are protected files, system.md §3), and files the record. Trade-off: the engine cannot auto-generate quality ADRs from prose §2, so agent judgment owns quality and the engine owns mechanics — the same division of labor as spec promotion.
- **D4. Spec status stays `APPROVED` through both steps; the `Phase:` field tracks progress.** No new statuses and no `normalize_status` change. The implementing agent sets `Phase: 2-Build` while working and Review sets `Phase: 3-Review`. Trade-off: the status value alone cannot distinguish "approved to build" from "built" — the `Phase:` header and fully-ticked §4 checklist carry that.
- **D5. Lane B also promotes.** An abbreviated spec (sections 1, 3, 4) is promoted at approval; ADRs are written only if a decision surfaces. Lane C and D are unchanged (no plan, no spec). Selected so every feature iteration can stop at a durable spec.

## 3. Affected Files & Scope

- Modified: .agents/skills/phase-protocol/references/plan.md
- Modified: .agents/skills/phase-protocol/references/build.md
- Modified: .agents/skills/phase-protocol/references/review.md
- Modified: .agents/skills/spec-builder/SKILL.md
- Modified: .agents/skills/spec-builder/scripts/promote_spec.py
- Modified: .agents/rules/system.md
- Modified: docs/architecture/000-modular-agent-orchestration-v7.md
- Created: .agents/skills/spec-builder/references/adr-template.md
- Deleted: none

## 4. Actionable TODO Checklist

- [x] Step 1: Create `.agents/skills/spec-builder/references/adr-template.md` (Title / Status: Accepted / Date / Context / Decision / Consequences / Source).
- [x] Step 2: Add the `adr` mode to `promote_spec.py` (validate sections, next NNN from `docs/decisions/`, slug from title, refuse overwrite, `--source` link, `--decisions-dir` for tests).
- [x] Step 3: Test `adr` + `promote` against a sandbox (`--specs-dir` / `--decisions-dir`).
- [x] Step 4: Edit phase-protocol `plan.md` (approval -> promote + ADRs -> handoff), `build.md` (work from `docs/specs/`, tick the spec's §4, set `Phase: 2-Build`), `review.md` (finalize step, no promotion).
- [x] Step 5: Edit `spec-builder/SKILL.md` (promotion at approval, ADR rule by decision-not-lane, Lane B promotes).
- [x] Step 6: Edit `.agents/rules/system.md` §2 step 4 wording.
- [x] Step 7: Edit `docs/architecture/000-modular-agent-orchestration-v7.md` (§4 lane table, §10 lifecycle diagram, §12 harness table).
- [x] Step 8: File ADRs for this spec via the new engine (self-hosting).
- [ ] Step 9: Regenerate `MAP.md`, verify, refresh the `dev-agent-test` machinery copy.

## 5. Verification Commands

- Build Command: python .agents/skills/spec-builder/scripts/promote_spec.py check docs/temp/draft-plan.md --lane A
- Test Command: python .agents/skills/spec-builder/scripts/promote_spec.py adr --help
- Test Command: python .agents/skills/spec-builder/scripts/promote_spec.py adr <draft-adr> --decisions-dir <sandbox> --source <spec> (sandbox run)
- Test Command: python .agents/skills/map-generator/scripts/generate_map.py

## 6. Rollback Strategy

All modified files revert via `git checkout` (they are committed or part of the working tree); the created `adr-template.md` and any filed ADRs are deleted. If verification fails 3 consecutive times, stop and report per the circuit breaker.