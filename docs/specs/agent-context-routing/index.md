# SPEC-001: Agent Context & Routing Specification

- **Status**: Approved
- **Author**: @orchestrator
- **Created**: 2026-06-24
- **Target Persona**: @engineer

## 1. Overview
This specification details how the agent dynamically routes user requests based on intent and adjusts the context loaded into the LLM context window.

## 2. Request Routing Matrices
For each message classification, a specific set of rules, personas, modes, and tools are loaded to tailor the agent's behavior and minimize context footprint.

### Path Index
| Request Type | Path Spec | Description & Trigger Condition | Status | Date |
| :--- | :--- | :--- | :--- | :--- |
| **QUESTION** | [QUESTION Path](question-path.md) | Information queries, conceptual questions, or teaching requests. Load when answering user questions. | Approved | 2026-06-24 |
| **ANALYSIS** | [ANALYSIS Path](analysis-path.md) | Code audits, architecture evaluations, or repository analysis. Load when performing codebase reviews. | Approved | 2026-06-24 |
| **BUG FIX** | [BUG FIX Path](bug-fix-path.md) | Debugging failures, fixing errors, or troubleshooting. Load when resolving runtime crashes or unit test failures. | Approved | 2026-06-24 |
| **SIMPLE CODE** | [SIMPLE CODE Path](simple-code-path.md) | Minor edits to single files. Load when executing simple standalone edits. | Approved | 2026-06-24 |
| **COMPLEX CODE** | [COMPLEX CODE Path](complex-code-path.md) | Multi-file code modifications, refactorings, or new features. Load when initiating structured plans. | Approved | 2026-06-24 |
| **DESIGN/UI** | [DESIGN/UI Path](design-ui-path.md) | Frontend layouts, interface assets, styling, or mockup prototyping. Load when planning visual changes. | Approved | 2026-06-24 |
| **TOOLING** | [TOOLING Path](tooling-path.md) | Dependency installations, env files, linting, formatting, compiling, and deploying. Load during environment setup and pre-ship. | Approved | 2026-06-24 |
| **DOCUMENTATION** | [DOCUMENTATION Path](documentation-path.md) | Drafting, editing, or auditing readme, specifications, ADR files, and manuals. Load when writing/reviewing docs. | Approved | 2026-06-24 |
| **TECH DEBT REDUCTION** | [TECH DEBT REDUCTION Path](tech-debt-reduction-path.md) | Managing files/folders, bulk renames/relocations, scratch pruning, and git tree hygiene. Load during workspace cleanup. | Proposed | 2026-06-24 |
| **SLASH CMD** | [SLASH CMD Path](slash-cmd-path.md) | Executing custom slash workflows (e.g. `/verify`). Load when handling slash commands. | Approved | 2026-06-24 |

> 📊 **[Open the Visual Summary →](summary.html)** for an interactive, tabbed view of all path traces, escalation rules, approval gates, and system comparison.
