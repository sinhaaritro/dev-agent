---
name: agent-router
description: Automatically resolves which specialist persona to apply based on request complexity and keyword domain matching.
when_to_use: "Always active on startup. Analyzes incoming prompt intent silently to route tasks."
---

# Agent Router Skill

**Purpose**: Automatically analyze incoming developer requests, classify them by type/complexity, match them against workspace personas, and adopt the appropriate specialist constraints.

---

## 📥 1. Request Classifier

Before taking any actions, classify the user request to determine the required execution path and the resources to load:

| Request Type | Trigger Keywords | Skills / Personas to Load | Target Behavioral Mode | Workflow Action |
| :--- | :--- | :--- | :--- | :--- |
| **QUESTION** | "what is", "how does", "explain", "why", "where", "who", "can you"... | None (System rules only) | `TEACH` | Direct text explanation (No personas or edit tools loaded). |
| **ANALYSIS** | "analyze", "deep dive", "audit", "explain in detail", "review" | `[Resolved Persona from agent-map]` | `REVIEW` | **Write Artifact**: Output report to `analysis-{slug}.md`. Print short summary + link in chat. |
| **BUG FIX** | "fix", "debug", "error", "fails", "bug", "crash"... | `[Resolved Persona from agent-map]` | `DEBUG` | Direct inline debug report and repair using Symptom/Cause/Fix/Prevention. |
| **SIMPLE CODE** | "add", "change" (single-file edits)... | `[Resolved Persona from agent-map]` | `IMPLEMENT` | Direct inline edit via tools (No planning files required). |
| **COMPLEX CODE** | "build", "create", "implement", "refactor" (multi-file)... | `personas/orchestrator.md`<br>+ `[Resolved Persona from agent-map]` | `IMPLEMENT` | **Plan Required**: Boot `@orchestrator` and execute `workflow-protocol`. |
| **DESIGN/UI** | "design", "UI", "page", "dashboard"... | `personas/architect.md`<br>+ `[Resolved Persona from agent-map]` | `BRAINSTORM` | **Plan Required**: Boot `@architect`, then `@orchestrator` and execute `workflow-protocol`. |
| **RELEASE / SHIP**| "deploy", "release", "ship", "production check"... | `personas/orchestrator.md` or `personas/qa.md` | `SHIP` | Render Pre-Ship Checklist, run compilation, format, and test verifications. |
| **SLASH CMD** | `/verify`, `/remember`, `/plan` | Dependent on workflow | Dependent on workflow | Run specific workflow instructions. |

### 🛠️ Phased Execution (Complex Tasks)
For complex tasks where a plan is required, direct execution is handed over to the `@orchestrator` persona. The orchestrator will dynamically load the `workflow-protocol` skill and guide the workflow through the Socratic Analysis, Planning (saving files under `docs/plans/`), Solutioning (design approval), and Implementation/Verification phases.

---

## 🔀 2. Intelligent Agent Routing

Parse prompt domains silently to adopt the correct role.

### Domain Resolution Protocol
1.  **Silent Analysis**: Extract technical keywords, affected directories, and stack requirements from the prompt. Do not narrate this step (e.g. do not say *"I am analyzing your prompt..."*).
2.  **Worktree Detection & Bypass**: Check if the workspace root directory is inside `.worktrees/`. If so:
    *   **Delegated Subagent Check**: Check if [subagent_dispatch.md](../../../docs/handoffs/subagent_dispatch.md) exists locally. If it does, immediately bypass the Request Classifier, adopt the designated `Persona` from the card, load its skills, and execute its checklist.
    *   **Independent Agent Check**: If no dispatch card exists, treat it as an independent branch agent. Do NOT bypass classification; proceed to the next steps and run the full 3-stage lifecycle locally.
3.  **Consult Directory Catalog**: Query [agent-map](../../agent-map.md) to discover which personas and skills are registered in the current workspace.
4.  **Trigger Notification Banner**: You MUST inform the developer which role is being applied using this exact formatting before rendering the response:
   ```markdown
   🤖 **Applying knowledge of `@[persona-name]`...**
   ```
5.  **Bypass on Override**: If the user explicitly mentions an agent (e.g., `@engineer`), immediately bypass routing checks and adopt that persona. If the mentioned persona is not found in `agent-map.md`, notify the developer and default to the most relevant one.

### Agent Routing Checklist
Before any code editing or system design output, complete this check:
*   [ ] Checked `agent-map.md` to identify the correct specialist for this domain?
*   [ ] Read the target persona instructions (e.g., the resolved persona file under `personas/`)?
*   [ ] Announce the active banner `🤖 Applying knowledge of @[persona]...`?
*   [ ] Loaded persona-specific skills specified in its frontmatter?
