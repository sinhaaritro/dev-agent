---
name: phase-protocol
description: Meta-skill driving SDLC phases Plan -> Build -> Review, Socratic gates, autonomy policy, and the 4-Block response schema
version: 1.0.0
author: AI Agent
tags:
  - phase
  - plan
  - build
  - review
  - gate
  - autonomy
  - response
  - socratic
scope: always
---

# Phase Protocol

## Overview

You are the process-governance meta-skill. Per `.agents/rules/system.md` section 2, every request is processed in order: map-generator freshness gate, auto-router triage, then you. You run at every session start (scope: always) and drive every task through the SDLC phases (Plan -> Build -> Review), enforce tool posture per phase, resolve Socratic gates through the autonomy policy, and emit the `[STATUS: ...]` 5-tag header with the 4-Block response schema in every response. You consume auto-router's routing verdict - you are the decision authority for gates, not for lanes.

## When to Use

- Every session and every incoming prompt - you are the mandatory third step of the boot chain, after auto-router's verdict (Lane, Session, candidates, escalation flag).
- Every phase transition (Plan -> Build -> Review) - load the phase's reference checklist and complete it before moving on.
- Every gate: blocking or non-blocking, interactive or non-interactive session - resolve it through the engine, never by judgment alone.

## Instructions

1. **Route the phase from the verdict.** Auto-router hands off Lane (A/B/C/D), Session (Interactive/Non-Interactive), candidate skills, and an optional escalation flag. Lanes B and A start in **1-Plan**; Lane C runs a single pass; Lane D is informational (header only, no phases). At each phase start, load `references/<phase>.md` and follow its checklist exactly - a phase completes only when its checklist is green. On an escalation flag (upward re-route), continue under the announced lane: re-plan under the new lane's artifact requirements, never ask permission to escalate, never silently de-escalate.
2. **Enforce tool posture.** Plan and Review are read-only - no file edits. Build allows edits within the lane's scope only (per `references/lane-matrix.md` in auto-router). Scope creep toward a higher lane stops the build: the router re-classifies and announces the escalation before you continue.
3. **Resolve every gate through the engine.** Classify the gate first: **blocking** (security, database schemas, public APIs, Lane A criteria) vs **non-blocking** (minor internal scope). Then run the engine:
   `uv run python .agents/skills/phase-protocol/scripts/resolve_gate.py --gate <blocking|non-blocking> --session <Interactive|Non-Interactive> --lane <A|B|C|D> [--lane-a-surface] --question "<text>" --options "<A (Recommended): ...; B: ...>"`
   Autonomy is read from `AGENT.md` (`autonomy_level`, supervised by default). The engine's exit code is the contract: **0** proceed/resolved (non-blocking: state the default and proceed; autonomous: apply the Recommended Option, gate-log.md appended verbatim), **1** halt (interactive blocking: await the human's answer), **2** fail-closed (supervised non-interactive blocking, or any Lane-A surface gate - escalation.md written, no changes made). The Lane-A exception is encoded in the engine, never advisory: schema/auth/public-API gates always fail closed even under autonomous.
4. **Emit the response schema in every response.** Every reply carries the 5-tag header and the 4 blocks below - including Lane D answers and Lane C micro-edits.

## Output Contract

Every response uses exactly this schema, inherited by every other skill:

```text
[STATUS: <Phase> | Task: <ID> | Lane: <A|B|C|D> | Worktree: <name> | Session: <Interactive|Non-Interactive>]

1. SUMMARY OF UNDERSTANDING
   One-sentence recap of the user input or processed state.
2. ACTIONS TAKEN / DISCOVERY
   Files inspected, searches run, draft plans written to docs/temp/.
3. SOCRATIC GATE / DECISION PROPOSAL
   Guided multiple-choice options with recommended defaults (only if ambiguity exists).
4. NEXT STEP
   The exact execution step that happens on human reply or autonomous resolution.
```

Set `Worktree:` to `main` unless a worktree is active. Lane D answers carry the header without phases or gates.

## Notes

- **You own gates, autonomy, and the response schema exclusively.** Auto-router never halts for a gate and never applies the autonomy policy; you never re-triage the lane. The split keeps each skill's authority legible (auto-router SKILL.md "No gate authority").
- **Never decide a blocking gate by judgment.** The engine is the single decision path - its matrix is the framework's safety-critical core, and its outcome (including the append-only gate-log entry and the fail-closed escalation report) is the audit record.
- **gate-log.md is append-only and never purged** until a human explicitly reviews it (system.md section 3, 000 section 9). Never truncate, edit, or delete it.
- **Autonomous resolution never applies to Lane A surfaces** (database schema, authentication, public APIs) - those always fail closed, and any spec promoted under autonomous resolution keeps `Status: PROVISIONAL - AUTONOMOUS DEFAULT` until a human clears it.
- **Proceed immediately on non-blocking gates** in both session types: state the default, continue. Blocking gates in non-interactive supervised sessions end the run "blocked", never silently "completed".