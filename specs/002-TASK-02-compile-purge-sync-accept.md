# TASK 002-02 — `compile` + `purge`/`sync`/`accept` subcommands

role & rules
  You are a coder. Implement ONLY this task. Obey the given signatures.
  Do not plan, do not touch files you don't Own, do not commit.

project overview
  Dev-agent: a portable meta-framework that drives coding tasks through a phase protocol
  (1-Plan → 2-Handoff → 3-Build → 4-Review → 5-Done).

this task
  02 compile + purge/sync/accept

task
  Add four subcommands to promote_spec.py:
  - `compile <spec>` (2-Handoff): read §5 Tasks & Outcomes and emit one self-contained
    `NNN-TASK-<NN>-<slug>.md` per task (format = `specs/002-TASK-01-new-template-check.md`);
    write pre-approvals for every task verify command into `NNN-APPROVALS-<slug>.json`
    (gitignored); stamp `Handoff: <date>`.
  - `purge <spec>`: remove the whole group (`NNN-SPEC/TASK/REPORT/APPROVALS/ESCALATION`),
    then regenerate `specs/README.md`.
  - `sync`: regenerate `specs/README.md` only (no deletes).
  - `accept <spec>`: stamp `Status: COMPLETED` + `Done: <date>` (used when a run stopped at
    `pre-commit` and the human commits/accepts).
  Contracts: `compile(spec: Path) -> list[Path]`, `purge(spec: Path) -> None`,
  `sync(root: Path) -> None`, `accept(spec: Path) -> None`.

  progress                      (this task only — the owning coder updates it)
    - reuse next_number + slug_from_title for the task-file names
    - render the task-file template from §5 rows (heading shows the NN, e.g. 002-01)
    - write approvals with fingerprint command|expect|cwd (no executor)
    - implement purge/sync against specs/README.md marker block
    - implement accept as a status stamp only (no git)
    - add cases to tests/test_promote_spec.py

Owns
  .agents/skills/spec-builder/scripts/promote_spec.py
  tests/test_promote_spec.py

Reads/Context                     (read-only)
  specs/002-subagent-task-files-phase-renumbering-and-full-plan-execution.md
  specs/002-TASK-01-new-template-check.md

Skills to use
  - spec-builder

upstream interfaces
  def find_root() -> Path
  def parse_sections(text: str) -> set[int]
  def next_number(specs_dir: Path) -> int
  def _refresh_toc_for(root: Path) -> None

verification
  python -m unittest tests.test_promote_spec -v
  Expect: OK
