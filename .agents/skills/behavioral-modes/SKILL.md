---
name: behavioral-modes
description: AI operational modes (brainstorm, implement, debug, review, teach, ship). Used to adapt chat reply formats and reasoning strategies.
when_to_use: "Used dynamically by personas to adjust their response templates and communication detail."
---

# Behavioral Modes & Reply Formats

**Purpose**: Define standardized communication layouts for different development phases to optimize token efficiency and human readability.

---

## 🎭 Reply Formats by Mode

### 1. Brainstorm Mode
*   **Trigger**: Requirements planning or architectural discussions.
*   **Format**:
    ```markdown
    Let's explore some options:
    
    *   **Option A**: [Description]
        *   Pros: ...
        *   Cons: ...
    *   **Option B**: [Description]
        *   Pros: ...
        *   Cons: ...
    ```

### 2. Implement Mode
*   **Trigger**: Writing code or configurations.
*   **Format**:
    ```markdown
    [Code block]
    
    [Brief 1-2 sentence technical summary]
    ```
*   **Behavioral Constraints (CRITICAL)**:
    *   **No tutorial-style explanations**: Output only the direct technical code or configurations; do not explain fundamentals.
    *   **No verbose chat commentary**: Keep conversational text around code blocks under 2 sentences max.
    *   **No unnecessary comments**: Code must be self-documenting. Avoid comments that explain what the code does.
    *   **Quality > Speed**: Do not rush. Read all reference files before editing.

### 3. Debug Mode
*   **Trigger**: Error tracing and bug fixing.
*   **Format**:
    ```markdown
    🔍 **Symptom**: [What fails]
    🎯 **Root Cause**: [Why it fails]
    ✅ **Fix**: [Resolution steps & code]
    🛡️ **Prevention**: [Avoidance check]
    ```

### 4. Review Mode
*   **Trigger**: Auditing code quality or system specs.
*   **Format**:
    ```markdown
    ### 🔴 Critical Issues
    *   [Issue with code reference]
    
    ### 🟠 Refactoring Suggestions
    *   [Improvement recommendations]
    
    ### 🟢 Positive Observations
    *   [Good coding patterns or logic well-handled]
    ```

### 5. Teach Mode
*   **Trigger**: Explaining design concepts or codebase layouts.
*   **Format**:
    ```markdown
    ### What is [Concept]?
    [Plain English explanation]
    
    ### How it Works
    [Technical flow and code example]
    ```

### 6. Ship Mode
*   **Trigger**: Release checklist and deployment preparation.
*   **Format**:
    ```markdown
    ## Pre-Ship Checklist
    *   [ ] ESLint/Tests passing
    *   [ ] Secrets scanned
    *   [ ] Build verified
    ```

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
