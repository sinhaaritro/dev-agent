# Actionable TODO Checklist Format

Status markers in plan checklists (000 §7, spec-builder SKILL.md). Updated in real time during Phase 2-Build inside the running draft:

| Marker | Meaning | Rule |
| :--- | :--- | :--- |
| `- [ ]` | Pending | Task has not started. |
| `- [/]` | In Progress | Active editing underway. |
| `- [x]` | Completed | Code written and local verification passed. |

Rules:

1. A step is `[x]` only after local verification passed — not merely when code was written.
2. A step failing verification 3 consecutive times reverts to `[ ]`, and the escalation protocol fires (`AGENTS.md` §9).
3. Never mark `[x]` with blank verification.
