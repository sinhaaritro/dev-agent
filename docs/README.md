---
tags: [docs, guide, onboarding, index]
---

# Dev Agent Docs — Start Here

This folder is the committed, human + AI shared knowledge of the Dev Agent framework. If you are new to this repository, **read this page top to bottom**; it tells you what the project is, the order to read the deeper docs in, and the vocabulary you need for the rest.

> Every doc here except this landing page and the generated `_topics.md` is a **topic doc** — one per subsystem, each with a `## Current State` you can read alone and a `## Decision Log` recording why it is the way it is. `_topics.md` is generated; don't edit it by hand.

## What this repository is

Dev Agent is a drop-in configuration framework for AI coding assistants. It turns a repository into a structured workspace where humans and AI agents work the same codebase as equals: a request is triaged into a **lane**, planned behind **gates**, built from a **compiled spec**, verified with **content-hash evidence**, and handed back so anyone can resume mid-flight.

This repository **is the framework's source**, not a project that uses it:

- **`skills/` is the product.** Each folder is an installable skill; `dev-agent` bundles the shared runtime and installer, while the other six are thin wrappers (`SKILL.md` + `references/`) that call the runtime by subcommand. Users install them with `npx skills add`. Only `skills/` ships.
- **`.agents/` is this repo's own workspace.** It holds only repo-only tooling skills (`author-skill`, the vendored `skill-creator`). It never ships, and the repo does **not** run the framework on itself.
- **`specs/` is what to build.** Each spec group is a plan with a single `Status:` lifecycle, its task files, approvals, report, and escalation.
- **`docs/` is what is + why we chose.** One topic doc per subsystem (this folder).

## Read in this order

The order is deliberate: each doc only assumes the ones before it.

| # | Doc | What you get |
| :-- | :--- | :--- |
| 1 | [`overview.md`](overview.md) | The mental model: what Dev Agent guarantees, the directory map, memory tiers, the seven core skills, and the boot chain. **Start here.** |
| 2 | [`skill-discovery.md`](skill-discovery.md) | How the agent finds skills: the generated `MAP.md`, snapshot-hash freshness, and two-stage recall. |
| 3 | [`routing.md`](routing.md) | How a request is classified: the four lanes (D/C/B/A), session detection, escalation, and the routing verdict. |
| 4 | [`lifecycle.md`](lifecycle.md) | How work is governed: the `Status:` lifecycle, Socratic gates, the autonomy policy, and the 4-block response schema. |
| 5 | [`decision-records.md`](decision-records.md) | How knowledge is stored: topic docs, IDs and tags, the spec-first lifecycle, templates, TOC, and the scratchpad. |
| 6 | [`task-files.md`](task-files.md) | The coder's unit of work: the task file, 1:1 file ownership, and subtasks vs the verify gate. |
| 7 | [`verification.md`](verification.md) | How "done" is proven: command resolution, approval fingerprints, content-hash evidence, the 3-attempt budget, the doctor, and escalation. |
| 8 | [`branching.md`](branching.md) | Isolation: branch-per-spec, commit-terminal, the never-merge rule, the sole-writer lease, and the (not yet built) worktree tier. |
| 9 | [`run-contract.md`](run-contract.md) | How a run starts and stops: targets, `supervised`/`unattended`, the `commit`/`pre-commit` stop point, and opt-in triggers. |
| 10 | [`flow.md`](flow.md) | The picture book: Mermaid diagrams of the state machine, build run, review, multi-spec batch, and build loop. |

Read 1–4 to understand *how the agent thinks*. Read 5–8 to understand *how work is built and proved*. Read 9–10 when you need the end-to-end picture.

## The 60-second mental model

On **every request**, in order (full detail in `overview.md`):

1. **Refresh the skill index** (`MAP.md`) if it is stale.
2. **Route** the prompt into a lane (D/C/B/A), detect the session type, and recall candidate skills.
3. **Govern** the work with the `Status:` lifecycle. Ambiguity is resolved with a blocking/non-blocking gate, never by silent judgment. Approving a draft **compiles** it into a spec + task files and **ends the session**.
4. **Build** in a *new* session/run from the `COMPILED` spec, dispatching tasks to coders, each proving itself through the runtime's `verify` command.
5. **Hand back**: review, sign off, commit on the spec's branch. A failure parks the spec `ESCALATED` for a human — never a silent pass.

The one rule that makes the whole thing work: **mechanics live in engines, not judgment.** The agent decides *what* to run; the shared stdlib Python runtime at `.agents/scripts/devagent/` does the counting, hashing, gating, and auditing.

## The vocabulary

| Term | Meaning |
| :--- | :--- |
| **Lane** | The scope class of a request: **D** read-only, **C** single-file micro-edit, **B** 2–5 files, **A** full SDLC (schema/API/auth/new dependency). Higher lanes get more gates. |
| **Gate** | A decision point. **Blocking** gates halt (or fail closed); **non-blocking** gates state a default and continue. Resolved through the runtime's `gate` command. |
| **Spec** | A committed plan (`specs/NNN-SPEC-*.md`) with a single `Status:` lifecycle. |
| **Task file** | A self-contained briefing for one coder (`specs/NNN-TASK-NN-*.md`), owning a disjoint `Owns` set of files. |
| **COMPILED** | The only state a run may start from. Reached by approving a draft; unreachable without the gate. |
| **Evidence block** | The record the runtime's `verify` command writes into a task file on a green verify: command, exit, `Expect` match, and the `sha256` of every owned file. |
| **Derived status** | Task completion read from evidence: `MET` / `NOT MET` / `STALE` / `NO-EVIDENCE` — never asserted. |
| **ESCALATED** | A visible, resumable halt after a task exhausts its 3 attempts. The batch continues; `ABORTED` is only a human stop. |
| **Topic doc** | One doc per subsystem (`docs/<name>.md`) holding Current State + Decision Log. |
| **SCRATCHPAD** | `specs/temp/` — gitignored working memory, purged by `task-cleaner` on acceptance. |

## Where things live

| Path | What it is | Ships? |
| :--- | :--- | :--- |
| `skills/` | The product: composable skills users install | **Yes** |
| `.agents/skills/` | Repo-only tooling skills (`author-skill`, vendored `skill-creator`) | No |
| `specs/` | What to build: approved specs + task files + reports | No |
| `docs/` | What is + why we chose (this folder) | No |
| `tools/` | Maintainer engines (`behavior_eval.py`, `skill_eval.py`, `suite_report.py`) | No |

## How to make a change in this repo

Because this repo *is* the framework, the normal rules are inverted: you are a **maintainer**, not a consumer.

1. **Changing a skill?** Edit it only under `skills/<name>/` (there is no derived copy). Use the `author-skill` skill, then verify with the repo's own commands (`compileall`, `unittest`, `ruff check`, `suite_report`).
2. **Changing a contract?** Update the rulebook and the skill that owns the behavior **together**, then run the canonical commands from `AGENTS.md` (`compileall`, `unittest`, `ruff check`, `suite_report`).
3. **Changing knowledge?** Edit the topic doc's `## Current State`; if you are reversing a decision, append a new `<TOPIC>-D<nn>` entry with `Supersedes:` through `python .agents/scripts/devagent/main.py spec topic` (never delete history).
4. **Adding a doc?** Add a flat `docs/<name>.md` topic doc (no numeric prefix), then run `python .agents/scripts/devagent/main.py map sync-docs`.

## Conventions for these docs

- **Filename is the identity** — no `name:` field. Topic docs are lowercase kebab (`data-storage.md`) and never carry a numeric prefix.
- **Frontmatter carries `tags:`** — a 2–7 word lowercase-kebab list (max 7). It is the source of the `covers:` line in the generated `_topics.md`.
- **Every topic doc has `## Current State` then `## Decision Log`.** Keep the log entries equal-weight and linkable (`### <TOPIC>-D<nn> - <title>`).
- **A reversal is a revision**, not an edit: next ID + `Supersedes:`, current state rewritten in place.
- **Never hand-edit `_topics.md`** — run `sync-docs` after changing a topic doc.
- **`docs/` never depends on `specs/`** — the rule is one-way (a durable file must not link into the disposable `specs/`), enforced by `python .agents/scripts/devagent/main.py spec specs-lint`. This framework repo is itself exempt: its product *documents* the system, so the `specs/…` names above are descriptive, not dependencies.
