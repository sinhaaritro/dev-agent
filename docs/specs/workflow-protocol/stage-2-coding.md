# SPEC-002b: Stage 2: Coding Phase Specification

- **Status**: Approved
- **Author**: @orchestrator
- **Created**: 2026-06-27
- **Parent Spec**: [SPEC-002: Agent Workflow Protocol Specification](index.md)

## 1. Overview
Stage 2 (Coding) is the active execution and implementation phase. Its goal is to translate the approved implementation plan into verified code changes, tracking milestones systematically using a task checklist, and adhering to strict software engineering standards.

## 1.1 Activated By
This stage is entered after Stage 1 approval, when executing:
- [SPEC-001e: COMPLEX CODE Path](../agent-context-routing/complex-code-path.md) → Step 6
- [SPEC-001f: DESIGN/UI Path](../agent-context-routing/design-ui-path.md) → (post-handoff to COMPLEX CODE)

## 2. Core Workflow Steps

```mermaid
graph TD
    A[Approve Plan] --> B[1. Initialize task.md Checklist]
    B --> C[2. Pick Milestone]
    C --> D[Mark [//] In-Progress]
    D --> E[Modify Code / Create Files]
    E --> F[Mark [x] Completed]
    F -->|More Tasks| C
    F -->|All Tasks Done| G[Transition to Stage 3]
```

### 1. Execute Milestones
*   **Actions**:
    *   Work sequentially through the checklist items in `docs/plans/task-{slug}.md`.
    *   Explicitly mark items in progress with `[/]` and completed with `[x]` to maintain a clear audit trail.
    *   Submit contiguous edits using precise replacement tools (e.g. `replace_file_content` or `multi_replace_file_content`).

### 2. Clean Code Adherence
*   **Standards**:
    *   **KISS (Keep It Simple, Stupid)**: Write simple, straightforward code and avoid over-engineering.
    *   **Modular Architecture**: Group code into cohesive modules/components.
    *   **Documentation Integrity**: Maintain existing comments and docstrings. Use clear, self-documenting naming conventions.

---

## 3. Specialist Plug-ins
*   **`@frontend-developer`**: Specialized in styling, user interface layouts, client-side state, and visual polishing.
*   **`@backend-developer`**: Specialized in server logic, database integration, background processing, and API endpoints.
*   **`@document-writer`**: Specialized in user manuals, markdown guides, API references, and documentation.

---

> [!NOTE]
> **Traditional Agent Difference**:
> Traditional IDE assistants edit files directly without a task checklist, making massive, unstructured changes that are hard to review. They frequently break unrelated code blocks, ignore documentation integrity, and lose track of the original plan constraints.
