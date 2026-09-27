# TASK 003-03 — Update skill + rules docs

## Role & rules
Implement ONLY this task. Obey the given signatures. Do not plan, do not touch files you
don't Own, do not commit.

## Project overview
The spec-builder engine currently bootstraps and regenerates `docs/README.md`
on every promote/topic/handoff/toc run and carries the `tag-index` subcommand
whose only output is that file. This change removes **every** reference to
`docs/README.md` from the engine and its docs: the script should not know the
file exists. `docs/README.md` itself stays as a plain human-maintained file
(its generated TOC/TAG-INDEX blocks are stripped). `specs/README.md` keeps its
generated TOC. No architectural decisions surface (Lane B).
(the global task list lives in the spec §5 — not copied here)

## Task
Update skill + rules docs. Depends On: Task 1.

### Progress
- [ ] implement the task
- [ ] run the Verification command and match Expect

## Owns
- [MODIFY] .agents/skills/spec-builder/scripts/promote_spec.py
- [MODIFY] docs/README.md
- [MODIFY] .agents/skills/spec-builder/SKILL.md
- [MODIFY] .agents/rules/system.md
- [MODIFY] docs/005-docs-architecture-and-spec-lifecycle.md
- [MODIFY] docs/decision-records.md
- [MODIFY] tests/test_promote_spec_docs_root.py

## Reads / Context (read-only)
- the spec: 003-SPEC-stop-the-engine-from-knowing-about-docs-readme-md.md

## Skills to use
- spec-builder

## Upstream interfaces
```python
def find_root() -> Path
```

## Verification
```bash
grep -o "CLEAN" .agents/rules/system.md | tail -1
```
**Expect:** `CLEAN`
