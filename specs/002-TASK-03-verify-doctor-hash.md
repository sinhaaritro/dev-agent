# TASK 002-03 — `verify.py`: root cwd, fingerprint, hash evidence, doctor/status/report

role & rules
  You are a coder. Implement ONLY this task. Obey the given signatures.
  Do not plan, do not touch files you don't Own, do not commit.

project overview
  Dev-agent: a portable meta-framework that drives coding tasks through a phase protocol
  (1-Plan → 2-Handoff → 3-Build → 4-Review → 5-Done).

plan progress            (as written at 2-Handoff; updated live during the run)
  [ ] 01 new-template check + statuses
  [ ] 02 compile + purge/sync/accept
  [ ] 03 verify.py doctor/hash/status/report
  [ ] 04 coder contract
  [ ] 05 phase renumber
  [ ] 06 run contract
  [ ] 07 branch/commit guardrail
  [ ] 08 spec-builder template
  [ ] 09 docs + charts
  [ ] 10 slim skills
  [ ] 11 bootstrap seeds
  [ ] 12 task-cleaner
  [ ] 13 migrate 001 + backlog
  [ ] 14 drift test + final verify

this task
  03 verify.py doctor/hash/status/report

task
  Update verify.py:
  - run subprocess with `cwd=find_root()`; fingerprint = `sha256(command | expect | cwd)`
    — drop `executor` so a human's pre-approval matches a coder's run.
  - `run` records evidence into the task file's evidence block: command, pass timestamp, and a
    `sha256` of every owned file at that moment.
  - `doctor --spec <n>`: the 9 ordered per-spec preconditions (§2.6); print `PRECONDITIONS OK`.
  - `status --task <id>`: derive `MET` (hash matches) / `NOT MET` / `STALE` (hash changed) /
    `NO-EVIDENCE` from the task file.
  - `report --spec <n>`: regenerate `NNN-REPORT-<slug>.md`.
  Contracts: `doctor(spec: Path) -> list[str]`, `run(...) -> int`, `status(task: Path) -> str`,
  `report(spec: Path) -> Path`.

  subtasks                      (static, generation-time — follow, do not check off)
    - change cwd handling + fingerprint
    - write/read the hash evidence block in the task file
    - implement doctor with the ordered checks
    - implement hash-based status derivation
    - implement report generation
    - add cases to tests/test_verify.py

Owns
  .agents/skills/verification-runner/scripts/verify.py
  tests/test_verify.py

Reads/Context                     (read-only)
  specs/002-subagent-task-files-phase-renumbering-and-full-plan-execution.md
  specs/002-TASK-01-new-template-check.md

Skills to use
  - verification-runner

upstream interfaces
  def find_root() -> Path
  def command_fingerprint(command: str, expect: str, cwd: str) -> str
  def read_approvals(state_dir: Path) -> dict

verification
  python -m unittest tests.test_verify -v
  Expect: OK
