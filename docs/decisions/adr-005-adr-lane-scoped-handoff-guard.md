# ADR: Lane-Scoped Handoff Guard

Status: Accepted
Date: 2026-08-19
Source: docs/specs/008-post-approval-handoff-guard.md

## Context

The handoff guard must apply exactly where an approval gate exists. Lanes B and A produce specs; Lanes C and D have no plan or approval step.

## Decision

Enforce the guard for Lanes B and A only, and note in the phase-protocol contract that C/D are approval-free so agents never look for a handoff there.

## Consequences

Keeps the extra-session cost confined to spec-producing work and avoids confusion on read-only (D) and single-pass (C) tasks. Requires the lane-scope note to be carried in the phase-protocol checklist so the exclusion stays explicit.