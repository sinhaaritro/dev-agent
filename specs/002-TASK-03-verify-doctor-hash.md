# TASK 002-03 — `verify.py`: root cwd, fingerprint, hash evidence, doctor/status/report

## Role & rules
Implement ONLY this task. Obey the given signatures. Do not plan, do not touch files you
don't Own, do not commit.

## Project overview
Dev-agent: a portable meta-framework that drives coding tasks through a phase protocol
(1-Plan → 2-Handoff → 3-Build → 4-Review → 5-Done).

## Task
Update verify.py:
- run subprocess with `cwd=find_root()`; fingerprint = `sha256(command | expect | cwd)` —
  drop `executor` so a human's pre-approval matches a coder's run.
- `run` records evidence into the task file's evidence block: command, pass timestamp, and a
  `sha256` of every owned file at that moment.
- `doctor --spec <n>`: the 9 ordered per-spec preconditions (section 2.6); print `PRECONDITIONS OK`.
- `status --task <id>`: derive `MET` (hash matches) / `NOT MET` / `STALE` (hash changed) /
  `NO-EVIDENCE` from the task file.
- `report --spec <n>`: regenerate `NNN-REPORT-<slug>.md`.
Contracts: `doctor(spec: Path) -> list[str]`, `run(...) -> int`, `status(task: Path) -> str`,
`report(spec: Path) -> Path`.

### Progress
- [x] change cwd handling + fingerprint
- [x] write/read the hash evidence block in the task file
- [x] implement doctor with the ordered checks
- [x] implement hash-based status derivation
- [x] implement report generation
- [x] add cases to tests/test_verify.py

## Owns
- `.agents/skills/verification-runner/scripts/verify.py`
- `tests/test_verify.py`

## Reads / Context (read-only)
- `specs/002-SPEC-subagent-task-files-full-plan.md`
- `.agents/skills/spec-builder/references/task-file-format.md`

## Skills to use
- verification-runner

## Upstream interfaces
```python
def find_root() -> Path
def command_fingerprint(command: str, expect: str, cwd: str) -> str
def read_approvals(state_dir: Path) -> dict
```

## Verification
```bash
python -m unittest tests.test_verify -v
```
**Expect:** `OK`
