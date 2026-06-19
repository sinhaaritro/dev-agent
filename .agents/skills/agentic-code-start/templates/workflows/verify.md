---
description: Verify code changes work by running them. Proves through execution, not just inspection.
---

# /verify — Prove Code Works

Use this workflow to test and verify the correctness of recent code modifications.

---

## 🔴 CRITICAL RULES

1. **Verify via Execution**: Do not just read the files. Run the code or run the tests to obtain concrete evidence of success or failure.
2. **Report Actual Output**: Include command logs, test results, or compilation summaries. Do not make statements like "it should work" without executing it.
3. **Check Edge Cases**: Ensure that error handling paths are exercised in addition to happy paths.

---

## Verification Steps

When `/verify` is triggered, follow this workflow:

1.  **Identify Changes**: Detect which files, components, or behaviors were modified during this session.
2.  **Inspect Task Plan**: Read the active task planner files under `docs/plans/` (`{task-slug}-plan.md` and `{task-slug}-task.md`) to see what verification criteria were defined.
3.  **Choose Verification Tool**: Select the appropriate task runner command (e.g., `task test`, `task verify`, `npm run lint`).
4.  **Execute**: Propose and run the task command on behalf of the user.
5.  **Record & Update Checklist**: 
    *   Format the execution log into the standard Verification Report.
    *   Mark the verification checkboxes in the tracker under `docs/plans/` (`{task-slug}-task.md`) as complete (`[x]`).
6.  **Compile Walkthrough**: If all tasks are completed, generate the `walkthrough-{slug}.md` under `docs/plans/` containing the Change Registry, Test Logs, and Self-Review checks.

---

## Expected Output Format

```markdown
## Verification Report

### Changes Audited
*   [File or Component]: ✅ Pass / ❌ Fail

### Test Logs
```bash
[Paste command output here]
```
```

