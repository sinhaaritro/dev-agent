# SPEC-001h: SLASH CMD Path Context Trace

- **Status**: Approved
- **Author**: @orchestrator
- **Created**: 2026-06-24
- **Parent Spec**: [SPEC-001: Agent Context & Routing](index.md)


## 1. Overview
Trace of what is loaded in the AI context when executing custom slash commands (e.g., `/verify`, `/remember`, `/plan`).

## 2. Context Load Steps
1. **Workflow Resolution**: Loads the specific workflow markdown guide (e.g., [verify.md](file:///d:/Projects/dev-agent/.agents/workflows/verify.md)).
2. **Workflow Guidelines**: Parses variables (e.g., target branch, modified files) from the active workspace.
3. **Runner Engine**: Loads tool instructions scoped to the command's checklist.
4. **Execution**: Runs the automated script or verification tools, printing step progress directly to the chat pane.

> [!NOTE]
> **Traditional Agent Difference**:
> Standard IDE assistants have no concept of project-scoped workflow scripts. The user has to manually copy-paste or write terminal commands, since the agent cannot boot structured workflow state files.
