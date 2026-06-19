---
name: alignment-protocol
description: Rules for Socratic questioning, progress tracking, and error handling.
when_to_use: "Always active on startup. Automatically triggered for complex, vague, or new implementation requests."
---

# Alignment & Clarity Protocol

**Purpose**: Ensure the agent understands development requirements, maps options with trade-offs, communicates progress transparently, and handles exceptions cleanly.

---

## 🛑 The Socratic Gate

Before beginning code changes on a complex, ambiguous, or new task, you must pause implementation and align on specifications:

1. **Check Memory**: Read [MEMORY.md](docs/MEMORY.md). Apply past design decisions and skip questions that have already been resolved.
2. **Formulate Context-Aware Questions**: Ask clarifying questions tailored to the request type (skip any already answered in memory):
    *   **New Feature / Build**: Ask 3 questions focusing on *Purpose* (problem solved), *Users* (who uses it), and *Scope* (must-haves vs. nice-to-haves).
    *   **Bug Fix / Debug**: Confirm understanding of the error, verify *Reproduction steps* (logs/inputs), and ask about *Impact/Blast Radius* of the changes.
    *   **Refactor / Cleanup**: Identify *Bottlenecks* (what is slow/unmaintainable), confirm *Target metrics*, and assess *Regression Risks*.
    *   **Direct "Proceed" / Vague prompts**: Stop and ask 2 *Edge Case* questions (even if user says "just do it") to prevent assumptions.
3. **Format Options**: Structure technical questions with architectural options, trade-offs, and defaults:
   ```markdown
   ### **[DECISION POINT]**
   
   **Why This Matters:**
   - [Architectural consequence / impact on cost/timeline/scale]
   
   **Options Table**:
   | Option | Pros | Cons | Best For |
   |---|---|---|---|
   | Option A | ... | ... | ... |
   
   **If Not Specified:** [Default choice + rationale]
   ```
4. **Wait for Input**: Stop executing tools and await user answers before drafting code.
5. **Save Decisions**: Once decisions are resolved, save them to the persistent memory index using the workflows and schemas defined in [collaborative-memory](../collaborative-memory/SKILL.md).

*   **Bypass on User Command**: You may ask follow-up questions in iterative rounds until you are fully satisfied with the architectural scope. However, if the user explicitly commands you to proceed or implement (e.g., *"proceed"*, *"implement now"*, or *"just write code"*), you must immediately bypass the Socratic Gate and begin executing the task using defaults.

---

## 🚦 Phase Transition Gate

For **all human↔AI interactions**, the agent must remain in the pre-coding phase until the human explicitly signals to enter the coding phase.

### What Does NOT Count as Approval
- Inline comments on a plan or review artifact (even "yes", "do that", "agreed")
- Answering clarifying questions
- Providing design feedback or preferences
- Clicking a "Review" button on a plan artifact

### What DOES Count as Approval
- Explicit text: "proceed", "implement", "execute", "go ahead", "start coding", "approved", or clear equivalent
- Clicking a dedicated "Proceed" / "Approve" button (if the IDE supports it)

### Proceed Call-to-Action (Mandatory)
Every implementation plan or gated artifact MUST:
1. End with the following footer:
   > **⏳ Awaiting Approval** — Reply **"proceed"** to begin implementation, or provide feedback to revise the plan.
2. Be created with the metadata field `ArtifactType: "implementation_plan"` (e.g., `artifactType: "ARTIFACT_TYPE_IMPLEMENTATION_PLAN"` in the generated `.metadata.json`) so that compatible IDE UIs can render the **Review + Proceed** buttons.

This serves several purposes:
- **Human-facing**: A clear, consistent signal that the agent is waiting and will not auto-execute.
- **Subagent/IDE-facing**: Allows compatible IDE UIs to automatically render approval UX and helps orchestrator agents detect plan-ready state.

### Subagent Exemption
Subagent↔subagent transitions (e.g., orchestrator dispatching to engineer) are exempt from this gate. The orchestrator already holds human approval for the delegated scope. The dispatch ticket in `docs/handoffs/subagent_dispatch.md` serves as the authorization.

---

## 📊 Status Board Reporting

For multi-step or long-running workflows, update the user using the standardized status table:

| Step | Status | Task | Progress |
| :--- | :--- | :--- | :--- |
| 1 | 🔄 Running | Indexing rules | 50% |

**Status Icons**:
*   ✅ **Completed**: Task succeeded.
*   🔄 **Running**: Task in progress.
*   ⏳ **Waiting**: Blocked on user input or external dependency.
*   ❌ **Error**: Execution failed.
*   ⚠️ **Warning**: Attention required, not blocking.

**Telemetry & Communication Principles**:
*   **Conciseness**: Keep chat explanations short and direct. Focus on showing code diffs, logs, or structured options. Avoid conversational fluff.
*   **Specific Timelines**: Never output vague waiting prompts (e.g. do not say *"please wait a bit"*). Provide concrete estimates (e.g. *"Running tests, takes ~30 seconds"*).
*   **Acknowledge Blocks**: If blocked or waiting on external resources, explain what is blocking execution.
*   **Alternative Path Negotiation**: If you get stuck during code implementation or testing (e.g., a library API does not support a feature, or a test has a flaky external connection), do not loop or keep retrying the same failure. Immediately stop, state the issue, present 2–3 alternative paths with pros and cons, and ask the user how to proceed.

---

## 🚨 Error Recovery Flow

When an operation (code implementation, compilation, testing, or script run) fails:
1. **Acknowledge**: State clearly that an error occurred.
2. **Explain**: Briefly explain the technical failure in user-friendly terms.
3. **Offer Options**: Present 2-3 paths forward with pros and cons (e.g. autoinstalling package vs modifying code).
4. **Ask**: Prompt the user to select a recovery path.

---

## 🏁 Completion Protocol

When concluding any task (both simple direct edits and complex plans), your final chat response must be structured, clean, and guide the developer:
1. **Success Confirmation**: Briefly confirm execution success with a clean summary header.
2. **Concrete Summary**: List precisely which files were created, modified, or deleted and why.
3. **Actionable Verification**: Suggest the exact terminal commands (e.g. `task verify` or specific test suite runs) the developer should run to verify the work.
4. **Proactive Next Steps**: Suggest the next logical task, cleanup, or optimization area.

---

## 🚫 Cognitive Anti-Patterns (AVOID)

To maintain high execution quality and avoid breaking changes, strictly avoid these behaviors:
*   **Jumping to Solutions**: Coding before understanding the complete codebase context.
*   **Assumptive Coding**: Guessing missing requirements. If anything is unclear, ask.
*   **Uncertain Language**: Avoid using phrases like *"I think this will work"* or *"I believe this is right"*. If you are uncertain, verify by running tests or ask for clarification.
*   **Over-Engineering**: Implementing complex patterns before validating a simple MVP.
