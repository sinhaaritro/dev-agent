---
tags: [branching, branch-per-spec, worktree, commit-terminal, never-merge, main]
---

# Branching & Commit

## Current State

The branching model separates **planning** (on `main`) from **code** (on a per-spec branch), and
makes the commit **terminal**.

### Specs live on `main`; a run creates one branch per spec

Planning artifacts — the spec, its task files, the report — are authored on `main`. When a run
starts, the orchestrator creates **one branch per spec off `main` (+ worktree)** and does all
coding there. It **never edits `main`**: code changes live only on the spec's branch. Because each
spec runs on its own branch, nothing crosses between specs: spec N runs through review on its
branch, and only once its final verification is green does it commit **on that branch** before spec
N+1 starts (BRANCH-D01).

### Commit is terminal

At spec end the run **commits on its branch and stamps `Status: COMPLETED` immediately; there are
no post-commit checks.** The run contract's **stop point** chooses the behavior: `commit` (default;
commit + complete) or `pre-commit` (run to `REVIEWED`, stop before commit so the human
inspects/commits). On a commit failure (e.g. a pre-commit hook) the spec is left `REVIEWED` and the
run report records it (BRANCH-D02).

### Hard guardrail: never merge or push to the default/release branch

**Merging is human-only, even for headless runs.** A run commits on its own spec branch and stops;
a human performs the merge. The run never merges or pushes to `main` or a release branch, in any
mode (BRANCH-D03).

### Failure parks `ESCALATED`; the batch continues

On a failure (a task exhausts its 3 attempts and no unblocked task remains) the spec is marked
**`ESCALATED`** (not `ABORTED`): the run writes `NNN-ESCALATION-<slug>.md` (every `FAILED` task with
its attempts + last output, every `BLOCKED` task, the dirty edits left in the tree) and stops that
spec's branch. The batch **continues** to the next spec — a bad spec cannot cascade. The run never
reverts: a mid-build failure leaves the tree dirty for a human to inspect; a completed-but-wrong
task is re-dispatched to its coder. Once a spec's commit lands on its branch, any task reverts as
one `git revert`; because each spec has its own branch + commit, reverting one spec never touches
another (BRANCH-D04).

## Decision Log

### BRANCH-D01 - One branch per spec, off main, + worktree
- **Date:** 2026-09-27
- **Why:** Planning stays on `main` while code changes are isolated per spec; an escalation stops
  only that spec's branch so a bad spec cannot cascade into the batch.

### BRANCH-D02 - Commit is terminal; the stop point decides
- **Date:** 2026-09-27
- **Why:** Stamping `COMPLETED` at commit with no post-commit checks makes the terminal state
  unambiguous; `pre-commit` is the opt-out for a human to inspect/commit themselves.

### BRANCH-D03 - Never merge or push to the default/release branch
- **Date:** 2026-09-27
- **Why:** Merging is a human-only decision even in headless runs; the run commits on its own
  branch and stops, so no automated path can land work on `main` unreviewed.

### BRANCH-D04 - Failure parks `ESCALATED`, no revert, batch continues
- **Date:** 2026-09-27
- **Why:** A failure is a visible, resumable halt (consolidated escalation + dirty tree for a human
  to inspect), not a silent abort; per-spec branch + commit keeps a failure from cascading.
