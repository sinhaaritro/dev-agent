# PHASE 1.5 - HANDOFF (reference checklist)

Load after the approval step (plan.md section 5) for Lanes B and A. **Read-only - no file edits.** Spec 008 D1: a session that produced an approved spec MUST stop here; implementation always runs in a new session.

## 1. Why this phase exists

Approval already produced Step 1 of the spec-first lifecycle: promoted spec plus ADRs. Coding in the same session defeats spec-first separation. Phase 1.5 makes the split mandatory.

## 2. Handoff STOP rules

- Never open `references/build.md`.
- Never set `Phase: 2-Build` on any spec.
- Never create or edit source files.
- Never draft a new plan in this session.
- If the spec is `Status: PROVISIONAL - AUTONOMOUS DEFAULT`, the handoff still happens, but implementation waits until a human clears the tag (no ADRs exist for autonomous defaults).

## 3. Record the handoff

1. Run the engine record:
   `python .agents/skills/spec-builder/scripts/promote_spec.py handoff docs/specs/<NNN>-<slug>.md --lane <B|A> [--handoff-dir <sandbox>] [--dry-run]`
   Validation: spec exists with `Status: APPROVED`; Lane A requires >=1 ADR whose `Source:` points at the spec; Lane B allows zero. Exit 0 writes `docs/temp/handoff.md` (ephemeral) and stamps `Handoff: <YYYY-MM-DD>` on the spec header (durable). Exit 1 prints the failure — fix the gap (e.g., file the missing ADR) first.
2. If the engine is unavailable (dogfooding before it ships), write `docs/temp/handoff.md` manually and label it MANUAL.

## 4. Exit criteria

- [ ] `docs/temp/handoff.md` exists (engine- or manual-written)
- [ ] Spec header carries `Handoff: <YYYY-MM-DD>` (engine); a manual handoff notes the absence
- [ ] No file edits made; no build started; no `Phase: 2-Build` set
- [ ] Final reply uses the 4-block schema with `[STATUS: 1.5-Handoff | ...]` and states the exact prompt for the next session

## 5. Lane C/D note

Lanes C and D have no plan or approval step, so no handoff applies. Never look for or create a handoff record for C/D tasks.
