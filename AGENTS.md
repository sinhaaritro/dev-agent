# Project - Dev Agent

## What this repo is

This repository **is the Dev Agent framework** - the source that produces the
skills users install. It is not a project that *uses* Dev Agent.

- **The product** is the skill folders under `skills/`. Users install them with
  `npx skills add ...` and run them in their own repositories. **Only `skills/`
  ships.**
- **`.agents/`** is this repo's own workspace: the gateway rules, the derived
  dogfood copy of the skills, and repo-only tooling. It is **never shipped**. The
  skills CLI also discovers `.agents/skills/`, so every `SKILL.md` there must
  carry `metadata.internal: true` or it leaks to users - the `promote` engine
  enforces this.
- **You are a maintainer of the framework, not a consumer of it.** The consumer
  contract in `.agents/rules/system.md` governs *how* you work, but your output is
  the shipped skills in `skills/`.

## Description

Dev Agent is a drop-in configuration framework (a set of composable skills plus a
shared docs/spec system) that turns any AI coding assistant into a structured,
memory-aware development team.

## Tech Stack

- Python 3.10+ (stdlib-only engines; no runtime dependencies)
- Ruff 0.17.1 as the only dev dependency (`pyproject.toml` dependency group)
- JavaScript (`skills.sh.json` catalog grouping only)

## Repo map

- `skills/` - **THE PRODUCT.** One folder per shipped skill (`SKILL.md` plus
  `scripts/`, `references/`, `reference/`). This is the canonical source of truth
  and exactly what users install.
- `.agents/` - this repo's workspace, never shipped:
  - `.agents/rules/system.md` - behavioral contract (loaded every session)
  - `.agents/agents/coder.md` - the coder subagent contract
  - `.agents/skills/` - the derived dogfood mirror of `skills/` (does not ship;
    stamped `metadata.internal: true`) plus repo-only tools (`promote`,
    `author-skill`) and vendored third-party `skill-creator`
  - `.agents/MAP.md` - generated skill index (gitignored)
- `tools/` - maintainer engines, not skills. `tools/promote.py` mirrors `skills/`
  into `.agents/skills/`; `tools/skill_eval.py` runs the skill-creator golden
  evals; `tools/behavior_eval.py` runs prompt-level behavior cases;
  `tools/suite_report.py` diffs the unit suite against its golden baseline.
- `specs/` - what to build: approved specs with a single `Status:` lifecycle
  (`DRAFTED -> COMPILED -> BUILDING -> BUILT -> REVIEWED -> COMPLETED`) plus
  `specs/temp/` (gitignored scratchpad)
- `docs/` - what is + why we chose: reference series `001..007`, topic docs
  (per-subsystem decision log; AI index at `docs/_topics.md`); human landing page
  at `docs/README.md`
- `tests/` - test suite

> The consumer template lives at `skills/bootstrap/reference/AGENTS.md` - that is
> the `AGENTS.md` bootstrap installs into *other* repos. **This** file is the
> maintainer's, and the two are intentionally different.

## Commands

- Build: `python -m compileall -q .agents skills tools tests`
- Test: `python -m unittest discover -s tests -v`
- Lint: `python -m ruff check skills tools tests` (`.agents/skills/` is the derived mirror + vendored `skill-creator`; it is excluded from lint)
- Skill sync (guard): `python tools/promote.py --check`
- Suite drift report: `python tools/suite_report.py` (`--update` refreshes `tests/.suite-baseline.json`)
- Behavior evals: `python tools/behavior_eval.py list|init|run|check|batch|feedback` (`batch --skill <name>` runs N predefined prompts as one review: new_skill vs old_skill + Benchmark summary)

## Skill-creator evals (maintainers)

The vendored `skill-creator` workflow runs on OpenCode. Do not run its
Claude-specific description-optimization scripts (`run_eval.py`,
`run_loop.py`, `improve_description.py`) - they hardcode `claude -p`.

- Cases: `tests/fixtures/skill-creator/cases/`
- Runs: `skill-workspaces/skill-creator/<case>/<run-id>/` (gitignored)
- `python tools/skill_eval.py init|run|check|iterate|accept --case <case>`
- Review `review.html`; put the viewer's `feedback.json` in the run dir, then
  `iterate`. `accept` records the case's golden baseline.
- Live test: `SKILL_EVAL=1 python -m unittest tests.test_skill_creator_live -v`
  (uses OpenCode and costs tokens).

## Hard rules

- **Author skills only in `skills/<name>/`.** Never create or edit a skill under
  `.agents/skills/` - it is derived, and the next `promote` overwrites it. Use the
  `author-skill` skill to change a skill, then run `promote`.
- **Never add `metadata.internal` to a `skills/` SKILL.md** - that would hide a
  shipped skill from users. Only the derived mirror carries it.
- **Do not hand-edit vendored third-party skills** (`.agents/skills/skill-creator`)
  beyond its `metadata.internal: true` hiding header. It is upstream
  (`anthropics/skills`); never run `npx skills update` on this repo — that would
  overwrite the vendored copy and drop the internal flag.

# DEV AGENT

Read `.agents/rules/system.md` (behavioral contract - read it and obey)
