---
name: promote
description: Maintainer sync - reconciles the dogfood workspace (.agents/skills/) from the shipped product (skills/) via tools/promote.py, stamping derived copies with metadata.internal so only skills/ ships. Use when a skill in skills/ is added, edited, or removed, before committing skill changes, when the skill index looks stale, or when the workspace copy may have drifted from the product.
tags:
  - promote
  - sync
  - mirror
  - internal
  - drift
  - skills
metadata:
  version: 1.0.0
  author: AI Agent
  internal: true
---

# Promote

## Overview

You keep the repo's dogfood workspace (`.agents/skills/`) in step with the
shipped product (`skills/`). `skills/` is canonical; `.agents/skills/` is
derived. The skills CLI discovers BOTH folders, so every skill under
`.agents/skills/` must carry `metadata.internal: true` or it leaks to users.
`tools/promote.py` mirrors the product and injects that flag; you decide WHEN to
run it and report WHAT changed.

This skill is repo-only (its own frontmatter carries `metadata.internal: true`)
and never ships to users.

## When to Use

- A skill in `skills/` was created, edited, renamed, or deleted.
- Before committing any change under `skills/`.
- The generated index (`.agents/MAP.md`) looks stale.
- You suspect `.agents/skills/` has drifted from `skills/`.

## Instructions

1. **Check for drift.** Run:
   `python tools/promote.py --check`
   Exit 0 = clean (nothing to do). Exit 1 = drift; the report names each skill as
   `new:` / `overwrite:` / `remove:`.
2. **Preview if useful.** `python tools/promote.py --dry-run` prints the same
   report without writing anything.
3. **Apply.** On drift, run:
   `python tools/promote.py apply`
   The engine mirrors each owned skill, deletes stale files, and stamps the
   derived `SKILL.md` with `metadata.internal: true`. Unmanaged folders
   (`promote`, `author-skill`, `skill-creator`) are never touched.
4. **Confirm.** Re-run `python tools/promote.py --check`; it must print
   `promote: clean`.
5. **Rebuild the index.** Run
   `python .agents/scripts/devagent/main.py map --force`
   so `MAP.md` reflects the mirror.
6. **Verify the shipping set.** The default `npx skills add . --list` must show
   exactly the top-level folders in `skills/`; repo-only skills stay hidden.
7. **Hand back.** Tell the human to start a new session so the reloaded skills
   and index are picked up.

## Boundaries

- **Canonical is `skills/`.** Never edit a mirrored copy under `.agents/skills/`
  - the next `apply` overwrites it. Edit `skills/<name>/`, then promote.
- **Never add `metadata.internal` to a `skills/` SKILL.md** - that would hide a
  shipped skill from users. Only the derived copy carries it.
- **Never hand-edit an unmanaged folder** (`skill-creator`). promote does not own
  it and will not overwrite or delete it.

## Output Contract

- Check: the per-skill report, then `promote: clean` or
  `promote: <N> change(s) needed`.
- Apply: the per-skill lines plus `promote complete: ...`; state which skills
  were reconciled and that a new session is the next step.
- Errors (no `skills/` folder, name collision with an unmanaged skill, missing
  frontmatter): the engine's message verbatim; no partial state is reported as
  success.
