# TASK 002-09 — `docs/` topic set + move flow charts

role & rules
  You are a coder. Implement ONLY this task. Obey the given signatures.
  Do not plan, do not touch files you don't Own, do not commit.

project overview
  Dev-agent: a portable meta-framework that drives coding tasks through a phase protocol
  (1-Plan → 2-Handoff → 3-Build → 4-Review → 5-Done).

this task
  09 docs + charts

task
  Write the topic docs that carry the deep explanation (the `.agents` files stay short):
  `docs/lifecycle.md`, `docs/task-files.md`, `docs/verification.md`, `docs/run-contract.md`,
  `docs/branching.md`. Move the mermaid charts out of `specs/002-flow-design.md` into
  `docs/flow.md` (master state machine, build run flow, review & acceptance, multi-spec +
  escalation). Each doc gets a `tags:` frontmatter block (topic-doc rules).

  progress                      (this task only — the owning coder updates it)
    - create the five topic docs from §2 of the spec (explain the why)
    - copy the mermaid blocks into docs/flow.md with short prose
    - add tags frontmatter to each; do not edit .agents here
    - ensure docs/_topics.md is regenerated (map-generator sync-docs)

Owns
  docs/lifecycle.md
  docs/task-files.md
  docs/verification.md
  docs/run-contract.md
  docs/branching.md
  docs/flow.md

Reads/Context                     (read-only)
  specs/002-subagent-task-files-phase-renumbering-and-full-plan-execution.md
  specs/002-flow-design.md

Skills to use
  - map-generator

upstream interfaces
  (none)

verification
  bash -c 'test -f docs/flow.md && grep -Eq "flowchart|stateDiagram" docs/flow.md && echo DOCS-FLOW-OK'
  Expect: DOCS-FLOW-OK
