tags: [adr, engine, handoff, sdsc]

# ADR-004: Engine-Recorded Handoff with Durable Marker

Status: Accepted
Date: 2026-08-19
Source: docs/specs/008-post-approval-handoff-guard.md

## Context

A prose-only handoff rule can be silently skipped. The handoff needs to be verifiable by the next session and durable past the scratchpad.

## Decision

Add a `handoff` mode to `promote_spec.py`. It validates the spec is `Status: APPROVED` (Lane A also requires at least one ADR whose `Source:` points at the spec; Lane B allows zero), writes `docs/temp/handoff.md` (ephemeral), and stamps `Handoff: <YYYY-MM-DD>` onto the spec's status header (durable).

## Consequences

A new session can confirm the handoff happened by checking the marker, making the guard enforceable rather than aspirational. Adds one engine mode and a header edit; the scratchpad file remains ephemeral and is purged by task-cleaner, while the header marker persists.