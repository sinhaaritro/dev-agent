---
name: author-skill
description: Author or edit a skill in THIS repo - creates, fixes, or optimizes a skill under skills/. Takes precedence over skill-creator in this repository. Use when creating a new skill, editing or optimizing an existing skill's instructions, or changing a skill's description or triggering, inside dev-agent.
tags:
  - author
  - skill
  - create
  - edit
  - optimize
metadata:
  version: 1.0.0
  author: AI Agent
  internal: true
---

# Author Skill

## Overview

You are the entry point for changing a skill in this repository. This repo is the
framework SOURCE: the product is the folders under `skills/`. A change to a skill
lands in `skills/<name>/` and is done - there is no mirror to regenerate. This
skill overrides `skill-creator` here.

Load `skill-creator` for its method (drafting, evals, iteration), then apply the
overrides below. They exist because `skill-creator` assumes a consumer layout
that does not match this repo.

## When to Use

- Creating a new skill in this repo.
- Editing or fixing an existing skill's instructions or scripts.
- Optimizing a skill's description or triggering.
- Any request `skill-creator` would handle, in this repository.

## Overrides (apply instead of skill-creator's defaults)

1. **Target `skills/<name>/` and edit in place.** The canonical skill lives at
   `skills/<name>/SKILL.md`, with `scripts/`, `references/`, `reference/` as
   needed. That IS the product - `npx skills add` ships these folders directly,
   so there is nothing to mirror or promote afterwards. `skill-creator` has no
   fixed output path; you supply `skills/<name>/`.
2. **Workspaces go to a gitignored folder.** Put eval workspaces under
   `skill-workspaces/<name>/` and pass that path explicitly to skill-creator's
   scripts. Do NOT let it create `skills/<name>-workspace/` (a duplicate of the
   shipped folder) and do not copy a skill to `/tmp` to edit it. For
   skill-creator's own evals, use `python tools/skill_eval.py` (canonical
   `skill-workspaces/skill-creator/<case>/<run-id>/`); the workflow runs on
   OpenCode, so skip the Claude-only Description Optimization section.
3. **Skip packaging.** Do not run `.skill` packaging
   (`skill-creator/scripts/package_skill.py`); this repo ships folders, not
   archives.
4. **Edit the source directly** rather than following skill-creator's
   copy-to-`/tmp` "updating an existing skill" advice - work in `skills/<name>/`.
5. **Follow dev-agent skill conventions.** Frontmatter: `name`, `description`,
   `tags`, and a `metadata:` block (`version`, `author`); optional `scope: always`
   for always-on skills. `description` must say what the skill does AND when to
   use it (third person, with trigger words), matching the other shipped skills.
   Keep the body ASCII and in the repo's house style.
6. **Do not edit third-party `skill-creator`.** It is vendored at
   `.agents/skills/skill-creator`; edits are lost on update. Wrap it, do not
   modify it.

## Finish

This repo does not run the framework on itself, so there is no `promote` step and
no in-repo runtime. Verify with the repo's own tooling:

1. Build, test, lint:
   `python -m compileall -q skills tools tests`,
   `python -m unittest discover -s tests`,
   `python -m ruff check skills tools tests`.
2. Exercise the skill's behavior via the eval harness (it installs the skill into
   a throwaway consumer repo outside this tree and drives OpenCode):
   `python tools/behavior_eval.py list --skill <name>`, then
   `python tools/behavior_eval.py batch --run-id <id> --skill <name>`.
3. Tell the human to start a new session.
