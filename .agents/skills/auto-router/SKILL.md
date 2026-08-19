---
name: auto-router
description: Intent triage & lane taxonomy engine - classifies every request into a lane, detects session type, monitors scope escalation
version: 1.0.0
author: AI Agent
tags:
  - triage
  - lane
  - escalation
  - session
  - routing
scope: always
---

# Auto-Router

## Overview

You are the initial gatekeeper. Per `.agents/rules/system.md` section 2, every request is processed in order: map-generator freshness gate, then you, then phase-protocol. You run at every session start (scope: always) and classify the incoming request into exactly one Execution Lane (D/C/B/A), detect the session type, surface candidate skills from `.agents/MAP.md`, and monitor scope escalation. Your output is a routing verdict for phase-protocol to consume - you are not the decision authority.

## When to Use

- Every session start and every incoming prompt - you are the mandatory second step of the boot chain.
- Mid-flight re-triage: whenever execution reveals a higher-lane criterion, re-run classification and announce the upward escalation.
- After `map-generator` reports `regenerated` - re-read `.agents/MAP.md` before matching anything against it.

## Instructions

1. **Classify the lane.** Load `references/lane-matrix.md` (the single source of truth for lane criteria, escalation rules, session detection, and worked examples). Walk the classification order top-down: non-mutating -> D; single-file diff under ~30 lines with no schema/API/auth/deps -> C; 2-5 files without a Lane-A surface -> B; otherwise -> A. Surface triggers (schema, public API, auth/security, new architectural dependency) outrank file count.
2. **Detect the session.** Interactive if a human can plausibly respond within the current turn; otherwise Non-Interactive. When the harness gives no signal, default to Non-Interactive.
3. **Recall candidate skills (two stages).** Run the engine:
   `python .agents/skills/auto-router/scripts/match_skills.py "<prompt>"`
   Stage 1 is mechanical: the engine ranks rows of `.agents/MAP.md` by tag hits, then description hits (4-char prefix matching), and prints a `Match:` column showing which tokens hit. Stage 2 is judgment, and it is yours: **the engine output is candidates only and can never exclude**. When candidates are thin (or zero), re-read the full `.agents/MAP.md` and match by semantic relation to each skill's description - a skill with zero literal hits can still be the right one. Never treat the engine's absence of a skill as proof it does not apply.
4. **Hand off the verdict.** Emit the routing verdict: Lane (A/B/C/D), Session (Interactive/Non-Interactive), candidate skills, and an optional escalation flag. Phase-protocol consumes these into the `[STATUS: ... | Lane: X | Session: Y]` header and drives phases, gates, autonomy policy, and the 4-Block response schema.

## Output Contract

Your output is exactly: **Lane**, **Session**, **candidate skills**, optional **escalation flag**. These feed phase-protocol's `[STATUS: ...]` header and phase routing. You do not draft plans, you do not write specs, and you do not execute the task - you route it.

## Notes

- **No gate authority.** Socratic gates (blocking/non-blocking), the autonomy policy, and the 4-Block response schema are exclusively phase-protocol's domain. You never halt for a gate and never apply autonomy policy.
- **Escalation is announce-only upward.** If execution reveals a higher-lane criterion, re-classify, announce the escalation (never ask permission), and phase-protocol continues under the new lane. Never silently de-escalate.
- **Never hardcode skill names.** Skill discovery goes through `.agents/MAP.md` only - the engine reads the index, and you re-read it whenever `map-generator` reports `regenerated`.
- **Never match against a stale index.** If `MAP.md` is missing or `map-generator` reports `regenerated`, refresh it first (system.md section 2 step 1) before triaging.