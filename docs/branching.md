---
tags: [branching, branch-per-spec, worktree, commit-terminal, never-merge, main, parallel]
---

# Branching, Parallel Work & Worktrees

The isolation model: how planning, coding, and committing are separated, how parallel specs and parallel coders are kept from colliding, and the (not yet implemented) physical-worktree tier.

## Current State

**Picture:** [flow.md](flow.md) — diagram 4, *Multi-spec + escalation*.

The branching model separates **planning** (on the default branch — `main` or `master`) from **code** (on a per-spec branch), and makes the commit **terminal**.

### Specs live on the default branch; a run creates one branch per spec

Planning artifacts — the spec, its task files, the report — are authored on the default branch (`main`/`master`). When a run starts, the orchestrator creates **one branch per spec off it (+ worktree)** and does all coding there. It **never edits the default branch**: code changes live only on the spec's branch. Because each spec runs on its own branch, nothing crosses between specs: spec N runs through review on its branch, and only once its final verification is green does it commit **on that branch** before spec N+1 starts (BRANCH-D01).

### Commit is terminal

At spec end the run **commits on its branch and stamps `Status: COMPLETED` immediately; there are no post-commit checks.** The run contract's **stop point** chooses the behavior: `commit` (default; commit + complete) or `pre-commit` (run to `REVIEWED`, stop before commit so the human inspects/commits). On a commit failure (e.g. a pre-commit hook) the spec is left `REVIEWED` and the run report records it (BRANCH-D02).

### Hard guardrail: never merge or push to the default/release branch

**Merging is human-only, even for headless runs.** A run commits on its own spec branch and stops; a human performs the merge. The run never merges or pushes to `main` or a release branch, in any mode (BRANCH-D03).

### Failure parks `ESCALATED`; the batch continues

On a failure (a task exhausts its 3 attempts and no unblocked task remains) the spec is marked **`ESCALATED`** (not `ABORTED`): the run writes `NNN-ESCALATION-<slug>.md` (every `FAILED` task with its attempts + last output, every `BLOCKED` task, the dirty edits left in the tree) and stops that spec's branch. The batch **continues** to the next spec — a bad spec cannot cascade. The run never reverts: a mid-build failure leaves the tree dirty for a human to inspect; a completed-but-wrong task is re-dispatched to its coder. Once a spec's commit lands on its branch, any task reverts as one `git revert`; because each spec has its own branch + commit, reverting one spec never touches another (BRANCH-D04).

### The problem

Concurrent AI agent sessions on one repository share one working tree and one `specs/temp/` scratchpad. Two agents working different tasks in the same clone collide on: uncommitted edits, the scratchpad, and the generated `MAP.md`.

### Current tier: branch-per-spec + the sole-writer lease

The framework already isolates **specs** from each other and **coders** within a spec:

- **Branch-per-spec.** Planning happens on `main`; a run creates **one branch per spec off `main` (+ worktree)** and does all coding there. It never edits `main`. Each spec runs through review on its branch and commits on that branch before the next spec starts, so nothing crosses between specs (BRANCH-D01).
- **Sole-writer ownership lease.** Within a spec, each task file is owned by exactly one coder, and the orchestrator dispatches two tasks concurrently **only** when their `Owns` sets are disjoint (a mechanical set-intersection check); overlapping tasks are serialized by a `Depends On` edge. This is the 1:1 file-ownership lease that keeps parallel coders from touching a shared file (see `task-files.md`).
- **Never merge/push to the default branch.** Merging is human-only in every mode; a run commits on its own branch and stops (BRANCH-D03).

### Intent tier: physical worktrees (NOT implemented)

> This section is **intent**, not implemented contract. Do not cite it as current behavior.

The future tier adds **Git Worktree Isolation** — one physical directory per spec branch. Worktrees are **not** stored inside the repository's working tree: the main worktree is the original clone, and each linked worktree is a sibling directory named `<repo>-<worktree>`, checked out on that spec's branch:

```text
/home/user/workspace/
├── project/                        # main worktree (main branch) — the original clone
├── project-spec-00x/               # linked worktree (spec 00X branch)
└── project-hotfix-billing/         # linked worktree (spec 00Y branch)
```

Git keeps the linkage in the **main** repo's `.git/worktrees/<id>/`; a linked worktree contains a `.git` *file* that points back to the main repo, not a nested `.git` directory. `git worktree list` shows every checkout, `git worktree add ../project-spec-00x spec-00x` creates one, and `git worktree remove` tears it down. A dedicated `worktrees/` or `.worktrees/` container is also common, but if it lives inside the repo it must be gitignored. Nesting a worktree inside another worktree's tracked tree is discouraged: recursive globs, file watchers, and IDE indexing treat the linked checkout as duplicate source, and the sibling layout keeps `specs/temp/` isolation unambiguous.

Operating rules:

1. **Placement: siblings, not inside the repo.** The main worktree is the original clone (`project/`); each linked worktree is a sibling named `<repo>-<worktree>` (e.g. `project-spec-00x/`) under the same parent. If you prefer a `worktrees/` container, keep it outside the tracked tree or gitignore it. Never nest a worktree inside another worktree's tracked directories.
2. **One worktree = one spec branch.** Each parallel run runs in a distinct physical git worktree directory on disk (one branch each).
3. **File-system isolation.** Because `specs/temp/` lives inside the physical path of a specific worktree, working memory is physically isolated — no shared scratchpad, no cross-task state pollution.
4. **Clean teardowns.** `git worktree remove` purges that session's ephemeral scratchpad without affecting the main repository state.
5. **`MAP.md` per worktree.** Each worktree regenerates its own index at session start (see `skill-discovery.md`); the snapshot-hash freshness check is mtime-independent, so a worktree checkout with old timestamps still reconciles correctly.

#### Integration points (where this would plug in)

- **Status header.** The `Worktree:` tag in the 5-tag header (see `lifecycle.md`) is already reserved for this: `main` unless a worktree is active.
- **ID conventions.** Spec sub-IDs share the parent `NNN` prefix (see `decision-records.md`) precisely so a branch can claim the spec group's subtree — a parallel branch works spec `00X` while main works spec `00Y`.
- **Hand-back payload.** The spec group itself (spec + task files + report + escalation) is the durable, inter-session transfer document: a fresh session resumes from `Status: COMPILED` (or `ESCALATED`) with the task files on disk, instead of re-planning.
- **Escalation & cleanup.** `NNN-ESCALATION-<slug>.md` is per-spec by construction; `task-cleaner`'s refusal to touch targets at or above the repo root keeps a cleanup scoped to its own worktree's scratchpad.

#### What a future skill would own

If this aspect is implemented, the expected shape (mirroring the engine-driven pattern of the core skills):

- A `git-worktree` skill with a stdlib-only engine handling: create (`git worktree add` with branch + scratchpad bootstrap), list/inspect, teardown (remove + scratchpad purge verification), and the branch naming convention.
- `dev-agent-framework.md` boot-chain step for worktree detection (is this session inside a non-main worktree? set the `Worktree:` tag).
- A topic decision recording the adoption, per the normal spec-first lifecycle — this section is the planning input, not the approval.

Until the worktree tier is built: parallel specs run **one at a time, each on its own branch** (branch-per-spec, the current tier), or on independent clones; the `Worktree:` header tag reflects the active branch.

## Decision Log

### BRANCH-D01 - One branch per spec, off main, + worktree
- **Date:** 2026-09-27
- **Why:** Planning stays on `main` while code changes are isolated per spec; an escalation stops only that spec's branch so a bad spec cannot cascade into the batch.

### BRANCH-D02 - Commit is terminal; the stop point decides
- **Date:** 2026-09-27
- **Why:** Stamping `COMPLETED` at commit with no post-commit checks makes the terminal state unambiguous; `pre-commit` is the opt-out for a human to inspect/commit themselves.

### BRANCH-D03 - Never merge or push to the default/release branch
- **Date:** 2026-09-27
- **Why:** Merging is a human-only decision even in headless runs; the run commits on its own branch and stops, so no automated path can land work on `main` unreviewed.

### BRANCH-D04 - Failure parks `ESCALATED`, no revert, batch continues
- **Date:** 2026-09-27
- **Why:** A failure is a visible, resumable halt (consolidated escalation + dirty tree for a human to inspect), not a silent abort; per-spec branch + commit keeps a failure from cascading.
