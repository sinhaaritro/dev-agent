# Dev Agent

> A modular, multi-agent workspace template that turns any AI coding assistant into a structured, memory-aware development team.

---

## What Is This?

**Dev Agent** is a drop-in configuration framework for AI-powered code editors (Antigravity, Pi, Cursor, Windsurf, Claude Code, Gemini Code Assist, and others). It provides a composable set of **skills** and a shared documentation system that turn a repository into a workspace where **multiple humans and multiple AI agents work the same codebase as equals**.

**Built for multi-human + multi-AI collaboration.** Humans and agents hand the work to each other — a human delegates to an agent, the agent hands back at a gate, another agent (or another human, on another machine) picks up exactly where it left off. Neither side is the authority: every handoff is recorded, and either side can take over at any pause point.

**Pause loops everywhere.** The lifecycle (Plan → Handoff → Build → Review) is full of deliberate stopping points — Socratic gates on ambiguity, an explicit approval gate before code is written, a verification gate after — so work is never locked behind a single session or a single actor.

Instead of relying on ad-hoc prompts, Dev Agent gives your agent:

- **Persistent memory** in `docs/` that survives across sessions, humans, and agents
- **Structured workflows** with planning gates, approval checkpoints, and verification
- **Recorded handoffs** so any human or any agent can resume the task mid-flight

---

## Quick Start

### 1. Install via the [skills.sh](https://skills.sh) CLI (Recommended)

Skills are installable with `npx skills`. Browse the grouped catalog at https://skills.sh/sinhaaritro/dev-agent.

```bash
# Install a single skill
npx skills add github/sinhaaritro/dev-agent --skill auto-router

# Install the 7 core skills
npx skills add github/sinhaaritro/dev-agent --skill bootstrap,auto-router,map-generator,phase-protocol,spec-builder,task-cleaner,verification-runner

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

### 2. Set Up an Existing Repo

To adopt the framework in a repo you already have, install the gateway files — `AGENTS.md`, `.agents/rules/system.md`, plus the IDE pointers `.cursorrules` / `.windsurfrules`:

**Option A — copy the files** (from a clone of this repo):

```bash
cp <dev-agent>/AGENTS.md                 /path/to/your/repo/AGENTS.md
mkdir -p /path/to/your/repo/.agents/rules
cp <dev-agent>/.agents/rules/system.md   /path/to/your/repo/.agents/rules/system.md
cp <dev-agent>/.cursorrules              /path/to/your/repo/.cursorrules
cp <dev-agent>/.windsurfrules            /path/to/your/repo/.windsurfrules
```

**Option B — the bootstrap skill** (from a clone of this repo, or a globally installed copy):

```bash
python .agents/skills/bootstrap/scripts/bootstrap.py --target /path/to/your/repo
```

Preview first with `--dry-run`; the engine reports each file as `new:` / `ok:` / `overwrite:`, is idempotent, and refuses to run against this framework's own source tree.

### 3. Start Coding

Open the project in your AI-powered editor. The agent reads `AGENTS.md` and `.agents/rules/system.md` on startup, auto-loads the `scope: always` skills, and routes every request through the lane taxonomy.

---

## Architecture Overview

```
dev-agent/
├── AGENTS.md                   # Install guide + agent contract (entry point)
├── skills.sh.json              # skills.sh catalog groupings
├── .cursorrules                # Cursor IDE → points to .agents/rules/system.md
├── .windsurfrules              # Windsurf IDE → points to .agents/rules/system.md
├── .agents/                    # Machine space — agent configuration
│   ├── rules/
│   │   └── system.md           # Gateway rulebook — loaded on every session
│   └── skills/                 # Modular capability packages (7 skills)
│       ├── bootstrap/          #   installs AGENTS.md + system.md into a target repo
│       ├── auto-router/        #   lane triage + skill recall (always on)
│       ├── map-generator/      #   builds the local skill index (MAP.md)
│       ├── phase-protocol/     #   Plan → 1.5-Handoff → Build → Review + gates (always on)
│       ├── spec-builder/       #   spec drafts, promotion, ADRs, handoffs, docs TOC
│       ├── task-cleaner/       #   purges the scratchpad on acceptance
│       └── verification-runner/#   test execution, retries, circuit breaker
└── docs/                       # Human + AI shared space — the committed knowledge
    ├── specs/                  #   what to build — specs with a lifecycle (DRAFT → APPROVED)
    ├── decisions/              #   why we chose — immutable ADRs
    ├── reference/              #   what is — living authoritative docs
    └── temp/                   #   ephemeral scratchpad (gitignored; handoff records live here)
```

Every skill is self-contained: a `SKILL.md` (what it does, when to use it) plus `scripts/` (a stdlib-only Python engine) and optional `references/`. `MAP.md` is generated locally at session start and never committed.

---

## IDE Compatibility

AI Setup works across multiple AI-powered editors through a pointer-based loading system:

| IDE | Config File | How It Loads |
|:---|:---|:---|
| **Cursor** | `.cursorrules` | Points to `.agents/rules/system.md` |
| **Windsurf** | `.windsurfrules` | Points to `.agents/rules/system.md` |
| **Claude Code** | `.agents/rules/system.md` | Direct rule loading |
| **Antigravity** | `.agents/rules/system.md` | Direct rule loading |

The `system.md` file acts as the universal gateway — it loads mandatory startup skills, defines universal rules, and bootstraps the memory and routing systems.

---

## License

This project is provided as a workspace template. Feel free to fork, customize, and adapt it to your development workflow.
