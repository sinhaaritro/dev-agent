# Dev Agent

> A modular, multi-agent workspace template that turns any AI coding assistant into a structured, memory-aware development team.

---

## What Is This?

**Dev Agent** is a drop-in configuration framework for AI-powered code editors (Antigravity, Pi, Cursor, Windsurf, Claude Code, Gemini Code Assist, and others). It provides a composable set of **skills** and a shared documentation system that turn a repository into a workspace where **multiple humans and multiple AI agents work the same codebase as equals**.

**Built for multi-human + multi-AI collaboration.** Humans and agents hand the work to each other — a human delegates to an agent, the agent hands back at a gate, another agent (or another human, on another machine) picks up exactly where it left off. Neither side is the authority: every hand-back is recorded, and either side can take over at any pause point.

**Pause loops everywhere.** The lifecycle (`DRAFTED → COMPILED → BUILDING → BUILT → REVIEWED → COMPLETED`, with the Vetting and Sign-off gates) is full of deliberate stopping points — Socratic gates on ambiguity, an explicit approval gate before code is written, a verification gate after — so work is never locked behind a single session or a single actor.

Instead of relying on ad-hoc prompts, Dev Agent gives your agent:

- **Persistent memory** in `docs/` that survives across sessions, humans, and agents
- **Structured workflows** with planning gates, approval checkpoints, and verification
- **Recorded hand-backs** so any human or any agent can resume the task mid-flight

---

## Quick Start

### 1. Install via the [skills.sh](https://skills.sh) CLI (Recommended)

Skills are installable with `npx skills`. Browse the grouped catalog at https://skills.sh/sinhaaritro/dev-agent.

```bash
# Install a single skill
npx skills add git@github.com:sinhaaritro/dev-agent.git --skill auto-router

# Install the 7 core skills
npx skills add git@github.com:sinhaaritro/dev-agent.git \
  -s dev-agent -s auto-router -s map-generator \
  -s phase-protocol -s spec-builder \
  -s task-cleaner -s verification-runner

# Install all skills
npx skills add git@github.com:sinhaaritro/dev-agent.git -s '*'
```

Useful flags: `-g` (install globally to `~/.config/opencode/skills/`), `-a <agent>` (target a specific agent), `-y` (skip prompts), `--copy` (copy files instead of symlinks).

**Global installs.** With `-g` the skills live under `~/.config/opencode/skills/`, not the project. The engines no longer run from the skill folder: the `dev-agent` skill installs a shared runtime into each project at `.agents/scripts/devagent/`, and every command runs project-relative — `python .agents/scripts/devagent/main.py <command>`. Run `dev-agent`'s `setup` once per project (from wherever the skill is installed) and a global install works in every repo; the runtime resolves the project by walking up from the current working directory.

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

### 2. Bootstrap your project with the `dev-agent` skill (Official)

Installing skills only makes them available to the agent — it does **not** set the project up. The official flow installs the `dev-agent` skill, then runs its `setup` to seed the framework into the project you are working in:

```bash
# The dev-agent skill installs the shared runtime + rulebook into the current repo
python <dev-agent-skill>/scripts/bootstrap.py setup --target .
```

`<dev-agent-skill>` is wherever the skills CLI put the `dev-agent` folder (for a `-g` install, `~/.config/opencode/skills/dev-agent/`; for a project install, `.agents/skills/dev-agent/`). Preview first with `--dry-run`. Setup seeds:

- `AGENTS.md`, `.gitignore`, `.cursorrules`, `.windsurfrules` at the repo root
- `.agents/rules/dev-agent-framework.md` (the gateway rulebook) and `.agents/agents/coder.md` (the coder contract)
- the shared runtime at `.agents/scripts/devagent/`, plus the `.agents/.devagent.json` manifest

After that, the agent handles it: just ask it to "run dev-agent setup" and it runs the skill for you. Keep the install in sync with `setup --check` (read-only, exits 1 on drift) and `setup --update`. Every engine command then runs project-relative as `python .agents/scripts/devagent/main.py <command>`.

### 3. Start Coding

Open the project in your AI-powered editor. The agent reads `AGENTS.md` and `.agents/rules/dev-agent-framework.md` on startup, auto-loads the `scope: always` skills, and routes every request through the lane taxonomy.

---

## Architecture Overview

This repo *is* the framework source. The **product** is `skills/` — that is what users install. Everything under `.agents/` is this repo's own workspace and is **never shipped**.

```
dev-agent/
├── AGENTS.md                   # Maintainer briefing (entry point)
├── skills.sh.json              # skills.sh catalog groupings
├── .cursorrules                # Cursor IDE → points to .agents/rules/dev-agent-framework.md
├── .windsurfrules              # Windsurf IDE → points to .agents/rules/dev-agent-framework.md
├── skills/                     # PRODUCT — installable skills (this is what ships)
│   ├── dev-agent/              #   installer + shared runtime (rulebook, coder contract, .agents/scripts/devagent/)
│   ├── auto-router/            #   lane triage + skill recall (always on)
│   ├── map-generator/          #   builds the local skill index (MAP.md)
│   ├── phase-protocol/         #   the Status lifecycle (DRAFTED → COMPILED → BUILDING → BUILT → REVIEWED → COMPLETED) + gates (always on)
│   ├── spec-builder/           #   spec drafts, promotion, task files, docs TOC
│   ├── task-cleaner/           #   purges the scratchpad on acceptance
│   └── verification-runner/    #   test execution, retries, circuit breaker
├── tools/                      # Maintainer engines (never shipped)
│   └── promote.py              #   mirrors skills/ down into .agents/skills/
├── .agents/                    # Repo workspace — NEVER shipped
│   ├── rules/dev-agent-framework.md         #   Gateway rulebook — loaded on every session
│   ├── agents/coder.md         #   coder subagent contract
│   └── skills/                 #   derived mirror (internal) + repo-only tools
├── specs/                      # What to build — spec groups with a lifecycle (NNN-SPEC + NNN-TASK + approvals + report)
│   └── temp/                   #   ephemeral draft-stage scratchpad (gitignored)
└── docs/                       # What is + why we chose — topic docs (Current State + Decision Log), README guide, generated index
```

Only the `dev-agent` skill carries code: it bundles the shared stdlib-only runtime and the installer. The other six are thin wrappers — a `SKILL.md` (what it does, when to use it) plus optional `references/` — that invoke the runtime at `.agents/scripts/devagent/main.py`. Only `skills/` ships — the skills CLI also scans `.agents/skills/`, so every copy there carries `metadata.internal: true` and stays hidden from users. `MAP.md` is generated locally at session start and never committed.

---

## IDE Compatibility

AI Setup works across multiple AI-powered editors through a pointer-based loading system:

| IDE | Config File | How It Loads |
|:---|:---|:---|
| **Cursor** | `.cursorrules` | Points to `.agents/rules/dev-agent-framework.md` |
| **Windsurf** | `.windsurfrules` | Points to `.agents/rules/dev-agent-framework.md` |
| **Claude Code** | `.agents/rules/dev-agent-framework.md` | Direct rule loading |
| **Antigravity** | `.agents/rules/dev-agent-framework.md` | Direct rule loading |

The `dev-agent-framework.md` file acts as the universal gateway — it loads mandatory startup skills, defines universal rules, and bootstraps the memory and routing systems.

---

## Development Setup (maintainers)

The shipped skills are stdlib-only: there are **no runtime dependencies**. Python 3.10+ is required; Ruff is the only dev tool.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux (use `python3` instead of `python` if needed)
source .venv/bin/activate

python -m pip install --group dev
```

`.venv/` is local to the machine and is **not portable between operating systems** — Windows and Linux use different interpreter layouts. It is gitignored, so when you switch OS just delete it and re-run the commands above; each environment is recreated from `pyproject.toml`.

If pip is older than 25.1 (no `--group` support), install the pinned tool directly: `python -m pip install ruff==0.17.1`.

Canonical commands (from the repo root):

```bash
python -m compileall -q .agents skills tools tests   # Build
python -m unittest discover -s tests -v              # Test
python -m ruff check skills tools tests              # Lint
python tools/promote.py --check                      # Skill mirror guard
```

`pyproject.toml` holds the Ruff policy (target Python 3.10). `.agents/skills/` is excluded from lint because it is the derived mirror and contains the vendored `skill-creator`.

---

## License

This project is provided as a workspace template. Feel free to fork, customize, and adapt it to your development workflow.
