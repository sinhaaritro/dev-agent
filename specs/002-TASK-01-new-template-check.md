# TASK 002-01 — new-template `check` + canonical `Status:` set

## Role & rules
Implement ONLY this task. Obey the given signatures. Do not plan, do not touch files you
don't Own, do not commit.

## Project overview
Dev-agent: a portable meta-framework that drives coding tasks through a phase protocol
(1-Plan → 2-Handoff → 3-Build → 4-Review → 5-Done).

## Task
Make `promote_spec.py check` validate the NEW spec template and retire the old
`### Task N:` / `Phase Gate:` structure check. `check` must:
- accept the new section set (0 Frontmatter, 1 Goal, 2 The Change, 3 Risks, 4 Affected Files,
  5 Tasks & Outcomes, 6 Gates, 7 Verification, 8 Rollback);
- parse the new §5 task shape (`### Task N:` with `Depends On:` and a `Verify:`/`Expect:`
  pair) and require at least one task;
- keep the Verify/Expect lint (no no-op command, no empty Expect, Expect must not appear in
  the Verify line);
- treat the canonical `Status:` set as `DRAFTED`, `COMPILED`, `BUILDING`, `BUILT`, `REVIEWED`,
  `COMPLETED`, `PLAN_REVISION_REQUIRED`, `REVIEW_REVISION_REQUIRED`, `ESCALATED`, `ABORTED`;
- print `structure: ok` on success and exit 0.

### Progress
- [ ] read `check_draft()` and `_validate_task_dag()` in promote_spec.py
- [ ] replace the old task-DAG parse with the new §5 parse (Task → Depends On + Verify/Expect)
- [ ] drop the `Phase Gate` and `>=1 subtask` requirements
- [ ] accept sections 0..8 in the Lane A expectations
- [ ] print `structure: ok`; keep the tag lint
- [ ] add a case to tests/test_promote_spec.py

## Owns
- `.agents/skills/spec-builder/scripts/promote_spec.py`
- `tests/test_promote_spec.py`

## Reads / Context (read-only)
- `specs/002-SPEC-subagent-task-files-full-plan.md`
- `.agents/skills/spec-builder/references/implementation-plan-template.md`

## Skills to use
- spec-builder

## Upstream interfaces
```python
def find_root() -> Path
def parse_sections(text: str) -> set[int]
def check_draft(draft: Path, lane: str) -> tuple[bool, list[int], list[str]]
def _is_noop_verify(cmd: str) -> bool
```

## Verification
```bash
python .agents/skills/spec-builder/scripts/promote_spec.py check specs/002-SPEC-subagent-task-files-full-plan.md --lane A
```
**Expect:** `structure: ok`
