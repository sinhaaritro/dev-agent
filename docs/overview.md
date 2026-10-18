---
tags: [framework, overview, architecture, orchestration]
---

# Framework Overview

Dev Agent is a drop-in configuration framework for AI coding assistants. It turns a repository into a structured workspace where humans and AI agents work the same codebase as equals: every task is triaged into a scope lane, planned behind Socratic gates, built against a compiled spec, verified with content-hash evidence, and handed back with a compiled spec so any human or agent can resume mid-flight.

## Current State

### What it is

- **Harness-agnostic.** No harness-specific skill mechanism. The agent reads files off disk (`AGENTS.md`, `.agents/rules/dev-agent-framework.md`, each `.agents/skills/<name>/SKILL.md`) guided by explicit paths — the same files work in Cursor, Windsurf, Claude Code, OpenCode, Aider, Gemini CLI, Roo Code, Antigravity, and others.
- **Model-agnostic.** Per-status model tiering (SOTA for planning/review, local or SOTA for building) is an optimization only; it never changes the contract.
- **Spec-driven.** Code is built from a `COMPILED`, committed spec — never from an ephemeral draft, and never in the same session that produced the spec.
- **Engine-driven.** Every mechanical contract (index freshness, skill recall, gate resolution, spec compile, verification counting, scratchpad purging) runs through a stdlib-only Python engine under `.agents/skills/<name>/scripts/`. The agent supplies judgment (what to run, what the ambiguity is); the engine supplies the mechanics and the audit record.

### Directory map

```text
<repository-root>/
├── AGENTS.md                    # Project contract + entry point (agent reads first)
├── .cursorrules                 # IDE pointer -> .agents/rules/dev-agent-framework.md
├── .windsurfrules               # IDE pointer -> .agents/rules/dev-agent-framework.md
├── skills.sh.json               # skills.sh catalog groupings (install via npx skills)
│
├── specs/                       # What to build — spec groups: NNN-SPEC + NNN-TASK + approvals + report
│   └── temp/                    # EPHEMERAL SCRATCHPAD (gitignored: * except .gitignore)
│
├── docs/                        # HUMAN + AI SHARED SPACE (committed)
│   ├── README.md                # Start here — the guided reading path
│   ├── <name>.md or <name>/     # Topic docs: one per subsystem, each
│   │                            #   ## Current State + ## Decision Log
│   └── _topics.md               # Generated AI routing index (sync-docs)
│
└── .agents/                     # MACHINE SPACE (AI internals)
    ├── rules/
    │   └── dev-agent-framework.md            # Gateway rulebook — loaded every session, wins conflicts
    ├── MAP.md                   # Generated skill index (on-disk at session start, never committed)
    └── skills/                  # Seven core skills (below)
```

Note: `.agents/MAP.md` is generated on demand by `map-generator` at session start and is not part of the committed tree; it is listed here because every other doc references it.

### Memory architecture

Memory is strictly split:

| Tier | Location | Lifecycle | Examples |
| :--- | :--- | :--- | :--- |
| Ephemeral working memory | `specs/temp/` (gitignored) | Purged by `task-cleaner` (default preserves `.gitignore` only) | `draft-plan.md`, `active-task.md`, draft-stage notes |
| Persistent memory | topic docs under `docs/`, specs under `specs/` (committed) | Never purged; specs have a `Status:` lifecycle; topic docs are living (decisions revised in place, never deleted) | topic docs, `NNN-SPEC`/`NNN-TASK` files |

There is no preserved append-only gate log in the scratchpad: gate decisions are recorded in the spec's own `Gates:` section, and the per-spec `NNN-ESCALATION-<slug>.md` is the durable failure audit record.

### The seven core skills

| Skill | Role | Engine |
| :--- | :--- | :--- |
| `auto-router` | Triage: lane assignment (D/C/B/A), session detection, skill recall, escalation monitoring | `match_skills.py` |
| `map-generator` | Keeps `.agents/MAP.md` fresh (snapshot-hash freshness check) | `generate_map.py` |
| `phase-protocol` | Meta-skill: the Status lifecycle (`DRAFTED`…`COMPLETED`), Socratic gates, autonomy policy, 4-block response schema | `resolve_gate.py` |
| `spec-builder` | Plan drafting, spec compile + promotion, task-file generation, topic decision recording, tag governance, TOC rollup | `promote_spec.py` |
| `verification-runner` | Verification command execution, content-hash evidence, `doctor`/`status`/`report`, consolidated escalation | `verify.py` |
| `task-cleaner` | Scratchpad garbage collection on acceptance (preserves `.gitignore` only) | `clean.py` |
| `bootstrap` | Installs the framework (AGENTS.md + dev-agent-framework.md + IDE pointers) into a target repo | `bootstrap.py` |

Each skill is self-contained: a `SKILL.md` (what/when/instructions), a `scripts/` engine (stdlib-only Python), and optional `references/` checklists. Skills with `scope: always` in frontmatter (auto-router, phase-protocol) load at session start; all others load on demand when their tags or context match. See `skill-discovery.md`.

### Boot chain (what happens on every request)

Defined in `.agents/rules/dev-agent-framework.md`, in order:

1. **MAP freshness.** Run `generate_map.py`; if it prints `regenerated`, re-read `.agents/MAP.md`. Never match against a stale index.
2. **Route (auto-router).** Classify the lane (D/C/B/A), detect session type (Interactive / Non-Interactive), run `match_skills.py "<prompt>"` for candidate skills (candidates only, never a filter). See `routing.md`.
3. **Gover (phase-protocol).** Drive the Status lifecycle `DRAFTED → COMPILED → BUILDING → BUILT → REVIEWED → COMPLETED` (Vetting and Sign-off gates); emit the 5-tag status header and 4-block schema; resolve every gate through `resolve_gate.py`; at "approve draft" the spec is compiled into task files and stamped `COMPILED`, at compile the session stops — build never follows in the same session. See `lifecycle.md`.
4. **Load matching on-demand skills** and obey their engines (spec-builder for plans, verification-runner for verification, task-cleaner for cleanup).
5. **No matching skill** → baseline: plan in `specs/temp/draft-plan.md`, build, verify, promote only on human acceptance.

### Guardrails (non-negotiable, regardless of loaded skills)

- Never modify or delete `.env*` files, credentials/keys/certificates, or lockfiles (unless executing approved dependency commands).
- Never modify `specs/*` without explicit human confirmation.
- Topic guardrail: no silent / unrequested topic-doc edits in any lane; Lanes A/B consult topic docs and emit the Conflict Surface on a reversal; Lanes C/D skip docs and escalate on a pattern-break; a reversal is a revision (next ID, `--supersedes`), never "delete + recreate".
- Never commit `specs/temp/` contents.
- Gate decisions are recorded in the spec's `Gates:` section; a failure's audit trail is the spec's `NNN-ESCALATION-<slug>.md` — never hand-written.
- Blocking gates are never resolved by judgment alone — the gate engine is the single decision path.

### Where to go next

`README.md` lays out a guided reading path. In short: this doc for the mental model, then `routing.md` → `lifecycle.md` → `decision-records.md` → `task-files.md` → `verification.md` → `branching.md` → `run-contract.md`, with `flow.md` as the picture book and `skill-discovery.md` as the skill-loading backdrop.

## Decision Log

No subsystem-specific decisions are recorded in this doc; the design decisions live in the topic doc they belong to. See `decision-records.md` for the docs-system history, including the consolidation that produced this single-layer docs set.
