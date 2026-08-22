tags: [adr, promotion, sdcl]

# ADR-002: ADRs Triggered by Decision, Not Lane

Status: Accepted
Date: 2026-08-18
Source: docs/specs/007-spec-first-lifecycle-core-skill.md

## Context

The previous rule wrote ADRs only for Lane A tasks, which let architectural
decisions from small tasks (Lane B, or a decision discovered mid-task) fall
through the cracks and never reach docs/decisions/ as durable knowledge.

## Decision

Any architectural decision at any lane (schema, public API, auth/security,
new dependency) gets a permanent ADR. Lane A mandates one per spec section-2
decision; Lane B writes one only if a decision surfaces, since its
abbreviated plan has no section 2.

## Consequences

Decisions from small tasks are preserved as durable knowledge instead of
being lost at task end. It maintains more records, and the agent must
exercise judgment about what qualifies as architectural.