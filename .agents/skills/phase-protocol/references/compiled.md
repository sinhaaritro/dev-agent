# COMPILED - COMPILE (reference checklist)

Load after the approval step (drafted.md section 5) for Lanes B and A. **Read-only - no file edits.** A session that produced an approved spec MUST stop here; implementation always runs in a new session.

## 1. Why this step exists

Approval already produced Step 1 of the spec-first lifecycle: promoted spec plus its task files. Coding in the same session defeats spec-first separation. The compile step makes the split mandatory.

## 2. Compile STOP rules

- Never open `references/building.md`.
- Never start a build (no source edits, no `Status: BUILDING`) on any spec.
- Never create or edit source files.
- Never draft a new plan in this session.
- A spec promoted under an autonomous resolution compiles the same way (to `Status: COMPILED`); its `## 6. Gates` entry is marked autonomous and it records no topic decisions until a human clears that mark.

## 3. Compile the spec

1. Run the engine compile:
   `python .agents/scripts/devagent/main.py spec compile specs/<NNN>-SPEC-<slug>.md`
   This is the `COMPILED` compile: it reads the spec's section 5 Tasks & Outcomes, writes one task file per task (`NNN-TASK-<NN>-<slug>.md`), writes `NNN-APPROVALS-<slug>.json` (pre-approving every verify command), and stamps `Status: COMPILED` on the spec header (durable). Exit 0 = compiled; non-zero prints the failure — fix the gap first.
2. If the engine is unavailable (dogfooding before it ships), write the task files manually and label the compile MANUAL.

## 4. Exit criteria

- [ ] Task files exist for every section 5 task (engine- or manual-written)
- [ ] Spec header carries `Status: COMPILED` (engine); a manual compile notes the absence
- [ ] No source edits made; no build started; no `Status: BUILDING` set
- [ ] Final reply uses the 4-block schema with `[STATUS: COMPILED | ...]` and states the exact prompt for the next session

## 5. Lane C/D note

Lanes C and D have no plan or approval step, so no compile applies. Never look for or create a compiled spec for C/D tasks.
