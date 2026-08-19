# Actionable TODO Checklist Format

Status markers used in plan checklists (000 §7, spec-builder SKILL.md). Updated in real time
during Phase 2-Build inside `docs/temp/draft-plan.md`:

| Marker | Meaning | Rule |
| :--- | :--- | :--- |
| `- [ ]` | Pending | Task has not started. |
| `- [/]` | In Progress | Active editing underway. |
| `- [x]` | Completed | Code written and local verification passed. |

Rules:

1. A step is `[x]` only after local verification passed — not merely when code was
   written.
2. A step that fails verification 3 consecutive times reverts to `[ ]`, and the
   escalation protocol fires (`AGENTS.md` §9).
3. Never mark a step `[x]` and leave its verification blank.