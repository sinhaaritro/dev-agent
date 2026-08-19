---
name: auto-router
description: Intent triage & lane taxonomy engine - classifies every request into a lane, detects session type, monitors scope escalation
tags:
  - triage
  - lane
  - escalation
  - session
  - routing
metadata:
  version: 1.0.0
  author: AI Agent
scope: always
---

# Auto-Router

## Overview

The initial gatekeeper, run at every session start before phase-protocol. You classify each request into exactly one Execution Lane (D/C/B/A), detect the session type, surface candidate skills from `.agents/MAP.md`, and monitor scope escalation. Your output is a routing verdict for phase-protocol — you are not the decision authority and hold no gate authority.

## When to Use

- Every session start and every incoming prompt (mandatory second step of the boot chain).
- Mid-flight: whenever execution reveals a higher-lane criterion — re-run classification and announce the upward escalation.
- After `map-generator` reports `regenerated` — re-read `.agents/MAP.md` before matching.

## Instructions

1. **Classify the lane.** Load `references/lane-matrix.md` (single source of truth for criteria, escalation, session detection, examples). Walk top-down: non-mutating → D; single file, diff under ~30 lines, no schema/API/auth/deps → C; 2–5 files without a Lane-A surface → B; otherwise → A. Surface triggers (schema, public API, auth/security, new architectural dependency) outrank file count.
2. **Detect the session.** Interactive if a human can plausibly respond within the current turn; otherwise Non-Interactive. No harness signal → default Non-Interactive.
3. **Recall candidate skills (two stages).** Run the engine:
   `python .agents/skills/auto-router/scripts/match_skills.py "<prompt>"`
   Stage 1 is mechanical: the engine ranks MAP.md rows by tag hits, then description hits (4-char prefix), printing a `Match:` column. Stage 2 is your judgment — engine output is candidates only and can never exclude. Thin or zero candidates: re-read the full MAP.md and match by semantic relation; a skill with zero literal hits can still apply. Never treat absence from the engine as proof a skill does not apply.
4. **Hand off the verdict.** Emit: Lane (A/B/C/D), Session (Interactive/Non-Interactive), candidate skills, optional escalation flag. Phase-protocol consumes these into the `[STATUS: ...]` header and drives phases, gates, autonomy, and the 4-Block schema.

## Output Contract

Exactly: **Lane**, **Session**, **candidate skills**, optional **escalation flag**. You do not draft plans, write specs, or execute the task — you route it.

## Notes

- **Escalation is announce-only upward:** reclassify, announce (never ask permission), phase-protocol continues under the new lane. Never silently de-escalate.
- **Skill discovery goes through `.agents/MAP.md` only** — never hardcode skill names; re-read the index whenever `map-generator` reports `regenerated`.
- **Never match against a stale index:** if MAP.md is missing or `regenerated` was reported, refresh it first (system.md step 1) before triaging.
