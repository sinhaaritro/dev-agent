# HARNESS TIERING - MODEL & HARNESS STRATEGY PER STATUS

Load when a session involves a harness or model-tier choice (deployment, CI setup, model routing). Situational, not a baseline rule.

| Execution Layer | Preferred Model Tier | Example Harnesses | Key Responsibility |
| :--- | :--- | :--- | :--- |
| **Planning (`DRAFTED`)** | SOTA Reasoning Models | Claude Code, Gemini CLI, Cursor, Windsurf | Requirements analysis, functional spec creation, draft plan generation in `specs/temp/`. |
| **Building (`BUILDING`)** | Local or SOTA Models | Ollama, DeepSeek Local, Roo Code, Aider, OpenCode, Pi.dev, Kilo Code | Fast-path edits, procedural code execution, test execution, micro-refactoring. |
| **Review (`REVIEWED`)** | SOTA / Specialized Models | Claude Code, Gemini CLI, Cursor | Code quality audit, security analysis, spec promotion to `specs/`, topic decision recording. |

## Routing rules

1. When a harness change is possible mid-task, route the **status** to a harness on its tier — never run Planning on a weak local model if SOTA tier is available, and never pay SOTA tokens for mechanical Build steps.
2. **Status handoff = session handoff:** moving a task between harnesses requires a `specs/temp/handoff-payload.md` so the receiving harness resumes with full state.
3. The orchestration contract is harness-agnostic: AGENTS.md, rules, and skills load identically in every listed harness. Tiering optimizes cost/latency only; it never changes the contract.
4. Status posture (read-only planning/review, lane-scoped build edits) is enforced by `phase-protocol` regardless of tier; a tier change never relaxes posture or gate behavior.
