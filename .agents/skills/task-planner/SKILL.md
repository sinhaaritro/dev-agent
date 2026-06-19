---
name: task-planner
description: Structured task planning with dynamic scaling, dependency mapping, and verification metrics. Use when implementing features, refactoring, or any multi-step work.
when_to_use: "Use when creating structured task plans, breaking down features into actionable tasks, or defining verification criteria."
---

# Task Planner Skill

## Overview
This skill provides a framework for breaking down workspace implementation work into clear, actionable, and independently verifiable tasks. It ensures planning is tailored to task complexity, aligned with persistent memory decisions, and dynamically updated during execution.

---

## 📋 Task Breakdown Principles

1. **Small, Focused Tasks**: Break tasks down so they take 2–5 minutes of focused agent execution. Avoid large, sweeping milestones.
2. **Actionable & Specific**: Define exactly what to execute (e.g. *Run npm run build*, *Create user database schema*) rather than vague assertions (e.g. *Fix db*, *Test page*).
3. **Verifiable Steps**: Every task must end with an explicit `Verify: [criteria/command]` step.
4. **Logical Ordering**: Place structural setup and dependencies first. Verification and cleanup tasks must be run last.
5. **Standard Folder Placement**: Save implementation plans and task trackers under `docs/plans/` as `{task-slug}-plan.md` and `{task-slug}-task.md`. This keeps the project clean and maintains session continuity.

---

## ⚡ Dynamic Plan Scaling

Adjust the complexity of the planning files based on the request complexity to conserve token budget:

### 1. Micro-Plan (Simple Tasks / Bug Fixes)
*   **When**: Adjustments affecting a single file, simple styling tweaks, or minor refactors.
*   **Format**: Create a lightweight `{task-slug}-task.md` file under `docs/plans/` containing only 3–5 items. No formal plan document needed.

### 2. Standard Plan (Multi-file Features)
*   **When**: Default for standard coding features, refactoring multiple components, or writing integrations.
*   **Format**: Create both `{task-slug}-plan.md` and `{task-slug}-task.md` under `docs/plans/` using the templates.

### 3. Architectural Plan (System Upgrades)
*   **When**: Database schema changes, major API contract shifts, or refactoring key modules.
*   **Format**: Use the standard templates but include dedicated sections in the plan for:
    *   *API & Schema contracts*
    *   *Rollback strategy / Blast radius*
    *   *Regression risks & Mitigation*

---

## 🧠 Memory & Specs Alignment (CMS)

Before writing or editing any plan:
1.  **Check Memory Index**: Read `docs/MEMORY.md` to discover relevant Specs, ADRs, or previously resolved design decisions.
2.  **Inspect Active Specs**: Check if there is an active spec for the current milestone under `docs/specs/`.
3.  **Align Decisions**: Ensure the plan adheres to approved architectural decisions. Do not query or guess about decisions already recorded in memory.

---

## 🔄 Plan Mutation & Human-in-the-Loop Gate

Plans are living documents. If you hit a blocker, discover missing dependencies, or identify shifting requirements:
1.  **Stop Execution**: Immediately pause the implementation loop. Do not write or edit application code under new assumptions before aligning the plan.
2.  **Assess Severity**:
    *   **Minor Adjustments** (e.g., adding a missing verification task, minor code file rename): Update the tracker `{task-slug}-task.md` under `docs/plans/` directly, note the reason, and proceed.
    *   **Significant Scope Drift / Design Changes** (e.g., database schema changes, new library requirements, API contract shifts, or feature pivots):
        *   Formulate 2-3 alternative paths with pros/cons.
        *   **Stop and Prompt the User**: Present the options and the proposed changes to the user. Await explicit approval before updating the plan files or resuming work.
3.  **Mutate & Annotate**: Once aligned with the user, update the checklists in `{task-slug}-plan.md` and `{task-slug}-task.md` under `docs/plans/`. Mark blocked/scrapped tasks using `[! Blocked/Scrapped: Reason]`.
4.  **Log Changes**: Document the mutation rationale in a brief "Plan Amendments" log inside the plan file.

---

## 👥 Subagent & Multi-Agent Planning

When acting in a multi-agent environment or coordinating work through subagents:

### 1. Planning Subagent Tasks
*   **Identify Delegatable Work**: Look for self-contained, independent tasks in your plan (e.g., *Write a specific test suite*, *Apply lint fixes to a folder*, *Conduct a security audit*).
*   **Annotate the Tracker**: Mark subagent tasks in `{task-slug}-task.md` under `docs/plans/` using the format:
    `* [ ] [Subagent: @persona] Task name → Verify: [specific verification criteria]`
*   **Instantiate Dispatch Ticket**: Copy the template at `.agents/skills/collaborative-memory/templates/subagent_dispatch_template.md` to `docs/handoffs/subagent_dispatch.md`. Fill in the task scope, tools, and constraints.
*   **Handoff and Read Back**: After the subagent completes the task and writes its execution report in the ticket, verify the report, mark the task as complete (`[x]`), and archive or update the ticket.

### 2. Multi-Agent Role Handoffs
*   **Phase-based Handoff Gates**: Organize plans to follow the logical transition between personas (e.g., Plan & Scope `@orchestrator` ➡️ Architect & Design `@architect` ➡️ Implement `@engineer` ➡️ Test & Verify `@qa`).
*   **Handoff Gate Tasks**: Insert explicit handoff gates in your task tracker:
    `* [ ] [Handoff Gate] Phase Name → Hand off to @[PersonaName]`
*   **Serialize State**: Before handing off, run the handoff script (`python .agents/skills/collaborative-memory/scripts/compile_handoff.py`) to record the workspace state. Set the next target persona in `docs/handoffs/active_handoff.md`.

---

## 🏁 Verification & Walkthrough Compilation

1.  **Run the Verification Workflow**: Execute `/verify` to test changes using concrete commands. Do not assume or assert that code works without execution.
2.  **Generate Walkthrough**: Upon completion, compile a `walkthrough-{slug}.md` in the workspace detailing:
    *   *Change Registry*: All created, modified, or deleted files.
    *   *Verification Logs*: Precise terminal command outputs proving success.
    *   *Self-Review Check*: Clean code and security verification.
