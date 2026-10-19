# Project - Dev Agent

## What this repo is

This repository **is the Dev Agent framework** - the source that produces the skills users install. It is not a project that *uses* Dev Agent.

- **The product** is the skill folders under `skills/`. Users install them with `npx skills add ...` and run them in their own repositories. **Only `skills/` ships.**
- **`.agents/`** is this repo's own workspace: repo-only tooling skills. It is **never shipped**. The skills CLI also discovers `.agents/skills/`, so every `SKILL.md` there must carry `metadata.internal: true` or it leaks to users.
- **You are a maintainer of the framework, not a consumer of it.** This repo does **not** run the framework on itself: it loads no gateway rulebook, keeps no dogfood mirror, and installs no in-repo runtime. You work directly on `skills/` and verify with `tools/` + `tests/` (see the Maintainer contract below).

## Description

Dev Agent is a drop-in configuration framework (a set of composable skills plus a shared docs/spec system) that turns any AI coding assistant into a structured, memory-aware development team.

## Tech Stack

- Python 3.10+ (stdlib-only engines; no runtime dependencies)
- Ruff 0.17.1 as the only dev dependency (`pyproject.toml` dependency group)
- JavaScript (`skills.sh.json` catalog grouping only)

## Repo map

- `skills/` - **THE PRODUCT.** One folder per shipped skill. `dev-agent` bundles the shared runtime (`runtime/devagent/`), the installer (`scripts/bootstrap.py`), the seed rulebook, and the coder contract; the other six skills are thin wrappers (`SKILL.md` + `references/`) that call the runtime by subcommand. This is the canonical source of truth and exactly what users install.
- `.agents/` - this repo's workspace, never shipped:
  - `.agents/skills/` - repo-only tooling skills: `author-skill` (how to change a skill) and the vendored third-party `skill-creator`; both stamped `metadata.internal: true`
- `tools/` - maintainer engines, not skills. `tools/skill_eval.py` runs the skill-creator golden evals; `tools/behavior_eval.py` runs prompt-level behavior cases; `tools/suite_report.py` diffs the unit suite against its golden baseline.
- `specs/` - what to build: approved specs with a single `Status:` lifecycle (`DRAFTED -> COMPILED -> BUILDING -> BUILT -> REVIEWED -> COMPLETED`) plus `specs/temp/` (gitignored scratchpad)
- `docs/` - what is + why we chose: one topic doc per subsystem (`## Current State` + `## Decision Log`; AI index at `docs/_topics.md`); human landing page at `docs/README.md`
- `tests/` - test suite

> The consumer template lives at `skills/dev-agent/reference/AGENTS.md` - that is the `AGENTS.md` the `dev-agent` installer sets up in *other* repos. **This** file is the maintainer's, and the two are intentionally different.

## Commands

- Build: `python -m compileall -q skills tools tests`
- Test: `python -m unittest discover -s tests -v`
- Lint: `python -m ruff check skills tools tests` (`.agents/skills/` holds the vendored `skill-creator`; it is excluded from lint)
- Suite drift report: `python tools/suite_report.py` (`--update` refreshes `tests/.suite-baseline.json`)
- Behavior evals: `python tools/behavior_eval.py list|init|run|check|accept|baseline|batch|feedback` (`batch --skill <name>` runs N predefined prompts as one review: new_skill vs old_skill + Benchmark summary; `accept` records a checked run as the case baseline and `baseline` reports skill/fixture drift offline)

## Skill-creator evals (maintainers)

The vendored `skill-creator` workflow runs on OpenCode. Do not run its Claude-specific description-optimization scripts (`run_eval.py`, `run_loop.py`, `improve_description.py`) - they hardcode `claude -p`.

- Cases: `tests/fixtures/skill-creator/cases/`
- Runs: `skill-workspaces/skill-creator/<case>/<run-id>/` (gitignored)
- `python tools/skill_eval.py init|run|check|iterate|accept --case <case>`
- Review `review.html`; put the viewer's `feedback.json` in the run dir, then `iterate`. `accept` records the case's golden baseline.
- Live test: `SKILL_EVAL=1 python -m unittest tests.test_skill_creator_live -v` (uses OpenCode and costs tokens).

## Hard rules

- **Author skills only in `skills/<name>/`.** Use the `author-skill` skill to create or change a skill; it lands in `skills/` and that is the end of it.
- **Never add `metadata.internal` to a `skills/` SKILL.md** - that would hide a shipped skill from users. Only the repo-only tooling skills under `.agents/skills/` carry it.
- **Do not hand-edit vendored third-party skills** (`.agents/skills/skill-creator`) beyond its `metadata.internal: true` hiding header. It is upstream (`anthropics/skills`); never run `npx skills update` on this repo — that would overwrite the vendored copy and drop the internal flag.
- **Do not reintroduce the dogfood layer.** No `.agents/rules/` gateway, no `.agents/agents/`, no `.agents/skills/<consumer skill>` mirror, no `.agents/scripts/devagent/`, no `tools/promote.py`. This repo is a source repo, not a consumer.

# MAINTAINER CONTRACT

This repo does **not** load the Dev Agent framework. The gateway rulebook, the
coder contract, the dogfood mirror, and the in-repo runtime were removed on
purpose (see `PLAN-DOGFOOD-REMOVAL.md`). Work like a maintainer editing a
library:

1. **Source of truth is `skills/`.** Edit skills there; never invent a derived copy.
2. **Verify with the repo's own tooling, not the framework's gates:** `python -m
   compileall -q skills tools tests`, `python -m unittest discover -s tests`,
   `python -m ruff check skills tools tests`, and `python tools/suite_report.py`.
3. **Behavior lives in evals, not in this repo's sessions.** `python
   tools/behavior_eval.py` installs a skill into a throwaway consumer repo
   outside this tree and drives OpenCode against it; `python tools/skill_eval.py`
   runs the vendored skill-creator cases.
4. **Do not use the `specs/` phase lifecycle or the framework skills to develop
   the framework.** `specs/` is retained as resolved history; new framework work
   goes through a plain plan (`PLAN.md`, `PLAN-DOGFOOD-REMOVAL.md`).

## Project instructions

Everything this project adds on top of the framework lives in this one section — the shipped skills stay generic.

- `autonomy_level`: supervised
- `Run Prefix`: none — the engines use the active Python interpreter.
