# TASK 003-01 — Remove docs/README.md machinery from promote_spec.py

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
(the global task list lives in the spec section 5 — not copied here)

## Task
Remove docs/README.md machinery from promote_spec.py. Depends On: None.

### Progress
- [x] implement the task
- [x] run the Verification command and match Expect

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
test -z "$(grep -E "docs/README|tag-index" .agents/skills/spec-builder/scripts/promote_spec.py)" && echo CLEAN
```
**Expect:** `CLEAN`

<!-- VERIFY:EVIDENCE:START -->
```json
{
  "command": "test -z \"$(grep -E \"docs/README|tag-index\" .agents/skills/spec-builder/scripts/promote_spec.py)\" && echo CLEAN",
  "exit": 0,
  "expect": "CLEAN",
  "matched": true,
  "at": "2026-09-27T11:32:27",
  "output_sha256": "0b98843240a0b1a2384483206c02be8968dd809eb73838820be24cb7d6d6aeb9",
  "files": {
    ".agents/skills/spec-builder/scripts/promote_spec.py": "7706d37072429b27505f22ff0c7394d998bd1975d6b49a58c17e0b1a5bac2d50",
    "docs/README.md": "954befb1b8b5e21234c261d653b7ebb7bc2083d324d7fb4b871ce1a1dc07bed5",
    ".agents/skills/spec-builder/SKILL.md": "d0783a72aaea6495a555c8e0ea45afb747d870a5c542d63272aeb7f59c3e133c",
    ".agents/rules/system.md": "e29b826e89af49398d129fe4d08819599da9b6d08512513a822c5e56a3f9bc48",
    "docs/005-docs-architecture-and-spec-lifecycle.md": "93e2ac268ba9a5f06bdff962df5d6c9f8f42b4b52bfc9b2bc91a942bfa8680af",
    "docs/decision-records.md": "41c7e33d421d572893f379cfdbbfc41b85818f35120f7a946e08bed13c82c914",
    "tests/test_promote_spec_docs_root.py": "1f00a828d4a61c863848979588127db4c23c7c7a4fe9983cf2f0ae6843891bd2"
  }
}
```
<!-- VERIFY:EVIDENCE:END -->
