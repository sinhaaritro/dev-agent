---
name: bootstrap
description: Project scaffolder - installs the Dev Agent framework (AGENTS.md and .agents/rules/system.md) into a target repository from the skill's reference/ seed files. Use when a new project should adopt the framework, the user asks to bootstrap or set up a repo, AGENTS.md or .agents/rules/ is missing in a target repo, or the framework install is re-run after a broken setup.
tags:
  - bootstrap
  - scaffold
  - install
  - setup
  - new project
metadata:
  version: 1.0.0
  author: AI Agent
---

# Bootstrap

## Overview

You install the Dev Agent framework into a target repository by copying the canonical seed files from this skill's `reference/` folder to their proper locations:

| Source (skill-local) | Destination (target repo) |
| :--- | :--- |
| `reference/AGENTS.md` | `AGENTS.md` (repo root) |
| `reference/.gitignore` | `.gitignore` (repo root) |
| `reference/rules/system.md` | `.agents/rules/system.md` |
| `reference/agents/coder.md` | `.agents/agents/coder.md` |
| `reference/.cursorrules` | `.cursorrules` (repo root) |
| `reference/.windsurfrules` | `.windsurfrules` (repo root) |

The two dotfiles are IDE pointer files — one line each, telling Cursor and Windsurf to load `.agents/rules/system.md` as the gateway.

`reference/agents/coder.md` is the **portable coder subagent contract** (role, input = the task file only, fetch context on demand, search/replace blocks for large files, run the task's verification, never commit / never plan / never expand scope / never touch files it does not Own, sole writer of its own task file, the trivial direct-fix exception). Bootstrap seeds it so every target repo has the contract the Build phase's coder dispatch relies on.

Copy mechanics belong to `scripts/bootstrap.py`; you decide WHERE the target repo is and confirm the overwrite policy. The engine never guesses a target: you pass `--target` explicitly, and the engine refuses to run against this framework's own source tree.

## When to Use

- A new (or existing) project should adopt the Dev Agent framework.
- The user asks to "bootstrap", "set up", or "install the framework" in a repo.
- A target repo is missing `AGENTS.md` or `.agents/rules/system.md` and the agent needs the gateway rulebook to function.
- Re-running a previous install after a broken or partial setup.

## Instructions

1. **Identify the target repo.** The target is the repository being set up — almost never the repo this skill lives in. Confirm the absolute path before running.
2. **Dry-run first.** Always preview:
   `python <this-skill>/scripts/bootstrap.py --target <abs-path> --dry-run`
    The report lists every file as `new:`, `ok:` (identical, nothing to do), `overwrite:` (differs, will be replaced), or `append:` (existing `.gitignore` will get only its missing patterns added). Show it to the human.
    3. **Overwrite policy.** Files marked `overwrite:` are replaced by the canonical seed. Existing content in the target that diverges (e.g. a filled-in `AGENTS.md`) is lost — confirm with the human before a real run that overwrites anything. A target where every file is `new:` or `ok:` needs no confirmation. **`.gitignore` is never overwritten:** an existing one is only appended with the seed's missing ignore patterns (idempotent), so a target's own ignores are always preserved.
4. **Run the install:**
   `python <this-skill>/scripts/bootstrap.py --target <abs-path>`
   Success contract: one line per file (`installed:` / `updated:` / `unchanged:`) followed by `bootstrap complete: N installed, M updated, K unchanged`.
5. **Post-install.** The target now has the gateway rulebook and the coder contract. Tell the human the next step: open the target in their AI editor (the agent reads `AGENTS.md` and `.agents/rules/system.md` on startup). If the target should also get the other core skills, install them via `npx skills add` per the target's AGENTS.md.
6. **Adapter notes.** The seeded `.agents/agents/coder.md` is the *behavioral* contract only — it is harness-agnostic. Each harness adds a **thin adapter** on top: bind a small (≈32k-class) model and a narrow permission surface to that file, and load it as the coder subagent's system prompt. The adapter is per-harness (it lives in the harness's own subagent mechanism), so bootstrap does not seed it; remind the human to point their harness's coder at `.agents/agents/coder.md`.

## Output Contract

- Dry-run: the per-file list (`new:` / `ok:` / `overwrite:` / `append:`) verbatim in block 2; block 4 states the real run proceeds only on confirmation when any `overwrite:` is present.
- Install: the per-file lines plus the `bootstrap complete:` summary verbatim; block 4 states the target is bootstrapped and names the next step.
- Errors (bad target, source tree refused, missing seed files): the engine's error message verbatim; no partial install is reported as success.

## Notes

- **The engine is location-agnostic and stdlib-only** (`python3`, no dependencies). It locates its own `reference/` folder relative to the script, so it works from any install path (symlinked or copied skill dirs).
- **Self-bootstrap is refused:** running with `--target` at or above the skill's own repo root exits 1 — this repo is the framework's source of truth, not a bootstrap target.
- **`--target` is required.** No defaults, no guessing. A relative path is resolved against the current working directory and reported in the output.
- **Reference files are the canonical seeds.** To change what bootstrap installs, edit the files under `reference/` in this skill — never the destination. Destinations are generated output.
- **Idempotent:** re-running against an already-bootstrapped target prints `unchanged:` for every file and changes nothing. `.gitignore` appends only patterns not already present, so repeated runs never duplicate lines.
