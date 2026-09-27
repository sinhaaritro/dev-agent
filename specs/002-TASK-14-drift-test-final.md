# TASK 002-14 — drift test + full canonical verification

## Role & rules
Implement ONLY this task. Obey the given signatures. Do not plan, do not touch files you
don't Own, do not commit.

## Project overview
Dev-agent: a portable meta-framework that drives coding tasks through a phase protocol
(1-Plan → 2-Handoff → 3-Build → 4-Review → 5-Done).

## Task
Add `tests/test_drift_phases.py` asserting the canonical sets appear exactly and the old ones
are gone: phases `1-Plan`, `1.5-Vetting`, `2-Handoff`, `3-Build`, `4-Review`, `4.5-Sign-off`,
`5-Done`; statuses `DRAFTED/COMPILED/BUILDING/BUILT/REVIEWED/COMPLETED/PLAN_REVISION_REQUIRED/
REVIEW_REVISION_REQUIRED/ESCALATED/ABORTED`; no `Phase:` field; no `1.5-Handoff`/`2-Build`/
`3-Review`. Fill the `AGENTS.md` command placeholders with the canonical Build/Test/Lint
commands.

### Progress
- [x] write the drift test over `.agents`, `docs`, `README.md`, `AGENTS.md`
- [x] fill AGENTS.md commands
- [x] run the full suite + lint

## Owns
- `tests/test_drift_phases.py`
- `AGENTS.md`

## Reads / Context (read-only)
- `specs/002-SPEC-subagent-task-files-full-plan.md`

## Skills to use
- verification-runner

## Upstream interfaces
(none)

## Verification
```bash
python .agents/skills/verification-runner/scripts/verify.py run --command "python -m unittest discover -s tests -v" --expect "OK" --task T14 --lane A
```
**Expect:** `OK`

<!-- VERIFY:EVIDENCE:START -->
```json
{
  "command": "python -m unittest discover -s tests -v",
  "exit": 0,
  "expect": "OK",
  "matched": true,
  "at": "2026-09-27T04:24:58",
  "output_sha256": "bef3dd45430a7701401fa25e3ac91ea16dc0d829f889c2f9341f368ab0ff050c",
  "files": {
    "tests/test_drift_phases.py": "da4b3a3246501639e03746b63dc59bee70b53bd9fb5b4b4ba824aaff6e88f67d",
    "AGENTS.md": "5b94ff3370bbde3a801da6bc3b441593f39728b88a9a4b67e715e1b03bc60a7a"
  }
}
```
<!-- VERIFY:EVIDENCE:END -->
