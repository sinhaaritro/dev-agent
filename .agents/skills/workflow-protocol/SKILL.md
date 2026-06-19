---
name: workflow-protocol
description: Rules for Socratic Gate planning, phase gates, session resume, and escape hatch protocols during complex implementations.
when_to_use: "Used by the orchestrator to guide multi-phase workflows (Analysis, Planning, Solutioning, Implementation, Verification)."
---

# Workflow Lifecycle & Phase Gates

**Purpose**: Manage multi-phase software development tasks. This protocol ensures the agent researches context, aligns on design decisions, and verifies changes safely while maintaining session continuity.

---

## 🛠️ The 3-Stage Generic Lifecycle

For complex or multi-file changes, execution is divided into three generic stages. Specialist agents or sub-phases (e.g. security audits, SEO scans) plug into these stages as required by the project.

### Stage 1: Pre-coding Phase (Planning & Design Alignment)
*   **Goal**: Gather context, align on technical decisions, design files, and obtain user approval before writing code.
*   **Core Workflow**:
    1.  **Analysis & Discovery**: Inspect the codebase, map dependencies, and check memory (`docs/MEMORY.md`).
    2.  **Socratic Gate**: Formulate trade-offs and options tables for ambiguous requirements using `alignment-protocol`.
    3.  **Plan & Solution Design**: Create `docs/plans/implementation_plan-{slug}.md` and `docs/plans/task-{slug}.md` (derived from templates). Detail affected files without writing code blocks.
    4.  **Approval Gate**: Seek user approval on the design. **Pause execution** and remain in the pre-coding phase. The agent MUST NOT transition to Stage 2 until the human sends an explicit proceed signal (see `alignment-protocol` → Phase Transition Gate). Design feedback, question answers, and inline review comments do NOT constitute approval — they are continued Stage 1 activity.
*   *Plug-and-play Specialists*: `@architect` (API/Schema design), `@legacy-analyst` (analyzing old codebases), `@security-reviewer` (threat modeling).

### Stage 2: Coding Phase (Implementation & Writing)
*   **Goal**: Implement the approved design. This covers all writing tasks, including source code, tests, documentation, and markdown files.
*   **Core Workflow**:
    1.  **Execute Milestones**: Work through the checklist in `docs/plans/task-{slug}.md` (mark items as `[/]` in-progress and `[x]` complete).
    2.  **Clean Code Adherence**: Apply standards like KISS, modular structures, and self-documenting naming rules.
*   *Plug-and-play Specialists*: `@frontend-developer`, `@backend-developer`, `@document-writer`.

### Stage 3: Post-coding Phase (Verification & Delivery)
*   **Goal**: Verify implementation correctness and output verification logs.
*   **Core Workflow**:
    1.  **Automated Verification**: Run compiler, linter, and testing commands (`task verify` or specific test runner).
    2.  **Deliver Walkthrough**: Generate `docs/plans/walkthrough-{slug}.md` containing the Change Registry, test output logs, and clean code self-review.
*   *Plug-and-play Specialists*: `@qa-tester` (test suite verification), `@security-tester` (security scanning), `@seo-verifier`.

---

## 🔄 Session Resume Protocol (Handoff Drift)

Because AI sessions are stateless, on boot the agent must check if it is resuming an in-progress workflow:
1.  **Worktree Check**: Check if the current workspace directory is inside `.worktrees/`. If so:
    *   Check if [subagent_dispatch.md](../../../docs/handoffs/subagent_dispatch.md) exists. If it does, load context from it instead of the global `active_handoff.md`, and announce:
        > *"I detected an active worktree execution. Resuming subagent tasks from subagent_dispatch.md..."*
    *   If no dispatch card exists, proceed to the main workspace scans below to search for local plans.
2.  **Scan Workspace**: Check the `docs/plans/` directory for any active `implementation_plan-*.md` or `task-*.md` files.
3.  **Determine Current State**:
    *   If a plan exists but is not approved ➔ Resume in **Stage 1: Pre-coding Phase** (Awaiting design approval).
    *   If a plan is approved and tasks in `task-*.md` are partially complete ➔ Resume in **Stage 2: Coding Phase** (Execution).
4.  **Announce State**: Print a clear resume banner to the user:
    > *"I detected an active plan in progress under `docs/plans/`. Resuming execution at Stage X (Task name)..."*

---

## 🚪 Escape Hatch Rule (Off-Topic Chats)

If the user interrupts the planning lifecycle with an unrelated or investigatory query (e.g., *"How does X library work?"* or *"What is our git layout?"*):
1.  **Bypass Phase Constraints**: Temporarily shift register to `TEACH` or `REVIEW` mode to answer the question directly.
2.  **Separate Artifacts**: If the question requires research or analysis, output the explanation to a scratchpad file (e.g., `docs/plans/scratch-{slug}.md`) rather than editing the core plan.
3.  **Remind User of Plan Status**: Conclude your answer by pointing back to the active plan:
    > *"Now returning to the active planning workflow under `docs/plans/...`"*
