# ADR: Mandatory Handoff Phase

Status: Accepted
Date: 2026-08-19
Source: docs/specs/008-post-approval-handoff-guard.md

## Context

Spec 007 D1 let the spec-producing session "either proceed in-session to build, or hand off". The birthday-tracker demo showed the agent coding immediately after approval, defeating spec-first separation.

## Decision

Make handoff mandatory. The in-session proceed option is removed from plan.md section 5; a new Phase 1.5 (Handoff) with a read-only checklist is added, and a session that produced an approved spec must stop there. Implementation runs only in a new session that reads the promoted spec.

## Consequences

Guarantees the approval gate truly ends Step 1, so coding can never follow approval in the same session. Costs one extra session per spec-producing task; spec sessions are cheap and the separation is the point of the lifecycle.