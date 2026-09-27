---
tags: [worktree, parallel, isolation, branch-per-spec, ownership-lease]
---

# 007 - Branch-per-spec, Parallel Execution & Worktrees

The isolation model is now **two-tier**: a **current** tier (branch-per-spec +
a sole-writer ownership lease, implemented by the run model and described in
`docs/branching.md`) and a **future** tier (physical git worktrees for fully
disjoint physical trees — still INTENT). The rest of this doc (sections 2–4)
is the INTENT tier; do not cite it as implemented contract.

**Skills covered:** the run model (current); a future `git-worktree` skill
would sit alongside the core skills (intent).

## 1. The problem

Concurrent AI agent sessions on one repository share one working tree and one
`specs/temp/` scratchpad. Two agents working different tasks in the same
clone collide on: uncommitted edits, the scratchpad, and the generated
`MAP.md`.

## 1a. Current tier: branch-per-spec + the sole-writer lease

The framework already isolates **specs** from each other and **coders** within
a spec:

- **Branch-per-spec.** Planning happens on `main`; a run creates **one branch
  per spec off `main` (+ worktree)** and does all coding there. It never edits
  `main`. Each spec runs through review on its branch and commits on that
  branch before the next spec starts, so nothing crosses between specs
  (BRANCH-D01). See `docs/branching.md`.
- **Sole-writer ownership lease.** Within a spec, each task file is owned by
  exactly one coder, and the orchestrator dispatches two tasks concurrently
  **only** when their `Owns` sets are disjoint (a mechanical set-intersection
  check); overlapping tasks are serialized by a `Depends On` edge. This is the
  1:1 file-ownership lease that keeps parallel coders from touching a shared
  file (see `docs/task-files.md`).
- **Never merge/push to the default branch.** Merging is human-only in every
  mode; a run commits on its own branch and stops (BRANCH-D03).

## 2. The isolation model (INTENT: physical worktrees)

The future tier adds **Git Worktree Isolation** — one physical directory per
spec branch:

```text
/home/user/workspace/project-main/            # Worktree 1 (main branch)
    └── specs/temp/                            # Isolated main task state

/home/user/workspace/project-feature-auth/    # Worktree 2 (spec 00X branch)
    └── specs/temp/                            # Isolated spec task state

/home/user/workspace/project-hotfix-billing/  # Worktree 3 (spec 00Y branch)
    └── specs/temp/                            # Isolated spec task state
```

Operating rules:

1. **One worktree = one spec branch.** Each parallel run runs in a distinct
   physical git worktree directory on disk (one branch each).
2. **File-system isolation.** Because `specs/temp/` lives inside the physical
   path of a specific worktree, working memory is physically isolated — no
   shared scratchpad, no cross-task state pollution.
3. **Clean teardowns.** `git worktree remove` purges that session's ephemeral
   scratchpad without affecting the main repository state.
4. **`MAP.md` per worktree.** Each worktree regenerates its own index at
   session start (002); the snapshot-hash freshness check is
   mtime-independent, so a worktree checkout with old timestamps still
   reconciles correctly.

## 3. Integration points (where this would plug in)

- **Status header.** The `Worktree:` tag in the 5-tag header (004, section 4)
  is already reserved for this: `main` unless a worktree is active.
- **ID conventions.** Spec sub-IDs share the parent `NNN` prefix (005,
  section 2) precisely so a branch can claim the spec group's subtree — a
  parallel branch works spec `00X` while main works spec `00Y`.
- **Hand-back payload.** The spec group itself (spec + task files + report +
  escalation) is the durable, inter-session transfer document: a fresh session
  resumes from `Status: COMPILED` (or `ESCALATED`) with the task files on
  disk, instead of re-planning.
- **Escalation & cleanup.** `NNN-ESCALATION-<slug>.md` is per-spec by
  construction; `task-cleaner`'s refusal to touch targets at or above the repo
  root keeps a cleanup scoped to its own worktree's scratchpad.

## 4. What a future skill would own

If this aspect is implemented, the expected shape (mirroring the
engine-driven pattern of the core skills):

- A `git-worktree` skill with a stdlib-only engine handling: create
  (`git worktree add` with branch + scratchpad bootstrap), list/inspect,
  teardown (remove + scratchpad purge verification), and the branch naming
  convention.
- `system.md` boot-chain step for worktree detection (is this session inside
  a non-main worktree? set the `Worktree:` tag).
- A topic decision recording the adoption, per the normal spec-first
  lifecycle — this doc is the planning input, not the approval.

Until the worktree tier is built: parallel specs run **one at a time, each on
its own branch** (branch-per-spec, the current tier), or on independent
clones; the `Worktree:` header tag reflects the active branch.
