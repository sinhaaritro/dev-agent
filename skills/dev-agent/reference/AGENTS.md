# Project - [PROJECT_NAME]

## Description
[Brief 1-2 sentence description of the project is, does.]

## Tech Stack

- [STACK_1]
- [STACK_2]

## Repo map

- `src/` - application source code
- `tests/` - test suite
- `specs/` - what to build: approved specs with a single `Status:` lifecycle (`DRAFTED → COMPILED → BUILDING → BUILT → REVIEWED → COMPLETED`) + `specs/temp/` (gitignored scratchpad)
- `docs/` - what is + why we chose: topic docs, one per subsystem (decision log per topic; AI index at `_topics.md`); human landing page at `docs/README.md`
- `.agents/` - machine space: `MAP.md` (generated skill index), `rules/`, `skills/`, `scripts/`

## Commands

- Build: <command>
- Test: <command>
- Lint: <command>

# DEV AGENT

Read `.agents/rules/dev-agent-framework.md` (the framework's behavioral contract — read it and obey).

## Project instructions

Everything this project adds on top of the framework lives in this one section —
the shipped skills stay generic. Fill in the settings the framework reads:

- `autonomy_level`: supervised
- `Run Prefix`: <your environment activator, e.g. `.venv\Scripts\activate &&`, or "none">
- <project-specific behavior / per-skill notes>

A project's own rules (beyond the framework) may live in a separate `SYSTEM.md`;
the framework neither creates nor manages it.
