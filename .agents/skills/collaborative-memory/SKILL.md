---
name: collaborative-memory
description: Shared cross-session memory, documentation, and handoff system for humans and agents. Standardizes context pinning, multi-channel handovers, specs, ADRs, test reports, audit trails, and change logs under the root-level docs/ folder.
when_to_use: "Used at session startup to load state, when performing handoffs (AI-to-Human, AI-to-AI, Human-to-AI), or when producing/updating specifications, ADRs, test reports, audit logs, or changelogs."
---

# Collaborative Memory System (CMS)

CMS is a shared blackboard for **AI agents** and **human developers** to synchronize, document, and hand over tasks. It separates core instructions (kept in `.agents/`) from runtime states and engineering documentation (kept in the root `docs/` folder).

---

## 🏛️ Directory Layout (docs/)

All human-readable memory and operational output live in the root-level `docs/` directory:

```plaintext
docs/
├── MEMORY.md                 # Root memory index & pinned files list (max 200 lines)
├── project_profile.md        # Technical profile: domain, tech stack, rules (AI reference)
├── handoffs/                 # Handover tickets between AI, humans, and subagents
│   ├── active_handoff.md     # Current active handover state
│   └── handoff_history.log   # Chronological log of all handoffs
├── specs/                    # Requirements & specifications (PM / Human-to-AI)
│   ├── index.md              # Registry index of specs
│   └── SPEC-XXX-name.md      # Spec file
├── adr/                      # Architectural Decision Records (Architect / human)
│   ├── index.md              # Registry index of ADRs
│   └── ADR-XXX-name.md       # ADR file
├── tests/                    # QA verification reports
│   └── report-latest.md      # Last test runner execution output
├── audits/                   # Reviewer & security audit trail
│   └── session_audit.log     # Command logs, decisions, and security gates
└── changes/                  # Change tracking and package impact
    └── changelog.md          # File edits and side effects
```

---

## 🔄 1. The Collaboration Matrix (Handoffs)

All handoffs are serialized inside `docs/handoffs/active_handoff.md`.

### A. AI ➡️ Human (Task Blocked / Completed / Going Idle)
When pausing execution, requesting input, or finishing, write to `active_handoff.md`:
1.  **State**: Completed items vs. outstanding tasks.
2.  **Unresolved Socratic Questions**: Concrete choices/questions for the human.
3.  **Handoff Type**: Set `Type: ai_to_human`.
4.  **Action Required**: Direct steps the human must take.

### B. Human ➡️ AI (Task Launch / Guidance)
When delegating work to an agent:
1.  Human updates `active_handoff.md` with goals, setting `Type: human_to_ai`.
2.  Human links relevant requirements from `docs/specs/`.
3.  At startup, the agent reads `docs/handoffs/active_handoff.md` first.

### C. AI ➡️ AI (Stages, Subagents, and Multi-Agent Chat Transfer)
*   **Stage-to-Stage Handover**: When transitioning between roles (e.g. `@architect` to `@engineer` to `@qa`), the active agent updates the checklist and swaps the active persona target in `active_handoff.md`.
*   **Subagent Dispatch**: When spawning a subagent, the parent writes instructions to `docs/handoffs/subagent_dispatch.md` (files to edit, tools permitted, constraints, and the target execution `branch` and local `worktree_path`). The subagent reads this, executes within the worktree isolation, and returns its results.
*   **Chat-to-Chat Context Transfer**: Since chat windows are ephemeral, write the active session's mental model sync (uncommitted changes, files touched, current goals, active worktree branch, and test statuses) to `active_handoff.md` before ending a chat. A new agent in a new chat reads this to resume seamlessly.

---

## 📜 2. Session Start & Context Pinning Protocol

At the start of every session:

1.  **Load Handoff**: Read `docs/handoffs/active_handoff.md`. Reconstruct current goals and progress.
2.  **Check Pinned References**: Read `docs/MEMORY.md` and identify files listed under the `# Pinned Files` section.
3.  **Load Pinned Files**: Read each pinned file into active context (e.g. core specs, active ADRs).
4.  **Silent Application**: Apply memory context silently. Do NOT recite user preferences or conventions unless explicitly asked.

---

## 📄 3. Memory Artifact Formats & Templates

### A. Functional Spec Template
Path: `docs/specs/SPEC-XXX-name.md`
```markdown
# SPEC-XXX: [Title]

- **Status**: Draft | Approved | Implementing | Shipped
- **Author**: [Author Name]
- **Created**: YYYY-MM-DD
- **Target Persona**: @engineer

## 1. Overview
High-level description of what is being built.

## 2. Requirements & User Stories
- As a user, I want...
- Detailed functional flows.

## 3. Acceptance Criteria
- [ ] Criteria 1 (verifiable via test)
- [ ] Criteria 2 (manual check)
```

### B. Architectural Decision Record (ADR)
Path: `docs/adr/ADR-XXX-name.md`
```markdown
# ADR-XXX: [Decision Title]

- **Status**: Proposed | Accepted | Deprecated
- **Author**: @architect | [Name]
- **Date**: YYYY-MM-DD

## Context
What is the technical problem and its constraints?

## Decision
What is the chosen design/tech stack? Why?

## Consequences
- **Pros**: Benefits.
- **Cons**: Overheads or technical debt.
```

### C. Test Report Template
Path: `docs/tests/report-latest.md`
```markdown
# Test Report - YYYY-MM-DD HH:MM

- **Status**: 🟢 PASSING | 🔴 FAILING
- **Executor**: @qa | Human Developer
- **Command**: `task test`

## Summary
| Suite | Passed | Failed | Total | Coverage |
| :--- | :--- | :--- | :--- | :--- |
| Unit | X | Y | Z | % |
```

### D. Change List & Impact
Path: `docs/changes/changelog.md`
```markdown
# Changelog

## [Commit Hash / Version] - YYYY-MM-DD
- **Author**: @engineer | [Name]
- **Description**: Summary of modification.

### Modified Files
| File | Action | Side-effects / Impact |
| :--- | :--- | :--- |
| [file.py](file:///path/to/file.py) | MODIFY | Details |
```

### E. Project Profile Template
Path: `docs/project_profile.md`
```markdown
# Project Profile

## 📋 General Information
- **Project Name**: [Project Name]
- **Domain**: [Domain description]
- **Tech Stack**: [Comma-separated stack]
- **Repository Pattern**: [Monorepo / Single Package]
- **Purpose**: [Brief explanation]

## 🛠️ Build & Run Commands
- **Environment Init**: [Command]
- **Run Locally**: [Command]
- **Verify/Test**: [Command]

## 🏗️ Architectural Overview
- [Architectural details]
```

---

## 🚀 Workspace Initialization Protocol (For AI Agents)

When an AI agent is loaded into a repository that is not yet fully configured:

1. **Verify Root Files**:
   - Check if `Taskfile.yml` and `.gitignore` exist. If they are missing, run `python .agents/scripts/ensure_taskfile.py` to restore them from their templates.
2. **Handle Missing Project Profile**:
   - Check if `docs/project_profile.md` exists. If not, trigger the setup:
      - **Case A: Root `README.md` is present**:
        - Read and parse it to extract Project Name, Domain, Tech Stack, Purpose, and Guidelines (Active rules, Formatting, Testing, Git).
        - If the extracted tech stack, domain, or guidelines/alignment philosophy are incomplete or generic, **analyze the workspace files (package files, configuration files), dynamically suggest the best options to the human in chat**, and update `docs/project_profile.md` upon approval.
      - **Case B: Root `README.md` is missing**: 
        - Analyze the workspace files to identify the likely domain, tech stack, and alignment philosophy.
        - Prompt the user in chat with these **suggested options** to ask for confirmation or customization.
        - Ask the user if they would like you (the AI) to generate a standard root `README.md` file. If they approve, create it using `.agents/scripts/README.template.md` formatted with their input.
        - Initialize the CMS layout by running `python .agents/skills/collaborative-memory/scripts/init_docs.py all` with the confirmed details.
