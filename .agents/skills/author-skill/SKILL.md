---
name: author-skill
description: Author or edit a skill in THIS repo - creates, fixes, or optimizes a skill under skills/ and hands off to promote. Takes precedence over skill-creator in this repository. Use when creating a new skill, editing or optimizing an existing skill's instructions, or changing a skill's description or triggering, inside dev-agent.
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
framework SOURCE: the product is the folders under `skills/`. Any change to a
skill lands in `skills/<name>/` and is then mirrored into `.agents/skills/` by
the `promote` skill. This skill overrides `skill-creator` here.

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
   needed. NEVER author into `.agents/skills/` - that is the derived mirror and
   the next `promote` overwrites it. `skill-creator` has no fixed output path;
   you supply `skills/<name>/`.
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

1. Run the `promote` skill: `python tools/promote.py apply`, then
   `python tools/promote.py --check` must print `promote: clean`.
2. Rebuild the index:
   `python .agents/skills/map-generator/scripts/generate_map.py --force`.
3. Verify the shipping set: the default `npx skills add . --list` shows the new
   skill when it is a shipped skill, and never shows repo-only skills.
4. Tell the human to start a new session.
