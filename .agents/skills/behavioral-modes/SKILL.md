---
name: behavioral-modes
description: AI operational modes (brainstorm, implement, debug, review, teach, ship). Used to adapt chat reply formats and reasoning strategies.
when_to_use: "Used dynamically by personas to adjust their response templates and communication detail."
---

# Behavioral Modes & Reply Formats

**Purpose**: Define standardized communication layouts for different development phases to optimize token efficiency and human readability.

---

## 🎭 Reply Formats by Mode

Verify any formatted file against its template by running:
```bash
python .agents/skills/behavioral-modes/scripts/verify_sections.py --template <template_path> <target_file>
```

| Mode | Trigger Condition | Template File | Constraints & Rules |
| :--- | :--- | :--- | :--- |
| **Brainstorm** | Requirements planning or architectural discussions | [templates/brainstorm.md](templates/brainstorm.md) | None |
| **Implement** | Writing code or configurations | [templates/implement.md](templates/implement.md) | **CRITICAL rules:**<br>- No tutorial-style explanations.<br>- Keep conversational text around code blocks under 2 sentences max.<br>- No unnecessary comments (code must be self-documenting).<br>- Quality > Speed (read references before editing). |
| **Debug** | Error tracing and bug fixing | [templates/debug.md](templates/debug.md) | None |
| **Review** | Auditing code quality or system specs | [templates/review.md](templates/review.md) | Structured based on `review.md` containing `🔴 Critical Issues`, `🟠 Refactoring Suggestions`, and `🟢 Positive Observations`. |
| **Teach** | Explaining design concepts or codebase layouts | [templates/teach.md](templates/teach.md) | Structured based on `teach.md` containing `Hook`, `Prerequisites`, `Technical Explanation`, `Code Implementation`, and `Footer`. |
| **Ship** | Release checklist and deployment preparation | [templates/ship.md](templates/ship.md) | None |

---

## 👥 Multi-Agent Collaboration Patterns

When coordinating with subagents (e.g. executing tasks in parallel or delegating scopes), follow these standard collaboration modes:

### 1. 🔭 EXPLORE Mode
*   **Role**: Codebase Discovery and Dependency Mapping.
*   **Behavior**: Silently read code, check package structures, and map file calls without modifying files.
*   **Output**: A concise dependency index or discovery findings summary.

### 2. 🗺️ Plan-Execute-Critic (PEC) Cycle
For high-complexity tasks, execute this cyclic mode handoff:
1.  **Planner**: Decomposes the requirement into atomic milestones under `docs/plans/` (`task-{slug}.md`).
2.  **Executor**: Focuses strictly on writing the code logic (`IMPLEMENT` mode).
3.  **Critic**: Audits code quality, checks coverage, and runs security scans (`REVIEW` mode).

### 3. 🧠 Mental Model Sync
*   **Behavior**: When spawning a subagent, pass a highly distilled summary (Mental Model) of active requirements, configurations, and decisions. When the subagent completes, it must write back a context sync block to update the parent agent, minimizing context window bloat.
