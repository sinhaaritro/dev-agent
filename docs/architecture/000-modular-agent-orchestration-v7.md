# Modular Agent Orchestration Architecture
## Master Reference Specification & Architectural Blueprint (Version 7)

---

## 1. Executive Summary & Core Philosophy

This specification defines a **harness-agnostic, model-agnostic, spec-driven architecture** for AI developer agents working in any codebase.

Version 7 introduces a formal **Execution Lane Taxonomy (Lanes A, B, C, D)**, **Session Context Detection (Interactive vs. Non-Interactive)**, and an explicit **Autonomy Policy Engine**. By categorizing tasks by scope and blast radius, governing headless execution (e.g., CI/CD runs, background daemons) via fail-closed policies, enforcing Socratic guided inquiry, and isolating parallel agent state via Git Worktrees, this architecture prevents unguided code editing, context pollution, and silent breaking changes across interactive and autonomous harnesses alike.

### Core Principles
1. **Explicit Execution Lane Taxonomy:** Every incoming request is triaged into one of four distinct lanes (D: Read-Only, C: Micro-Edit, B: Scoped Multi-File, A: Full SDLC) with explicit escalation rules, documentation requirements, and gate behaviors.
2. **Session Context & Autonomy Control:** The system distinguishes interactive sessions (human in chat UI) from non-interactive sessions (headless CI/CD). Non-interactive sessions operate under a declared Autonomy Policy (`supervised` fail-closed vs. `autonomous` logged defaults).
3. **Socratic Inquiry Gate & Guided Communication:** The AI is forbidden from making unguided assumptions on architecture or asking vague open-ended questions. It must frame queries as guided multiple-choice options with recommended defaults using a standardized 5-tag response header.
4. **Dynamic Plug-and-Play Skill Ecosystem:** Skills are classified into **Core System Skills** (mandatory baseline engine) and **Optional Extension Skills** (plug-and-play capabilities). Skills are dynamically indexed via `MAP.md` without hardcoded references in the router.
5. **Human-First Visibility (`docs/` Shared Space):** All human-facing artifacts (Specs, Architectural Decisions, Active Task State) reside in `docs/`, ensuring visibility across all IDEs and file explorers.
6. **Zero Git Noise Scratchpad (`docs/temp/`):** Ephemeral session state, execution logs, and draft plans live in a gitignored `docs/temp/` folder, keeping git commit history clean.
7. **Parallel Execution via Git Worktree Isolation:** Multi-agent execution runs in dedicated Git Worktrees (`1 Worktree = 1 Branch = 1 Isolated docs/temp/`), preventing state cross-contamination.
8. **Circuit Breakers for Safety:** Prevent infinite agent retry loops and token burn by enforcing explicit escalation thresholds (maximum 3 failed retries) for human handoff.

---

## 2. Directory Structure & File Lifecycle

The repository architecture maintains a strict boundary between **Machine Space** (`.agents/`) and **Human + AI Shared Space** (`docs/`).

### Standard Architecture Directory Map

```text
<repository-root>/
├── AGENT.md                              <-- Primary System Prompt & Autonomy Policy
│
├── docs/                                 <-- HUMAN + AI SHARED SPACE (Committed to Git)
│   ├── specs/                            <-- Permanent Functional & Technical Specs
│   │   └── 001-feature-spec.md
│   ├── decisions/                        <-- Architectural Decision Records (ADR)
│   │   └── adr-001-database-selection.md
│   ├── architecture/                     <-- High-level system diagrams & overviews
│   │
│   └── temp/                             <-- EPHEMERAL WORKING MEMORY (Gitignored)
│       ├── .gitignore                    <-- Ignores all contents except itself
│       ├── active-task.md                <-- Working memory & current state tracker
│       ├── draft-plan.md                 <-- Unapproved draft plan being iterated on
│       ├── escalation.md                 <-- Circuit breaker log / Human handoff report
│       ├── gate-log.md                   <-- Persistent audit log for autonomous choices
│       └── handoff-payload.md            <-- Inter-agent session handoff context
│
└── .agents/                              <-- MACHINE SPACE (AI System Internals)
    ├── MAP.md                            <-- Dynamic Metadata Index (Generated Map)
    ├── skills/                           <-- Capabilities & Governance Ecosystem
    │   │
    │   ├── [ CORE SYSTEM SKILLS - MANDATORY BASELINE ]
    │   ├── phase-protocol/               <-- Meta-Skill (Process Control & SDLC Driver)
    │   │   ├── SKILL.md                  <-- Phase Router & Communication Schema
    │   │   └── references/
    │   │       ├── plan.md               <-- Phase 1 Checklist & Socratic Gate
    │   │       ├── build.md              <-- Phase 2 Checklist & Test Loops
    │   │       └── review.md             <-- Phase 3 Checklist & Sign-off
    │   ├── auto-router/                  <-- Intent Triage & Lane Taxonomy Engine
    │   │   └── SKILL.md
    │   ├── map-generator/                <-- Index Sync & Timestamp Cache Check
    │   │   └── SKILL.md
    │   ├── spec-builder/                 <-- Spec Drafting & Promotion Pipeline
    │   │   ├── SKILL.md
    │   │   └── references/
    │   │       ├── implementation-plan-template.md
    │   │       └── todo-checklist-format.md
    │   ├── verification-runner/          <-- Test Execution & Circuit Breakers
    │   │   └── SKILL.md
    │   ├── task-cleaner/                 <-- Garbage Collection on Acceptance
    │   │   └── SKILL.md
    │   │
    │   ├── [ OPTIONAL EXTENSION SKILLS - PLUG & PLAY ]
    │   ├── git-worktree/                 <-- (Optional) Worktree Lifecycle & Teardown
    │   │   └── SKILL.md
    │   ├── technical-explainer/          <-- (Optional) Deep-Dive & Tech Comparisons
    │   │   └── SKILL.md
    │   ├── refactoring/                  <-- (Optional) Code Smell Audit & Patterns
    │   │   └── SKILL.md
    │   ├── react/                        <-- (Optional) Tech Stack Guidelines
    │   │   └── SKILL.md
    │   └── database/                     <-- (Optional) Migration Best Practices
    │       ├── SKILL.md
    │       └── references/
    │           └── migration-patterns.md
    │
    └── scripts/                          <-- Utility Scripts (e.g., Map Generator Script)
```

---

## 3. Communication Protocol — Socratic Gate & Response Schema

### 1. The Socratic Inquiry Protocol

Ambiguity during Phase 1 (Planning) or Scope Escalation is resolved via guided multiple-choice inquiry, never open-ended questions.

* **Guided Multiple-Choice Schema:** Frame queries as concrete options with a recommended default choice:
  * *Option A (Recommended):* Best for performance/security, trade-offs stated.
  * *Option B:* Alternative approach, trade-offs stated.
* **Blocking vs. Non-Blocking Gates:**
  * **Blocking Question (Gate):** Touches security, database schemas, public APIs, or Lane A criteria. Execution halts until answered or governed by Autonomy Policy.
  * **Non-Blocking Question:** Touches minor internal scope. AI states the default and proceeds immediately.

### 2. Interactive vs. Non-Interactive Session Detection

Before the first gate fires, the harness session is classified as either:
* **Interactive:** A human can plausibly respond within the current turn (chat UI, IDE copilot session).
* **Non-Interactive:** The harness runs headless with no human in the loop for this invocation (CI-triggered agent, scheduled batch job, background daemon run).

This classification comes from the harness's invocation context. If the harness provides no signal either way, **default to Non-Interactive** (fail toward caution).

### 3. Gate Behavior by Session Type

| Gate Type | Interactive Session | Non-Interactive Session |
| :--- | :--- | :--- |
| **Non-blocking** | State default, proceed immediately | State default, proceed immediately (unchanged) |
| **Blocking** | Halt, await human reply | Governed by **Autonomy Policy** (below) — never hangs indefinitely |

### 4. Autonomy Policy (Required Config for Non-Interactive Runs)

Every repository using this architecture declares an explicit autonomy level in `AGENT.md` or harness configuration:

```yaml
autonomy_level: supervised   # Options: supervised | autonomous
```

* **`supervised` (Default if unset):** A blocking gate hit in a non-interactive session **fails closed**. The task halts, writes `docs/temp/escalation.md` with the pending question and its options, and exits cleanly without making the change. Nothing ships without a human answering, even if the CI run ends in "blocked" rather than "success" or "failure."
* **`autonomous`:** A blocking gate hit in a non-interactive session resolves to the **Recommended Option** automatically, subject to strict audit rules:
  1. The choice is logged verbatim to `docs/temp/gate-log.md` (question, options, choice made, timestamp)—this file is **never purged** by `task-cleaner` until a human explicitly reviews it.
  2. Any resulting spec promoted to `docs/specs/` is tagged `Status: PROVISIONAL — AUTONOMOUS DEFAULT` until a human explicitly clears the tag.
  3. `autonomous` mode **never applies** to gates classified under Lane A's database schema, authentication, or public-API criteria—those **always fail closed** regardless of policy. Autonomy can shortcut minor architectural defaults; it cannot shortcut irreversible or security-relevant choices.

### 5. The 4-Block Response Schema

Every response generated by the agent must carry an updated 5-tag status header:

```text
[STATUS: Phase 1 - Planning | Task: AUTH-001 | Lane: B | Worktree: feature/auth | Session: Interactive]

1. SUMMARY OF UNDERSTANDING
Brief 1-sentence recap of user input or processed state.

2. ACTIONS TAKEN / DISCOVERY
Summary of files inspected, code searched, or draft plans written to docs/temp/.

3. SOCRATIC GATE / DECISION PROPOSAL
Targeted multiple-choice options with recommended defaults (if ambiguity exists).

4. NEXT STEP
Clear statement of what execution step occurs upon human reply or autonomous resolution.
```

---

## 4. Execution Lane Taxonomy

The `auto-router` skill classifies every incoming prompt into exactly one of four lanes before any other skill runs. Lane assignment is re-evaluated continuously during execution—a task can escalate mid-flight, but it can never silently de-escalate.

### Lane Definitions

| Lane | Name | Scope Criteria | Docs Artifact | Socratic Gate | Verification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **D** | **Read-Only / Informational** | No file mutations. Explanations, comparisons, code Q&A. | None | None — informational, non-mutating | None |
| **C** | **Micro-Edit** | Single file. No schema, public API, auth, or dependency changes. Diff under ~30 lines. | None (inline diff output) | Non-blocking only | Single pass; 3-fail escalates to Lane B |
| **B** | **Scoped Multi-File Edit** | 2–5 files. No schema/API/auth/security surface touched. No new external dependencies. | Abbreviated `draft-plan.md` (Sections 1, 3, 4 only) | Non-blocking by default; blocking only if scope creeps toward Lane A criteria | Full circuit breaker (3-retry) |
| **A** | **Full SDLC** | >5 files, OR touches database schema, public API contracts, auth/security, or introduces a new architectural dependency. | Full `implementation-plan-template.md`, promoted to `docs/specs/` on acceptance | Blocking mandatory for every architectural decision point | Full circuit breaker + review phase |

### Escalation Rules
1. **Upward escalation is automatic and silent-safe:** If execution reveals a criterion for a higher lane (e.g., a Lane C edit turns out to require touching an auth middleware), the router immediately reclassifies the task, halts, and reports the reclassification to the human before continuing—it does not ask permission to escalate, only announces it.
2. **Downward escalation requires explicit human confirmation:** A task never quietly downgrades from A to B, since that would mean skipping planning artifacts already assumed to exist.
3. **Ambiguous lane assignment defaults to the higher lane:** If a prompt could plausibly be Lane B or Lane A, the router assigns A. The cost of over-scoping a small task is lower than the cost of under-scoping a schema change.
4. **Lane D never escalates automatically:** If a "read-only" request implicitly asks for a code change (*"explain this function, then fix the bug you find"*), the router splits it: answer in Lane D, then re-triage the fix request separately.

### Worked Examples
* *"What's the time complexity of this sort?"* $\rightarrow$ **Lane D**.
* *"Rename this variable in `utils.ts`."* $\rightarrow$ **Lane C**.
* *"Extract this logic into a shared helper used by three call sites."* $\rightarrow$ **Lane B**.
* *"Add a new `refresh_token` column and update the auth flow."* $\rightarrow$ **Lane A** (schema + auth trigger, regardless of file count).

---

## 5. Skills Catalog: Core vs. Optional Classification

Skills are strictly divided into **Core System Skills** (required to operate the baseline framework) and **Optional Extension Skills** (added on-demand per repository).

### Skills Classification Matrix

| Skill Folder | Type | Requirement | Function |
| :--- | :--- | :--- | :--- |
| `phase-protocol/` | Meta-Skill | **MANDATORY CORE** | Process governance, SDLC phase routing, tool permissions, Socratic gate. |
| `auto-router/` | Core System | **MANDATORY CORE** | Triage intent, assign lanes (A/B/C/D), monitor scope escalation. |
| `map-generator/` | Core System | **MANDATORY CORE** | Check timestamp freshness, scan skill headers, rebuild `.agents/MAP.md`. |
| `spec-builder/` | Core System | **MANDATORY CORE** | Enforce plan templates, draft specs in `docs/temp/`, manage promotion. |
| `verification-runner/`| Core System | **MANDATORY CORE** | Execute build/test scripts, track 3-retry limit, log escalation reports. |
| `task-cleaner/` | Core System | **MANDATORY CORE** | Purge `docs/temp/` scratchpad upon human acceptance/completion. |
| `git-worktree/` | Extension | *OPTIONAL* | Manage worktree creation, isolation rules, and teardown scripts. |
| `technical-explainer/`| Extension | *OPTIONAL* | First-principles deep-dive explanations, technology comparison matrices. |
| `refactoring/` | Extension | *OPTIONAL* | Code smell identification, pattern transformations, risk-scored diff proposals. |
| `react/`, `database/` | Extension | *OPTIONAL* | Domain tech stack rules, framework patterns, migration guidelines. |

### Detailed Skill Descriptions

#### Core System Skills (Mandatory Baseline)
1. **`phase-protocol` (Meta-Skill):** Drives SDLC phases (Plan, Build, Review). Enforces tool permissions (read-only during planning), loads `/references/plan.md`, `build.md`, and `review.md`, and enforces the 4-Block Response Schema.
2. **`auto-router` (Triage & Lane Engine):** Initial gatekeeper skill. Reads prompts, queries `.agents/MAP.md` for skill tag matches, assigns Execution Lanes (A, B, C, D), and triggers upward escalation if edit scope expands.
3. **`map-generator` (Index Sync):** Compares skill file timestamps against `.agents/MAP.md`. Regenerates `MAP.md` headers automatically when skills are added or modified.
4. **`spec-builder` (Spec Lifecycle & Templates):** Manages specification drafting. Uses `references/implementation-plan-template.md` to write `docs/temp/draft-plan.md` and promotes approved specs to `docs/specs/`.
5. **`verification-runner` (Test Runner & Circuit Breaker):** Executes local verification scripts. Tracks the 3-attempt retry counter; if 3 consecutive attempts fail, halts execution and logs `docs/temp/escalation.md`.
6. **`task-cleaner` (Garbage Collector):** Resets `docs/temp/` upon human task acceptance, purging ephemeral scratchpads to prepare for the next session (preserves unreviewed `gate-log.md`).

#### Optional Extension Skills (Plug-and-Play)
1. **`git-worktree` (Optional):** Teaches the agent to spawn isolated working directories (`git worktree add`), set up branch-specific `docs/temp/` paths, and perform teardowns upon task completion.
2. **`technical-explainer` (Optional):** Used when users request concept explanations or tech stack comparisons. Generates structured trade-off matrices (Pros/Cons, Latency, Cost) and uses a Socratic layered approach.
3. **`refactoring` (Optional):** Used when users request code refactoring. Analyzes code smells, proposes design patterns, assigns a risk score, and defines a safety verification checklist.
4. **Domain Tech Stack Skills (Optional):** Language and framework skills (e.g., `react/`, `database/`, `docker/`). Contain stack-specific guidelines, anti-patterns, and migration rules.

---

## 6. Dynamic Skill Discovery (Zero Hardcoding)

The `auto-router` **does not hardcode** skill names. All skill discovery is fully dynamic via `.agents/MAP.md`.

```text
1. DEVELOPER DROPS NEW SKILL: Folder added to .agents/skills/graphql/SKILL.md
   (Contains header metadata: trigger_tags: ["graphql", "apollo", "schema"])
                                   │
                                   ▼
2. MAP GENERATOR SYNC: map-generator detects new skill timestamp 
   and updates .agents/MAP.md.
                                   │
                                   ▼
3. USER PROMPT: "How do I query this GraphQL endpoint?"
                                   │
                                   ▼
4. DYNAMIC MATCHING: auto-router checks MAP.md tags 
   --> Matches "graphql" tag --> Loads .agents/skills/graphql/SKILL.md!
                                   │
                                   ▼
5. FALLBACK BEHAVIOR: If no matching extension skill exists in MAP.md,
   auto-router executes the prompt via baseline defaults (Lane A, B, C, or D).
```

---

## 7. Artifact Templates & Progress Tracking

Standardized templates are stored inside `.agents/skills/spec-builder/references/` to ensure identical formatting across all sessions.

### Implementation Plan Template (`implementation-plan-template.md`)
Drafted in `docs/temp/draft-plan.md` during Phase 1 and promoted to `docs/specs/<id>-<feature>.md`:

```text
# [SPEC-ID]: Feature Title
Status: DRAFT | Phase: 1-Plan | Author: AI Agent | Date: YYYY-MM-DD

## 1. Goal & Context
1-2 sentences explaining the business/technical goal.

## 2. Architectural Decisions & Trade-offs
Key technical choices made, alternative options considered, and trade-offs.

## 3. Affected Files & Scope
- Modified: src/auth/service.ts
- Created: src/auth/jwt-strategy.ts
- Deleted: none

## 4. Actionable TODO Checklist
- [ ] Step 1: Create JWT strategy helper in src/auth/jwt-strategy.ts.
- [ ] Step 2: Implement validation method in src/auth/service.ts.
- [ ] Step 3: Add unit tests in tests/auth/service.test.ts.

## 5. Verification Commands
- Build Command: npm run build
- Test Command: npm test -- tests/auth/service.test.ts

## 6. Rollback Strategy
Instructions on reverting edits if verification fails 3 times.
```

### Actionable TODO Progress Tracker
During Phase 2 (Build), the AI updates `draft-plan.md` checkboxes in real-time:
* `- [ ] Step 1: Pending` $\rightarrow$ Task has not started.
* `- [/] Step 1: In Progress` $\rightarrow$ Active editing underway.
* `- [x] Step 1: Completed` $\rightarrow$ Code written and local verification passed.

---

## 8. Parallel Execution & Git Worktree Memory Isolation

To support concurrent AI agent sessions without state collision, the architecture relies on **Git Worktree Isolation**.

```text
/home/user/workspace/project-main/            <-- Worktree 1 (main branch)
    └── docs/temp/                            <-- Isolated main task state

/home/user/workspace/project-feature-auth/    <-- Worktree 2 (feature/auth branch)
    └── docs/temp/                            <-- Isolated auth task state

/home/user/workspace/project-hotfix-billing/  <-- Worktree 3 (hotfix/billing branch)
    └── docs/temp/                            <-- Isolated billing task state
```

### Worktree Operating Rules
1. **One Worktree = One Task:** Each parallel agent runs in a distinct physical Git Worktree directory on disk.
2. **FileSystem Isolation:** Because `docs/temp/` lives inside the physical path of a specific worktree, working memory is physically isolated.
3. **Clean Teardowns:** Removing a git worktree (`git worktree remove`) cleanly purges that session's ephemeral scratchpad without affecting main repository state.

---

## 9. Circuit Breakers & Protected File Controls

### Escalation Protocol (Circuit Breaker)
1. **Max Retry Threshold:** Maximum of **3 consecutive failed attempts** at fixing a build error, test failure, or syntax issue.
2. **Action on Threshold Reached:**
   * Immediately cease all code modifications.
   * Revert uncommitted dirty edits if they break build integrity.
   * Generate `docs/temp/escalation.md` detailing attempts, error logs, hypothesis, and remediation options.
   * Halt execution and request Human Handoff (**AI-to-Human Escalation**).

### Guardrails & Protected File Controls

Regardless of the active phase or skill, the agent is forbidden from editing or deleting the following without explicit human confirmation in every chat session:
* Environment and secrets files (`.env*`)
* Security credentials, keys, certificates
* Package manager lockfiles (unless executing approved dependency commands)
* Existing Architectural Decision Records (`docs/decisions/*`)

---

## 10. Human-Centric State & Memory Architecture

Memory is strictly divided into **Ephemeral Working Memory** (gitignored scratchpad) and **Persistent Memory** (version-controlled repository knowledge).

### Memory Lifecycle & Promotion Pipeline

```text
                  Incoming Requirement
                           │
                           ▼
             ┌───────────────────────────┐
             │   EPHEMERAL SCRATCHPAD    │  <-- docs/temp/ (GITIGNORED)
             │   • docs/temp/draft-plan  │      Zero git noise during iteration
             └─────────────┬─────────────┘
                           │
                           ▼
             [ Human Acceptance Gate Passed ]
                           │
                           ├─────────────────────────────────────────┐
                           ▼                                         ▼
             ┌───────────────────────────┐             ┌───────────────────────────┐
             │     PROMOTED SPEC         │             │      TASK CLEANER         │
             │   • docs/specs/001.md     │             │ • Purges docs/temp/*      │
             │   (COMMITTED TO GIT)      │             │   (Preserves gate-log.md) │
             └───────────────────────────┘             └───────────────────────────┘
```

---

## 11. Dynamic Map Generator & Progressive Context Loading

To maintain maximum context window efficiency, the architecture uses the `map-generator` skill.

### Indexing & Cache Invalidation System
* **Function:** Scans all skill folders inside `.agents/skills/`.
* **Timestamp Check:** Compares skill file modification times against `.agents/MAP.md`. If skills are newer, `map-generator` runs automatically before prompt processing.
* **Output File:** Compiles metadata into `.agents/MAP.md`.

---

## 12. Tooling & Harness Execution Strategy

| Execution Layer | Preferred Model Tier | Example Harnesses | Key Responsibility |
| :--- | :--- | :--- | :--- |
| **Phase 1: Planning (`references/plan.md`)** | SOTA Reasoning Models | Claude Code, Gemini CLI, Cursor, Windsurf | Requirements analysis, functional spec creation, draft plan generation in `docs/temp/`. |
| **Phase 2: Building (`references/build.md`)** | Local or SOTA Models | Ollama, DeepSeek Local, Roo Code, Aider, OpenCode, Pi.dev, Kilo Code | Fast-path edits, procedural code execution, test execution, micro-refactoring. |
| **Phase 3: Review (`references/review.md`)** | SOTA / Specialized Models | Claude Code, Gemini CLI, Cursor | Code quality audit, security analysis, spec promotion to `docs/specs/`, ADR generation. |

---

## 13. Version 7 Summary Verification Checklist

Before deploying via `npx`, confirm that the framework satisfies:

* [x] **Execution Lane Taxonomy:** Classifies prompts into Lanes D, C, B, A with clear criteria, artifacts, and verification rules.
* [x] **Automatic Upward Escalation:** Reclassifies tasks upward silently-safe when blast radius expands; requires human confirmation to de-escalate.
* [x] **Session Context Detection:** Distinguishes Interactive from Non-Interactive sessions, defaulting to Non-Interactive on ambiguity.
* [x] **Autonomy Policy Engine:** Enforces `supervised` fail-closed behavior by default and audit-logged `autonomous` resolution for background runs.
* [x] **Socratic Gate & 5-Tag Header:** Enforces guided multiple-choice options with defaults and a 5-tag response status header.
* [x] **Git Worktree Memory Isolation:** Supports multi-agent parallel execution without `docs/temp/` collisions (`1 Worktree = 1 Isolated Scratchpad`).
* [x] **Skills Catalog Classification:** Explicitly classifies skills into **Core System Skills** (mandatory 6) and **Optional Extension Skills** (`git-worktree`, `technical-explainer`, `refactoring`, tech stacks).
* [x] **Dynamic Skill Discovery:** `auto-router` matches skills dynamically via `MAP.md` tags with zero hardcoding.
* [x] **Task Garbage Collection:** Purges ephemeral `docs/temp/` scratchpad upon human acceptance while preserving unreviewed `gate-log.md`.
* [x] **100% Harness Agnostic:** Works identically across Cursor, Claude Code, Windsurf, Roo Code, Aider, OpenCode, and Gemini CLI.