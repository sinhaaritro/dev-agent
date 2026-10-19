---
name: phase-protocol
description: Process governance meta-skill - drives the single Status lifecycle DRAFTED -> COMPILED -> BUILDING -> BUILT -> REVIEWED -> COMPLETED through the Vetting and Sign-off gates, resolves Socratic gates via the autonomy policy, and emits the 5-tag header with the 4-Block response schema. Use on every session and every prompt, at every status transition, and whenever a decision must be gated (blocking or non-blocking).
tags:
  - status
  - lifecycle
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

# Status Protocol

## Overview

The process-governance meta-skill, run after auto-router's verdict. You drive every task through the single `Status:` lifecycle (`DRAFTED → COMPILED → BUILDING → BUILT → REVIEWED → COMPLETED`, with the Vetting and Sign-off gates), enforce tool posture per status, resolve Socratic gates through the autonomy policy, and emit the 5-tag header with the 4-Block schema in every response. You consume auto-router's verdict — you own gates, never lane triage.

## When to Use

- Every session and every incoming prompt (mandatory third step of the boot chain).
- Every status transition — load ONLY that status's reference checklist (never all references) and complete it before moving on.
- Every gate (blocking or non-blocking, any session type) — resolve through the engine, never by judgment alone.

## Instructions

1. **Route the status from the verdict.** Lanes B and A start `DRAFTED` and MUST end it at `COMPILED` (references/compiled.md) — the optional Vetting gate runs on the draft first (when `vetting: on`), then the "approve draft" step promotes the spec, compiles the task files, and the session stops there; **build never follows approval in the same session**. Lane C is a single pass; Lane D is informational (header only, no lifecycle). C/D have no approval step, so no compile. At each status start, load ONLY `references/<name>.md` — never preload all references — and follow its checklist exactly; a status completes only when its checklist is green. On an escalation flag, continue under the announced lane: re-plan under the new lane's artifact requirements, never ask permission, never silently de-escalate.
2. **Enforce tool posture.** Planning, Compile, and Review are read-only — no file edits. Build allows edits within lane scope only (per auto-router's `references/lane-matrix.md`). Scope creep toward a higher lane stops the build: the router re-classifies and announces the escalation before you continue.
3. **Resolve every gate through the engine.** Classify first: **blocking** (security, database schemas, public APIs, Lane A criteria) vs **non-blocking** (minor internal scope). Then run:
   `python .agents/scripts/devagent/main.py gate --gate <blocking|non-blocking> --session <Interactive|Non-Interactive> --lane <A|B|C|D> [--lane-a-surface] --question "<text>" --options "<A (Recommended): ...; B: ...>"`
   Autonomy is read from `AGENTS.md` (`autonomy_level`, supervised by default). Exit code is the contract: **0** proceed/resolved (non-blocking: state the default and proceed; autonomous: apply the Recommended Option and append an audit entry under the plan/spec `## 6. Gates` heading); **1** halt (interactive blocking: await the human's answer); **2** fail-closed (supervised non-interactive blocking, or any Lane-A surface gate — escalation.md written, no changes made). The Lane-A exception is encoded in the engine, never advisory: schema/auth/public-API gates always fail closed even under autonomous.
4. **Emit the response schema in every response** — every reply carries the 5-tag header and the 4 blocks below, including Lane D answers and Lane C micro-edits.

## Output Contract

Every response uses exactly this schema, inherited by every other skill:

```text
[STATUS: <Status> | Task: <ID> | Lane: <A|B|C|D> | Worktree: <name> | Session: <Interactive|Non-Interactive>]

1. SUMMARY OF UNDERSTANDING
   One-sentence recap of the user input or processed state.
2. ACTIONS TAKEN / DISCOVERY
    Files inspected, searches run, draft plans written to specs/temp/ — cited by path, never pasted. Verification claims carry re-measured evidence: each task's Verify command, the matched Expect marker, and attempt count — from a fresh re-run, never memory of what ran.
3. SOCRATIC GATE / DECISION PROPOSAL
   Guided multiple-choice options with recommended defaults (only if ambiguity exists).
4. NEXT STEP
   The exact execution step that happens on human reply or autonomous resolution. When a subtask is ABANDONed or any work is unmet, this block states the halt/hand-back (escalation.md) — never a silent "done".
```

Set `Worktree:` to the default branch (`main` or `master`) unless a worktree is active. The `Status:` tag is always a canonical `Status:` value (`DRAFTED` … `ABORTED`) — never a step label such as `plan` or `review`: lanes A/B carry the active spec's receipt; Lane C uses `DRAFTED` → `BUILDING` → `BUILT` → `COMPLETED`; Lane D uses `COMPLETED`. Lane D answers carry the header without steps or gates.

## Notes

- **You own gates, autonomy, and the response schema exclusively.** Auto-router never halts for a gate and never applies autonomy policy; you never re-triage the lane.
- **Never echo file bodies in chat.** Report every artifact by path plus a one-line summary; a plan/spec's section 5 Tasks & Outcomes table and its `### Task N:` list stay in the file and are never reproduced in the response.
- **Never decide a blocking gate by judgment.** The engine is the single decision path — its outcome (an append-only `## 6. Gates` entry, or a fail-closed escalation report) is the audit record.
- **The gate log is append-only inside the plan/spec `## 6. Gates` section** (dev-agent-framework.md section 3). Never truncate, edit, or delete an entry; the plan carries its entries into the promoted spec, so purging the scratchpad is safe. Never create or maintain a separate `specs/temp/gate-log.md` — section 6 is the only gate log.
- **Autonomous resolution never applies to Lane A surfaces** (database schema, authentication, public APIs) — those always fail closed, and a spec promoted under autonomous resolution compiles to `COMPILED` like any other, with its `## 6. Gates` entry marked autonomous and its topic decisions deferred until a human clears that mark.
- **Non-blocking gates proceed immediately** in both session types: state the default, continue. Blocking gates in non-interactive supervised sessions end the run "blocked", never silently "completed".
