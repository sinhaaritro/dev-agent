# SPEC-002: Agent Workflow Protocol Specification

- **Status**: Approved
- **Author**: @orchestrator
- **Created**: 2026-06-27
- **Target Persona**: @engineer

## 1. Overview
This specification defines the standard multi-phase workflow lifecycle, session resume mechanism, and escape hatch behaviors used by agents during complex implementation tasks. These stages govern how the agent transitions from planning and design alignment to coding, verification, and final delivery, ensuring structural rigor and alignment at each step.

## 2. Workflow Phase Matrix
Execution for complex or multi-file changes is structured into three discrete stages, accompanied by session recovery and interrupt-handling protocols.

### Path Index
| Stage / Mechanism | Path Spec | Description & Trigger Condition | Status | Date |
| :--- | :--- | :--- | :--- | :--- |
| **STAGE 1: PRE-CODING** | [Stage 1: Pre-coding](stage-1-pre-coding.md) | Planning & Design Alignment. Prepares context, designs solutions, and gathers user approval before code changes. | Approved | 2026-06-27 |
| **STAGE 2: CODING** | [Stage 2: Coding](stage-2-coding.md) | Implementation & Writing. Executes tasks defined in approved plans following clean code standards. | Approved | 2026-06-27 |
| **STAGE 3: POST-CODING** | [Stage 3: Post-coding](stage-3-post-coding.md) | Verification & Delivery. Runs validation tests, lint checks, and delivers walkthrough reports. | Approved | 2026-06-27 |
| **SESSION RESUME** | [Session Resume](session-resume.md) | Session continuity and handoff drift resolution. Reconstructs state on stateless start. | Approved | 2026-06-27 |
| **ESCAPE HATCH** | [Escape Hatch](escape-hatch.md) | Managing interruptions and off-topic queries without breaking the active plan state. | Approved | 2026-06-27 |

> 📊 **[Open the Visual Summary →](summary.html)** for an interactive view of the workflow phases, Specialist Agent plug-ins, and state transitions.
