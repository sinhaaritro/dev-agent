# Installation

Skills are installable via the [skills.sh](https://skills.sh) CLI (`npx skills`). Browse the grouped catalog at https://skills.sh/sinhaaritro/dev-agent.

```bash
# Install a single skill
npx skills add github/sinhaaritro/dev-agent --skill auto-router

# Install the 6 core skills
npx skills add github/sinhaaritro/dev-agent \
  --skill auto-router --skill map-generator --skill phase-protocol \
  --skill spec-builder --skill task-cleaner --skill verification-runner

# Install all skills
npx skills add github/sinhaaritro/dev-agent --all
```

Useful flags: `-g` (install globally to `~/.config/opencode/skills/`), `-a <agent>` (target a specific agent), `-y` (skip prompts), `--copy` (copy files instead of symlinks).

```bash
# Non-interactive, global, opencode-only
npx skills add github/sinhaaritro/dev-agent --skill phase-protocol -g -a opencode -y
```

Management:

```bash
npx skills list            # list installed skills
npx skills update          # update to latest
npx skills remove <name>   # remove a skill
```

# Project - [PROJECT_NAME]

## Description
[Brief 1-2 sentence description of the project is, does.]

## Tech Stack

- [STACK_1]
- [STACK_2]

## Repo map

- `src/` - application source code
- `tests/` - test suite
- `docs/` - shared space: `specs/`, `decisions/`, `reference/`, and `temp/` (gitignored scratchpad); human landing page at `docs/README.md`
- `.agents/` - machine space: `MAP.md` (generated skill index), `rules/`, `skills/`, `scripts/`

## Commands

- Build: <command>
- Test: <command>
- Lint: <command>

# DEV AGENT

Read `.agents/rules/system.md` (behavioral contract - read it and obey)
