---
name: dev-agent
description: Dev Agent framework installer and runtime - sets up a repository with the gateway rulebook, the coder contract, and the shared devagent runtime, then keeps them in sync. Use when a new project should adopt the Dev Agent framework, the user asks to bootstrap / set up / install the framework or "dev-agent setup", AGENTS.md or .agents/rules/dev-agent-framework.md is missing in a target repo, the runtime under .agents/scripts/devagent/ is missing or outdated (setup --check / --update), the framework install is re-run after a broken or partial setup, or a globally-installed skill must be pointed at a project.
tags:
  - bootstrap
  - scaffold
  - install
  - setup
  - dev-agent
  - framework
  - new project
  - global install
metadata:
  internal: true
  version: 1.0.0
  author: AI Agent
---

# Dev Agent

## Overview

You install and maintain the Dev Agent framework in a target repository. `setup`
does two jobs:

1. **Seeds** the canonical files from this skill's `reference/` folder:

   | Source (skill-local) | Destination (target repo) |
   | :--- | :--- |
   | `reference/AGENTS.md` | `AGENTS.md` (repo root) |
   | `reference/.gitignore` | `.gitignore` (repo root) |
   | `reference/rules/dev-agent-framework.md` | `.agents/rules/dev-agent-framework.md` |
   | `reference/agents/coder.md` | `.agents/agents/coder.md` |
   | `reference/.cursorrules` | `.cursorrules` (repo root) |
   | `reference/.windsurfrules` | `.windsurfrules` (repo root) |

2. **Installs the shared runtime** bundled with this skill (`runtime/devagent/`)
   into `<target>/.agents/scripts/devagent/`, then writes the project-owned
   manifest `<target>/.agents/.devagent.json`.

Every engine command in a bootstrapped project runs through that runtime:

```
python .agents/scripts/devagent/main.py <command> [args]
```

The manifest records the installed runtime version, scope, agent, and a sha256
per runtime file, so `--check` can detect drift and `setup` can repair or
upgrade. The install is atomic: the runtime is staged in
`.agents/scripts/.devagent.tmp/`, renamed into place, and the manifest is
written last — an interrupted install is detectable rather than half-applied.

The two dotfiles are IDE pointer files — one line each, telling Cursor and
Windsurf to load `.agents/rules/dev-agent-framework.md` as the gateway. Only the
framework's own contract is seeded; a project that wants its own rules keeps
them in its own `SYSTEM.md` (the framework neither creates nor manages it).

`reference/agents/coder.md` is the **portable coder subagent contract** (role,
input = the task file only, fetch context on demand, search/replace blocks for
large files, run the task's verification, never commit / never plan / never
expand scope / never touch files it does not Own, sole writer of its own task
file, the trivial direct-fix exception).

## When to Use

- A new (or existing) project should adopt the Dev Agent framework.
- The user asks to "bootstrap", "set up", "install the framework", or run
  "dev-agent setup" in a repo.
- A target repo is missing `AGENTS.md` or `.agents/rules/dev-agent-framework.md`.
- The runtime is missing or out of date (`.agents/scripts/devagent/` absent, or
  `setup --check` reports drift).
- Re-running a previous install after a broken or partial setup, or upgrading
  the runtime after the skill was updated.

## Instructions

1. **Identify the target repo.** The target is the repository being set up —
   almost never the repo this skill lives in. Confirm the absolute path.

2. **Dry-run first.** Always preview:
   `python <this-skill>/scripts/bootstrap.py setup --target <abs-path> --dry-run`
   Show the human the per-file report. `setup` is the default command, so
   `--target <abs-path> --dry-run` alone behaves the same.

3. **Overwrite policy.** Seeds marked `overwrite:` are replaced by the canonical
   seed (e.g. a filled-in `AGENTS.md` is lost) — confirm before a real run that
   overwrites anything. A target where every seed is `new:`/`ok:` needs no
   confirmation. **`.gitignore` is never overwritten:** an existing one only
   receives the seed's missing ignore patterns (idempotent). Runtime files are
   owned by the framework; `--update` writes a `*.bak` next to any file the user
   had modified before replacing it.

4. **Run setup:**
   `python <this-skill>/scripts/bootstrap.py setup --target <abs-path>`
   Options: `--scope project|global`, `--agent <name>` (recorded in the
   manifest), `--check`, `--update`.

5. **Keep it in sync.** `python <this-skill>/scripts/bootstrap.py --check
   --target <abs-path>` is read-only and exits 1 on drift (a CI guard).
   `--update` reconciles the runtime to the bundled version, backs up modified
   files, and rewrites the manifest. A packaged runtime **older** than the
   installed one is refused (exit 2) — a deploy can never silently downgrade.

6. **Opt-in wrapper skills (`--skills`).** The other core skills are installed
   from the skills catalog, never copied:
   `python <this-skill>/scripts/bootstrap.py setup --target <abs-path> --skills mandatory`
   accepts `mandatory`, `all`, or a comma list, and delegates to
   `npx skills add <source> --skill …`. It is **opt-in and never auto-prompts**.
   Without `npx` the runtime still installs and the manual command is printed.
   Pass `--scope global` / `--agent <name>` to match a global install.

7. **Post-install.** The target now has the gateway rulebook, the coder
   contract, and the runtime. Next: run commands via
   `python .agents/scripts/devagent/main.py <command>`; add that exact prefix to
   the harness's always-allow execution list. If the target should also get the
   other core skills, run step 6.

8. **Adapter notes.** The seeded `.agents/agents/coder.md` is the *behavioral*
   contract only — harness-agnostic. Each harness adds a **thin adapter** on top:
   bind a small (≈32k-class) model and a narrow permission surface to that file
   and load it as the coder subagent's system prompt. Setup does not seed the
   adapter; remind the human to point their harness's coder at
   `.agents/agents/coder.md`.

## Global installs

A `-g` skill copy lives in the harness's global skills directory and serves many
projects. The runtime is **per project**: each project runs `setup` once, and the
runtime resolves its project by walking up from the current working directory for
`.agents/.devagent.json` — never by the skill's own location. `setup` is the only
skill-relative command; every other command is project-relative.

## Output Contract

- Dry-run: the per-file list (`new:` / `ok:` / `overwrite:` / `append:`) verbatim
  in block 2; block 4 states the real run proceeds only on confirmation when any
  `overwrite:` is present.
- Setup: the per-file lines plus the `dev-agent setup complete:` summary
  verbatim; block 4 states the target is set up and names the next step.
- Check: the `ok` / `stale` / `modified` / `missing` / `orphan` lines and the
  exit status verbatim; drift is never reported as success.
- Errors (bad target, source tree refused, downgrade refused, missing seeds):
  the engine's error message verbatim; no partial install is reported as success.

## Notes

- **The installer is location-agnostic and stdlib-only** (`python3`, no
  dependencies). It locates its own `reference/` and `runtime/` folders relative
  to the script, so it works from any install path (symlinked or copied dirs).
  Only `--skills` needs `npx`.
- **Self-bootstrap is refused:** running `setup --target` at or above the
  skill's own repo root exits 1 — that repo is the framework's source of truth,
  not a target.
- **`--target` defaults to `.`** (the current working directory); confirm it is
  the repo you mean before running.
- **Reference files are the canonical seeds;** the bundled `runtime/devagent/` is
  the canonical runtime. To change what setup installs, edit those under this
  skill — never the destination. Destinations are generated output.
- **Idempotent:** re-running `setup` against an up-to-date target reports every
  file `unchanged:` and writes nothing. `.gitignore` appends only missing
  patterns, so repeated runs never duplicate lines.
