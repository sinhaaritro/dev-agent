---
name: phase-protocol
description: Meta-skill driving SDLC phases Plan -> 1.5-Handoff -> Build -> Review, Socratic gates, autonomy policy, and the 4-Block response schema
tags:
  - phase
  - plan
  - build
  - review
  - gate
  - autonomy
  - response
  - socratic
metadata:
  version: 1.0.0
  author: AI Agent
scope: always
---

# Phase Protocol

## Overview

The process-governance meta-skill, run after auto-router's verdict. You drive every task through the SDLC phases (Plan → 1.5-Handoff → Build → Review), enforce tool posture per phase, resolve Socratic gates through the autonomy policy, and emit the 5-tag header with the 4-Block schema in every response. You consume auto-router's verdict — you own gates, never lane triage.

## When to Use

- Every session and every incoming prompt (mandatory third step of the boot chain).
- Every phase transition — load ONLY that phase's reference checklist (never all references) and complete it before moving on.
- Every gate (blocking or non-blocking, any session type) — resolve through the engine, never by judgment alone.

## Instructions

1. **Route the phase from the verdict.** Lanes B and A start in 1-Plan and MUST end it at 1.5-Handoff (references/handoff.md) — the approval step promotes the spec and records the handoff, and the session stops there; **build never follows approval in the same session**. Lane C is a single pass; Lane D is informational (header only, no phases); C/D have no approval step, so no handoff. At each phase start, load ONLY `references/<phase>.md` — never preload all references — and follow its checklist exactly; a phase completes only when its checklist is green. On an escalation flag, continue under the announced lane: re-plan under the new lane's artifact requirements, never ask permission, never silently de-escalate.
2. **Enforce tool posture.** Plan, Handoff, and Review are read-only — no file edits. Build allows edits within lane scope only (per auto-router's `references/lane-matrix.md`). Scope creep toward a higher lane stops the build: the router re-classifies and announces the escalation before you continue.
3. **Resolve every gate through the engine.** Classify first: **blocking** (security, database schemas, public APIs, Lane A criteria) vs **non-blocking** (minor internal scope). Then run:
   `python .agents/skills/phase-protocol/scripts/resolve_gate.py --gate <blocking|non-blocking> --session <Interactive|Non-Interactive> --lane <A|B|C|D> [--lane-a-surface] --question "<text>" --options "<A (Recommended): ...; B: ...>"`
   Autonomy is read from `AGENTS.md` (`autonomy_level`, supervised by default). Exit code is the contract: **0** proceed/resolved (non-blocking: state the default and proceed; autonomous: apply the Recommended Option, gate-log.md appended verbatim); **1** halt (interactive blocking: await the human's answer); **2** fail-closed (supervised non-interactive blocking, or any Lane-A surface gate — escalation.md written, no changes made). The Lane-A exception is encoded in the engine, never advisory: schema/auth/public-API gates always fail closed even under autonomous.
4. **Emit the response schema in every response** — every reply carries the 5-tag header and the 4 blocks below, including Lane D answers and Lane C micro-edits.

## Output Contract

Every response uses exactly this schema, inherited by every other skill:

```text
[STATUS: <Phase> | Task: <ID> | Lane: <A|B|C|D> | Worktree: <name> | Session: <Interactive|Non-Interactive>]

1. SUMMARY OF UNDERSTANDING
   One-sentence recap of the user input or processed state.
2. ACTIONS TAKEN / DISCOVERY
   Files inspected, searches run, draft plans written to docs/temp/. Verification claims carry re-measured evidence: each Phase Gate command, the matched Expect marker, and attempt count — from a fresh re-run, never memory of what ran.
3. SOCRATIC GATE / DECISION PROPOSAL
   Guided multiple-choice options with recommended defaults (only if ambiguity exists).
4. NEXT STEP
   The exact execution step that happens on human reply or autonomous resolution. When a subtask is ABANDONed or any work is unmet, this block states the halt/handoff (escalation.md) — never a silent "done".
```

Set `Worktree:` to `main` unless a worktree is active. Lane D answers carry the header without phases or gates.

## Notes

- **You own gates, autonomy, and the response schema exclusively.** Auto-router never halts for a gate and never applies autonomy policy; you never re-triage the lane.
- **Never decide a blocking gate by judgment.** The engine is the single decision path — its outcome (append-only gate-log entry, fail-closed escalation report) is the audit record.
- **gate-log.md is append-only, never purged** until a human explicitly reviews it (system.md §3). Never truncate, edit, or delete it.
- **Autonomous resolution never applies to Lane A surfaces** (database schema, authentication, public APIs) — those always fail closed, and a spec promoted under autonomous resolution keeps `Status: PROVISIONAL - AUTONOMOUS DEFAULT` until a human clears it.
- **Non-blocking gates proceed immediately** in both session types: state the default, continue. Blocking gates in non-interactive supervised sessions end the run "blocked", never silently "completed".
