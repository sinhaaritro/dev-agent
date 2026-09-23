---
tags: [worktree, parallel, isolation, intent]
---

# 007 - Parallel Execution & Git Worktrees (INTENT)

> **Status: INTENT — not implemented.** No skill in this repo manages git
> worktrees. This doc records the architectural direction the framework is
> designed around, so a future `git-worktree` skill (or equivalent) has a
> spec to build against. Every statement here is a design goal, not current
> behavior — do not cite it as implemented contract.

**Skills covered:** none yet (the intended future skill would sit alongside
the seven core skills).

## 1. The problem

Concurrent AI agent sessions on one repository share one working tree and one
`specs/temp/` scratchpad. Two agents working different tasks in the same
clone collide on: uncommitted edits, the scratchpad (draft plans,
verify-state, gate-log entries), and the generated `MAP.md`.

## 2. The isolation model

The design relies on **Git Worktree Isolation**:

```text
/home/user/workspace/project-main/            # Worktree 1 (main branch)
    └── specs/temp/                            # Isolated main task state

/home/user/workspace/project-feature-auth/    # Worktree 2 (feature/auth branch)
    └── specs/temp/                            # Isolated auth task state

/home/user/workspace/project-hotfix-billing/  # Worktree 3 (hotfix/billing branch)
    └── specs/temp/                            # Isolated billing task state
```

Operating rules:

1. **One worktree = one task.** Each parallel agent runs in a distinct
   physical git worktree directory on disk (one branch each).
2. **File-system isolation.** Because `specs/temp/` lives inside the physical
   path of a specific worktree, working memory is physically isolated — no
   shared scratchpad, no shared `verify-state.json`, no cross-task
   `gate-log.md` pollution.
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
  section 2) precisely so "a worktree can claim the subtree" — a parallel
  branch works `001-A01` while main works `001-A02`.
- **Handoff payload.** `specs/temp/handoff-payload.md` (inter-agent session
  context: origin worktree, origin branch, completed state, pending blocks,
  artifact pointers) is the transfer document between worktrees/sessions; the
  per-session `handoff.md` (005, section 4) remains the approval-phase
  record.
- **Escalation & cleanup.** `escalation.md` and `verify-state.json` are
  per-worktree by construction; `task-cleaner`'s refusal to touch targets at
  or above the repo root keeps a cleanup scoped to its own worktree's
  scratchpad.

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

Until then: parallel sessions should run **sequentially on one worktree**,
or on independent clones, and the `Worktree:` header tag should stay `main`.
