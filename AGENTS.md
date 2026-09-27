# Project - Dev Agent

## Description
This is a framework for a agent setup. This repo, has the skills that will help agents to do agentinc coding.

## Tech Stack

- Python
- Javascript

## Repo map

- `src/` - application source code
- `tests/` - test suite
- `specs/` - what to build: approved specs with a lifecycle (DRAFT -> APPROVED) + `specs/temp/` (gitignored scratchpad)
- `docs/` - what is + why we chose: reference series `001..007`, topic docs (per-subsystem decision log; AI index at `docs/_topics.md`); human landing page at `docs/README.md`
- `.agents/` - machine space: `MAP.md` (generated skill index), `.agents/rules/`, `.agents/skills/`, `.agents/scripts/`

## Commands

- Build: `python -m compileall -q .agents tests`
- Test: `python -m unittest discover -s tests -v`
- Lint: `python -m ruff check .agents tests`

# DEV AGENT

Read `.agents/rules/system.md` (behavioral contract - read it and obey)
