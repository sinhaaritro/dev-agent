---
trigger: always_on
---


# Agent Gateway Rules

This is the primary entry point and rulebook for the workspace agent setup.

---

## ⚙️ Core Protocol

**Mandatory Skills to Load on Startup**:
*   [agent-router](../skills/agent-router/SKILL.md)
*   [alignment-protocol](../skills/alignment-protocol/SKILL.md)
*   [behavioral-modes](../skills/behavioral-modes/SKILL.md)
*   [collaborative-memory](../skills/collaborative-memory/SKILL.md)
*   [git-worktree](../skills/git-worktree/SKILL.md)
*   [task-planner](../skills/task-planner/SKILL.md)
*   [workflow-protocol](../skills/workflow-protocol/SKILL.md)

1. **Request Classification & Routing**: Delegate all request classification, complexity assessment, and persona routing decisions to the `agent-router` skill ([agent-router](../skills/agent-router/SKILL.md)).
2. **Socratic Gate Checks**: Apply Socratic gate procedures defined in the `alignment-protocol` skill ([alignment-protocol](../skills/alignment-protocol/SKILL.md)) for all complex, design, or unclear requests.
3. **Token Efficiency**: Default all output formatting and style constraints to the guidelines defined in the active `caveman` skill ([caveman](../skills/caveman/SKILL.md)) if requested.

---

## 🌐 Universal Rules (Always Active)

*   **Language Handling**: Translate user messages internally if needed, but always reply in the user's dominant language. Keep code comments, variables, and structural documentation in English.
*   **Memory Loading**: On session start, read the current handover state from [active_handoff.md](docs/handoffs/active_handoff.md) and the memory index from [MEMORY.md](docs/MEMORY.md). Load all pinned context files as instructed by the [collaborative-memory](../skills/collaborative-memory/SKILL.md) skill to restore active workspace memory.
*   **Workspace Bootstrap**: On session start, silently check for missing infrastructure files. If `Taskfile.yml` or `.gitignore` are missing from the project root, run `python .agents/scripts/ensure_taskfile.py` to restore them from templates. If the `docs/` directory does not exist, run `python .agents/skills/collaborative-memory/scripts/init_docs.py all` to scaffold the CMS layout. Do not prompt the user for these checks — execute them automatically.
*   **No Assumption Coding**: If any technical detail or requirement in a user request is ambiguous, do not guess. Stop and ask clarifying questions first.
*   **Stack Discovery**: On initial boot, scan the root directory and read the project profile from [project_profile.md](docs/project_profile.md) (if it exists) to extract the project's domain, tech stack, purpose, and rules. Also check package managers, build systems, configuration files (e.g. `Taskfile.yml`), and language frameworks to dynamically map linting, compilation, and testing strategies.
*   **Single-Agent Fallback**: If running as a single-agent developer (e.g., standard IDE assistant), you are authorized to adopt all personas sequentially as execution phases (Plan ➡️ Design ➡️ Implement ➡️ Test ➡️ Review) rather than treating them as mutually exclusive boundaries.
*   **Modular Handoffs**: Serialize major phase completions into the appropriate files under `docs/` (e.g. plans under `docs/plans/`, ADRs under `docs/adr/`, test reports under `docs/tests/`) before prompting the user or handoff.
