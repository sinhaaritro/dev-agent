# TASK 002-09 — `docs/` topic set + move flow charts

## Role & rules
Implement ONLY this task. Obey the given signatures. Do not plan, do not touch files you
don't Own, do not commit.

## Project overview
Dev-agent: a portable meta-framework that drives coding tasks through a phase protocol
(1-Plan → 2-Handoff → 3-Build → 4-Review → 5-Done).

## Task
Write the topic docs that carry the deep explanation (`.agents` files stay short):
`docs/lifecycle.md`, `docs/task-files.md`, `docs/verification.md`, `docs/run-contract.md`,
`docs/branching.md`. Move the mermaid charts out of `specs/002-flow-design.md` into
`docs/flow.md` (master state machine, build run flow, review & acceptance, multi-spec +
escalation). Each doc gets a `tags:` frontmatter block (topic-doc rules).

### Progress
- [x] create the five topic docs from section 2 of the spec (explain the why)
- [x] copy the mermaid blocks into docs/flow.md with short prose
- [x] add tags frontmatter to each; do not edit `.agents` here
- [x] regenerate docs/_topics.md (map-generator sync-docs)

## Owns
- `docs/lifecycle.md`
- `docs/task-files.md`
- `docs/verification.md`
- `docs/run-contract.md`
- `docs/branching.md`
- `docs/flow.md`

## Reads / Context (read-only)
- `specs/002-SPEC-subagent-task-files-full-plan.md`
- `specs/002-flow-design.md`

## Skills to use
- map-generator

## Upstream interfaces
(none)

## Verification
```bash
bash -c 'test -f docs/flow.md && grep -Eq "flowchart|stateDiagram" docs/flow.md && echo DOCS-FLOW-OK'
```
**Expect:** `DOCS-FLOW-OK`
