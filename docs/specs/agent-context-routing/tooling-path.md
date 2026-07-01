# SPEC-001g: TOOLING Path Context Trace

- **Status**: Approved
- **Author**: @orchestrator
- **Created**: 2026-06-24
- **Parent Spec**: [SPEC-001: Agent Context & Routing](index.md)

## 1. Overview
Trace of what is loaded in the AI context when managing dependencies, configurations, compiling, testing, linting, or deploying (e.g., "install", "setup", "configure", "deploy", "release", "ship").

## 2. Context Load Steps
1. **Specialist Persona**: Boots `@engineer` (for packages/config) or `@qa` (for linting/shipping/tests).
2. **Environment & Build Context**: Reads dependency lists (`package.json`, `requirements.txt`), task definitions (`Taskfile.yml`), linters/formatters configs, and `.env.example`.
3. **Behavioral Mode Rules**: Adopts `SHIP` mode.
4. **Active Tools**: Enables environment modification and execution tools (`run_command`, `write_to_file`). Disables core application code modifications.

> [!NOTE]
> **Traditional Agent Difference**:
> Traditional agents treat configuration modifications and code shipping as standard file edits, often introducing build-breaking dependencies, running shell commands without verifying lockfiles, or failing to run automated pre-ship verification test suites.
