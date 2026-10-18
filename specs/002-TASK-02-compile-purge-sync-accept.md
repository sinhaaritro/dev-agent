# TASK 002-02 — `compile` + `purge`/`sync`/`accept` subcommands

## Role & rules
Implement ONLY this task. Obey the given signatures. Do not plan, do not touch files you
don't Own, do not commit.

## Project overview
Dev-agent: a portable meta-framework that drives coding tasks through a phase protocol
(1-Plan → 2-Handoff → 3-Build → 4-Review → 5-Done).

## Task
Add four subcommands to promote_spec.py:
- `compile <spec>` (2-Handoff): read section 5 Tasks & Outcomes and emit one self-contained
  `NNN-TASK-<NN>-<slug>.md` per task in the **canonical task-file shape**
  (`references/task-file-format.md`), **validating each file it writes** (required headings in
  order; `Verification` has a fenced command + an `**Expect:**` line); write pre-approvals for
  every task verify command into `NNN-APPROVALS-<slug>.json` (gitignored); stamp
  `Handoff: <date>`.
- `purge <spec>`: remove the whole group (`NNN-SPEC/TASK/REPORT/APPROVALS/ESCALATION`), then
  regenerate `specs/README.md`.
- `sync`: regenerate `specs/README.md` only (no deletes).
- `accept <spec>`: stamp `Status: COMPLETED` + `Done: <date>`.
Contracts: `compile(spec: Path) -> list[Path]`, `purge(spec: Path) -> None`,
`sync(root: Path) -> None`, `accept(spec: Path) -> None`,
`validate_task_file(text: str) -> list[str]`.

### Progress
- [ ] add `references/task-file-format.md` (the canonical skeleton + rule list)
- [ ] implement `validate_task_file(text)` against the required headings + fence/Expect
- [ ] emit each task file from section 5 rows; validate before writing
- [ ] write approvals with fingerprint `command|expect|cwd` (no executor)
- [ ] implement purge/sync against the `specs/README.md` marker block
- [ ] implement accept as a status stamp only (no git)
- [ ] add cases to tests/test_promote_spec.py

## Owns
- `.agents/skills/spec-builder/scripts/promote_spec.py`
- `.agents/skills/spec-builder/references/task-file-format.md`
- `tests/test_promote_spec.py`

## Reads / Context (read-only)
- `specs/002-SPEC-subagent-task-files-full-plan.md`
- `specs/002-TASK-01-new-template-check.md`

## Skills to use
- spec-builder

## Upstream interfaces
```python
def find_root() -> Path
def parse_sections(text: str) -> set[int]
def next_number(specs_dir: Path) -> int
def _refresh_toc_for(root: Path) -> None
```

## Verification
```bash
python -m unittest tests.test_promote_spec -v
```
**Expect:** `OK`
