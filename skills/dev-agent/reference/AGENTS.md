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
- `docs/` - what is + why we chose: topic docs, one per subsystem (decision log per topic; generated AI index at `_topics.md`); human landing page at `docs/README.md`. `README.md`, `_topics.md`, and underscore-prefixed names are reserved, not topics.
- `.agents/` - machine space: `MAP.md` (generated skill index), `rules/`, `skills/`, `scripts/`

## Commands

A single-stack project keeps one flat list. A mixed-stack project groups commands under one
`### <area>` heading per stack, plus an optional `- Skills:` line naming the domain skills
whose coders work in that area (task files render them by path):

- Build: <command>
- Test: <command>
- Lint: <command>

Mixed-stack example (replace the flat list above with this shape):

```markdown
## Commands

### astro-site
- Build: npm run build
- Test: npm run test
- Lint: npm run lint
- Skills: astro-framework, shadcn, design-system

### python-scripts
- Build: python -m compileall -q scripts
- Test: python -m unittest discover -s scripts/tests
- Lint: python -m ruff check scripts
```

`docs/_topics.md` is generated: never hand-edit it; run
`python .agents/scripts/devagent/main.py map sync-docs` after changing any `docs/` file
(`map sync-docs --check` reports staleness, and `verify doctor` fails on it).

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
