---
name: agentic-code-start
description: >
  Initialize or bootstrap a new developer project workspace with standard agentic configurations,
  workflows, and personas. Use this skill when setting up a repository, starting a new project,
  configuring agentic workflows/personas, or when asked to initialize, bootstrap, or unpack workspace files.
---

# Agentic Code Start

This skill provides the bootstrap and workspace initialization routines to set up standard agent personas, workflows, rules, and editor configurations (Cursor and Windsurf).

## Triggering the Initialization

When this skill is loaded, check if the standard agent folders (`.agents/personas/`, `.agents/workflows/`, and `.agents/rules/`) are present in the project root.

If they are missing or if you are explicitly asked to bootstrap/initialize the workspace, you **MUST** run the bootstrap script:

```bash
python .agents/skills/agentic-code-start/scripts/bootstrap.py
```

## Setup Guidelines

The bootstrap script will automatically:
1. Copy standard templates (`personas`, `workflows`, `rules`, `Taskfile.yml`, `.gitignore`, `skills-lock.json`) from the skill's `templates/` folder to your project root.
2. Ensure existing files with custom modifications are **never** overwritten, throwing safety warnings if differences exist.
3. Configure routing files (`.cursorrules` and `.windsurfrules`) to enable dynamic pointer loading for other IDE agents.
4. Execute `npx skills update` to install and synchronize dependent capabilities.

Once the bootstrap execution finishes, inspect the output to report which files were created and if any safety warnings were issued.
