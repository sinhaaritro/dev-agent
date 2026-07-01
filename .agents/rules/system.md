---
trigger: always_on
---


# Agent Gateway Rules

This is the primary entry point and rulebook for the workspace agent setup.

---

## ⚙️ Core Protocol

**Mandatory Skills (Execution Order)**:
1.  [collaborative-memory](../skills/collaborative-memory/SKILL.md) — Load memory & handoff state
2.  [workflow-protocol](../skills/workflow-protocol/SKILL.md) — **Session Resume check** (detect active plans before classifying)
3.  [agent-router](../skills/agent-router/SKILL.md) — Classify request & boot persona
4.  [alignment-protocol](../skills/alignment-protocol/SKILL.md) — Socratic gates (when triggered)
5.  [behavioral-modes](../skills/behavioral-modes/SKILL.md) — Apply mode formatting
6.  [task-planner](../skills/task-planner/SKILL.md) — Plan structuring (when triggered)
7.  [git-worktree](../skills/git-worktree/SKILL.md) — Worktree ops (when triggered)

1. **Request Classification & Routing**: Delegate all request classification, complexity assessment, and persona routing decisions to the `agent-router` skill ([agent-router](../skills/agent-router/SKILL.md)).
2. **Socratic Gate Checks**: Apply Socratic gate procedures defined in the `alignment-protocol` skill ([alignment-protocol](../skills/alignment-protocol/SKILL.md)) for all complex, design, or unclear requests.
3. **Token Efficiency**: If the `caveman` skill exists in the repo (`.agents/skills/caveman/`), apply its formatting rules when the user requests compressed communication. If it is not present, respond normally without attempting to install it.
4. **Execution Precedence**: On session boot, always run the `workflow-protocol` Session Resume check *before* the `agent-router` Request Classifier. If an active plan is detected, resume the workflow at the appropriate stage instead of re-classifying the user's first message as a new request.

---

## 🌐 Universal Rules (Always Active)

*   **Language Handling**: Translate user messages internally if needed, but always reply in the user's dominant language. Keep code comments, variables, and structural documentation in English.
*   **Skill Creation Fallback**: If the user asks to create a new skill, use the `skill-creator` skill ([skill-creator](../skills/skill-creator/SKILL.md)) if it exists in the repo. If it is not present, ask the user how they would like to create the skill instead of attempting to install or fetch it.
*   **Memory Loading**: On session start, read the current handover state from [active_handoff.md](docs/handoffs/active_handoff.md) and the memory index from [MEMORY.md](docs/MEMORY.md). Load all pinned context files as instructed by the [collaborative-memory](../skills/collaborative-memory/SKILL.md) skill to restore active workspace memory.
*   **Workspace Bootstrap**: On session start, silently check for missing infrastructure files. If `Taskfile.yml` or `.gitignore` are missing from the project root, run `python .agents/scripts/ensure_taskfile.py` to restore them from templates. If the `docs/` directory does not exist, run `python .agents/skills/collaborative-memory/scripts/init_docs.py all` to scaffold the CMS layout. Do not prompt the user for these checks — execute them automatically.
*   **No Assumption Coding**: If any technical detail or requirement in a user request is ambiguous, do not guess. Stop and ask clarifying questions first.
*   **Stack Discovery**: On initial boot, scan the root directory and read the project profile from [project_profile.md](docs/project_profile.md) (if it exists) to extract the project's domain, tech stack, purpose, and rules. Also check package managers, build systems, configuration files (e.g. `Taskfile.yml`), and language frameworks to dynamically map linting, compilation, and testing strategies.
*   **Single-Agent Fallback**: If running as a single-agent developer (e.g., standard IDE assistant), you are authorized to adopt all personas sequentially as execution phases (Plan ➡️ Design ➡️ Implement ➡️ Test ➡️ Review) rather than treating them as mutually exclusive boundaries.
*   **Modular Handoffs**: Serialize major phase completions into the appropriate files under `docs/` (e.g. plans under `docs/plans/`, ADRs under `docs/adr/`, test reports under `docs/tests/`) before prompting the user or handoff.
