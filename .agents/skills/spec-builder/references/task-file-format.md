# Task File Format (canonical)

The task file is the **coder's own working file**: exactly one task file is owned by
exactly one coder, and only that coder writes it. It carries the **Progress** checklist the
coder works through and the **evidence block** (the per-task verification record, written by
`verify.py`). The **global** task list — which tasks are done — lives only in the spec's
§5 and is written by the orchestrator; it is **not** copied into task files.

## Generation

`promote_spec.py compile <spec>` (the handoff "compile" step) reads the spec's §5
**Tasks & Outcomes** and emits **one self-contained task file per task**, named
`NNN-TASK-<NN>-<slug>.md` (parent `NNN` prefix + two-digit task number + a short task slug).
It validates **every file it writes** with `validate_task_file(text)` — a missing or
misordered heading, or a missing `Verification` fence / `Expect`, is an error and the file
is not written. It also writes pre-approvals for every task's verify command into
`NNN-APPROVALS-<slug>.json` (gitignored) and stamps `Handoff: <date>` on the spec.

A task file is a **self-contained briefing** (copied, not referenced, so the coder never
needs the full spec). Everything the coder might need is copied in.

## Required headings (in order)

Standard Markdown with these `##` headings, **in this exact order**:

1. `## Role & rules`
2. `## Project overview`
3. `## Task`
   - `### Progress` — an `###` under Task (the coder's own checklist, `- [ ]` items)
4. `## Owns`
5. `## Reads / Context (read-only)`
6. `## Skills to use`
7. `## Upstream interfaces`
8. `## Verification`
   - **MUST** contain one fenced code block (the command) and a `**Expect:**` line

An optional `doctor:` field (a scoped pre-check a task may name) does **not** gate the
task — `Verification` still decides pass/fail.

## Canonical skeleton

The title is `# TASK <NNN>-<NN> — <title>`. Every generated file matches this shape:

````markdown
# TASK 003-01 — add `verify.py doctor` pre-flight subcommand

## Role & rules
Implement ONLY this task. Obey the given signatures. Do not plan, do not touch files you
don't Own, do not commit.

## Project overview
Dev-agent: a meta-framework that drives coding tasks through a status protocol.
(the global task list lives in the spec §5 — not copied here)

## Task
Add a `doctor` subcommand to verify.py that checks the unattended preconditions and fails
fast with a named list of gaps.

### Progress
- [ ] add `doctor` subparser to the argparse setup
- [ ] implement the pre-flight checks
- [ ] write the "named list of gaps" failure output

## Owns
- `.agents/skills/verification-runner/scripts/verify.py`

## Reads / Context (read-only)
- `.agents/skills/spec-builder/scripts/promote_spec.py`   (reuse find_root + spec parse)

## Skills to use
- verification-runner

## Upstream interfaces
```python
def find_root() -> Path
```

## Verification
```bash
python .agents/skills/verification-runner/scripts/verify.py doctor
```
**Expect:** `PRECONDITIONS OK`
````

## Validation rules (`validate_task_file`)

`validate_task_file(text: str) -> list[str]` returns a list of violation strings (empty
when the file is well-formed). It checks, in order:

1. **Title** — a `# TASK <NNN>-<NN> — ` first heading is present.
2. **Headings in order** — the eight `##` headings above appear, each exactly once, in
   this order. A missing heading, a duplicate, or a misordered heading is a violation.
3. **Progress** — `### Progress` appears under `## Task`.
4. **Verification fence** — the `## Verification` section contains at least one fenced
   code block (the command).
5. **Verification Expect** — the `## Verification` section contains a `**Expect:**` line.

The engine never writes a task file that fails this check; `compile` refuses to write and
reports the violations.

## Ownership & evidence

- A file is owned by exactly one task — the owning task owns **every** change to it.
- `verify.py` writes the per-task **evidence block** (command, pass timestamp, content
  hash of every owned file) into the task file when the task's verify passes.
- The task's `Verify` is the single pass/fail oracle; subtasks are the coder's checklist,
  not a second gate.
