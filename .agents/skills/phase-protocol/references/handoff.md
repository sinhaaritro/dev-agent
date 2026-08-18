# PHASE 1.5 - HANDOFF (reference checklist)

Load after the approval step (plan.md section 5) for Lanes B and A. **Read-only
posture - no file edits.** Spec 008 D1: a session that produced an approved
spec MUST stop here; implementation always runs in a new session.

## 1. Why this phase exists

Approval already produced Step 1 of the spec-first lifecycle: the promoted spec
plus its ADRs. Coding in the same session defeats spec-first separation (the
birthday-tracker demo did exactly that). Phase 1.5 makes the split mandatory.

## 2. Handoff STOP rules

- Never open `references/build.md`.
- Never set `Phase: 2-Build` on any spec.
- Never create or edit source files.
- Never draft a new plan in this session.
- If the spec is `Status: PROVISIONAL - AUTONOMOUS DEFAULT`, the handoff still
  happens, but implementation waits until a human clears the tag (no ADRs exist
  for autonomous defaults).

## 3. Record the handoff

1. Run the engine record:
   `uv run python .agents/skills/spec-builder/scripts/promote_spec.py handoff docs/specs/<NNN>-<slug>.md --lane <B|A> [--handoff-dir <sandbox>] [--dry-run]`
   The engine validates: the spec exists with `Status: APPROVED`; Lane A
   requires at least one ADR whose `Source:` points at the spec; Lane B allows
   zero (ADRs optional there). Exit 0 writes `docs/temp/handoff.md` (ephemeral)
   and stamps `Handoff: <YYYY-MM-DD>` on the spec's status header (durable).
   Exit 1 prints the validation failure - fix the gap (e.g. file the missing
   ADR) before calling it a handoff.
2. If the engine is unavailable (e.g. the phase is being dogfooded before the
   engine ships), write `docs/temp/handoff.md` manually and label it MANUAL.

## 4. Exit criteria

- [ ] `docs/temp/handoff.md` exists (engine- or manual-written)
- [ ] Spec header carries `Handoff: <YYYY-MM-DD>` (engine); a manual handoff
      notes the absence instead
- [ ] No file edits made; no build started; no `Phase: 2-Build` set
- [ ] Final reply uses the 4-block schema with `[STATUS: 1.5-Handoff | ...]`
      and states the exact prompt for the next session

## 5. Lane C/D note

Lanes C and D have no plan or approval step, so no handoff applies there
(spec 008 D3). Never look for or create a handoff record for C/D tasks.