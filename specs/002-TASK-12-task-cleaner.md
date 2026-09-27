# TASK 002-12 — `task-cleaner` scope / `specs/temp` fate

## Role & rules
Implement ONLY this task. Obey the given signatures. Do not plan, do not touch files you
don't Own, do not commit.

## Project overview
Dev-agent: a portable meta-framework that drives coding tasks through a phase protocol
(1-Plan → 2-Handoff → 3-Build → 4-Review → 5-Done).

## Task
Update `clean.py` + the skill to the new world: evidence lives in the **task files** under
`specs/`, the gate log lives in the **spec's `Gates:` section**, and approvals are a
**gitignored** per-spec file. So `specs/temp/` now holds only draft-phase scratch
(`draft-plan.md`, `active-task.md`) and is safe to purge on approval. Define and implement:
purge everything in `specs/temp/` except `.gitignore`; never touch `specs/` group files,
`docs/`, or `BACKLOG.md`; report `purged: N, preserved: M`.

### Progress
- [x] retire gate-log.md / verify-state.json / approvals.json as scratch concepts
- [x] implement the new purge scope + dry-run/status
- [x] keep the scratchpad guard (refuse targets at/above repo root)
- [x] add cases to tests/test_clean.py

## Owns
- `.agents/skills/task-cleaner/scripts/clean.py`
- `.agents/skills/task-cleaner/SKILL.md`
- `tests/test_clean.py`

## Reads / Context (read-only)
- `specs/002-SPEC-subagent-task-files-full-plan.md`
- `.agents/skills/verification-runner/scripts/verify.py`

## Skills to use
- task-cleaner

## Upstream interfaces
```python
def clean(temp_dir: Path, preserve: list[str], dry_run: bool) -> tuple[list[str], list[str]]
```

## Verification
```bash
python -m unittest tests.test_clean -v
```
**Expect:** `OK`
