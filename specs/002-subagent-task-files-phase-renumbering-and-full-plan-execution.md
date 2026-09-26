---
tags: [phases, task-files, subagents, backlog, verification, unattended]
vetting: off          # 1.5-Vetting gate (plan review): on | off
signoff: off          # 4.5-Sign-off gate: on | off (on => pauses for a human when unattended)
review_revision: auto # review failure: auto (<=3 re-build cycles) | halt (straight to human)
---

# [SPEC-ID]: Subagent Task Files, Phase Renumbering, and Full-Plan Execution

Status: DRAFTED | Date: 2026-09-23

## 1. Goal & Context

Today the framework drives every task through 1-Plan → 2-Handoff → 3-Build → 4-Review
(plus the optional 1.5-Vetting and 4.5-Sign-off gates), with one long-lived spec per task
and build sessions that carry the full planning context. This
change reshapes that into a system that:

- makes each spec a **disposable task list** (nothing references it back; the whole group
  is only ever deleted on purpose, via the purge subcommand, if you choose to — there is no
  auto-purge) and adds a single permanent **backlog**;
- renames the phases to a **gapless 1-5 sequence with optional decimal consensus gates**
  (1-Plan, 1.5-Vetting, 2-Handoff, 3-Build, 4-Review, 4.5-Sign-off, 5-Done);
- splits each approved spec into **self-contained per-task files** a small (~32k-context)
  coding subagent can execute, with task-level edits going through a deterministic,
  harness-agnostic `coder` (trivial one-line fixes may be edited directly by the lead —
  §2.4);
- runs **all verification from the repo root** (so permission lists can allowlist the
  commands) and makes **completion derived, not asserted**; and
- adds **full-plan execution**: the orchestrator runs every task of an approved, handed-off
  spec through fresh-context coders (rolling, DAG-driven), runs 4-Review, and — once the
  final verification is green — commits and writes a run report. Several named specs run one
  at a time, in order (the next spec starts only after the previous one is committed).

**Non-goals (confirmed):** per-run metrics, token/cost budgets, and cross-project
session comparison are the **harness's** job — the harness sees every project and session
and can run its own comparisons. The framework only consolidates what it already records.

**Phase sequence (canonical):**

```
1-Plan
1.5-Vetting      (optional gate)
2-Handoff
3-Build
4-Review
4.5-Sign-off     (optional gate)
5-Done
```

## 2. The Change (end state, by area)

> Read top-to-bottom; each area is self-contained. §4 (affected files) and §5 (Tasks &
> Outcomes) are filled at final.

### 2.1 Phases & lifecycle

The spec header tracks a single **`Status:`** field — a **past-tense receipt of the last
completed engine action**. The five integer phases each carry a receipt; the two decimal
consensus **gates** carry none (they either pass or block). Stage names `1-Plan … 5-Done`
are the human-facing SDLC labels.

At the end of **every** stage and gate the human may stop and start a fresh session — no
information is lost, because everything the next stage needs is already written to `.md`
files on disk. The table's last column names that hand-off artifact.

| stage | `Status:` (receipt) | you say | the engine does | next stage reads |
|-------|---------------------|---------|-----------------|------------------|
| 1-Plan | `DRAFTED` | (you prompt) | drafts the plan in `specs/temp/` | the draft (`specs/temp/`) |
| 1.5-Vetting *(gate)* | — | (optional) | fresh critic vets the draft; **pass = no change** (gate log), block = `PLAN_REVISION_REQUIRED` | the draft + the gate log |
| 2-Handoff | `COMPILED` | "approve draft" | promotes to a permanent spec (`specs/`) + writes the task files + stamps `Handoff: <date>` | the permanent spec + the task files |
| 3-Build | `BUILDING` → `BUILT` \| `ESCALATED` | "approve handoff" | coder subagents execute the DAG to exhaustion; all MET → `BUILT`, any `FAILED` → consolidated `NNN-ESCALATION` + `ESCALATED` | the task files (+ the spec for context) |
| 4-Review | `REVIEWED` | (auto, core) | the orchestrator audits the diff vs spec + re-runs the final verify; green → `REVIEWED`, combined failure → re-build (≤3 cycles) then halt for human | the built diff + the spec |
| 4.5-Sign-off *(gate)* | — | "say ok" (only when `signoff: on`) | the human accepts or rejects the reviewed result; **pass = no change** (gate log), block = `REVIEW_REVISION_REQUIRED` | the review + the gate log |
| 5-Done | `COMPLETED` | (after commit, no input) | stamps `Done: <date>` + `Status: COMPLETED`; the group stays in `specs/`; a multi-spec run continues to the next named spec | the run report |

**Principle:** each status is the past-tense verb of what the *engine* did — the engine
*drafts* (you intend), *compiles* (you approve), *builds*, *reviews*, *completes*. That's
why it's `DRAFTED` not `PLANNED`, `COMPILED` not `HANDED-OFF`. Only the long pole (Build)
gets a progressive form (`BUILDING`); every other phase jumps straight to its receipt.

**Who stamps what (each receipt has exactly one producer).** Build runs as coder subagents;
when every task's derived state is MET the orchestrator stamps `BUILT`. The orchestrator
(the main agent) then runs 4-Review — diff audit + a fresh re-run of the final verify — and
on green stamps `REVIEWED`. `COMPLETED` is stamped right after the spec-end commit:
automatically when `signoff: off`, or after the human's "say ok" at 4.5 when `signoff: on`.
**Commit is terminal** — once it lands there are no further checks; the run moves to the next
named spec, or stops.

**The two optional stages differ in kind.** **1.5-Vetting** (after `DRAFTED`, on the plan) is
a consensus of *fresh* critics that did not author the draft; it feeds your "approve draft".
**4.5-Sign-off** (after `REVIEWED`) is **only your decision** on the finished result — there
is no second critic, because 4-Review already ran the automated cross-task audit + fresh final
verify; it is your "say ok". Each **passes** (no status change, written to the gate log) or
**blocks** → its own stage-specific revision receipt, `PLAN_REVISION_REQUIRED` or
`REVIEW_REVISION_REQUIRED`.

**They are per-spec header flags**, set when the draft is written — one key-value pair each,
trivial to flip: `vetting: on|off` (1.5 plan review) and `signoff: on|off` (4.5). Default is
`on` for a Lane-A surface, `off` otherwise (token cost). `signoff: on` marks the **one
spec-level human gate**: in a supervised run the human is there; in an **unattended** run the
spec **pauses at 4.5** until a human signs off — it is never auto-waived.

**The gate log** is the decision trail for the optional gates. It lives in the artifact's
`Gates:` section (a new section, §2.2): the **draft** carries the same section, so a
1.5-Vetting entry is written to `specs/temp/draft-plan.md` and carried into the promoted
spec verbatim at 2-Handoff (promotion copies the draft); a 4.5-Sign-off entry is written to
the spec directly. Every time a gate *runs* it appends one entry: which gate, when, the
critic's note, and the verdict — **pass or block** (a blocked gate records the issues that
triggered the revision receipt, so the next person sees *why* it failed, not just *that* it
failed). A gate that is *off* writes nothing. Because the log travels with the artifact it
survives a session switch and feeds the next stage — this is a new mechanism, kept
deliberately small (one append per gate) so it's easy to evaluate and drop if it doesn't
earn its place.

**1.5-Vetting (the optional gate).** Controlled by the header flag `vetting: on|off`
(default: `on` for a Lane-A surface — schema, auth, public API, new dependency — `off` for a
small low-risk Lane B; token cost). When it runs, *fresh* critic agents
(neither authored the draft) re-check the **plan-readiness checklist** — every goal captured,
no internal inconsistency, every decision made, every ambiguity resolved, plus the engine
checks (the U2 verify/expect lint and the §2.7 outcome-owner coverage). **Two paths:**
vetting pass → your "approve draft" → 2-Handoff; or skip vetting → your "approve draft" →
2-Handoff. A **block** sets `PLAN_REVISION_REQUIRED` and returns the plan to the authoring
loop, where goals, decisions, and tasks may be **removed or changed**; after the fix vetting
runs **again**. The loop is bounded by the **same 3-try exit as a task's verify** (3 blocks →
escalate/abort) **and** by human control (the human may accept-as-is or abort at any round),
and any draft edit after a *pass* **invalidates** that pass → re-vet or explicitly waive.
Vetting **never** promotes — the status changes only at 2-Handoff. The exact mechanics (two
critics in parallel vs in sequence, tie-break on disagreement, pass/block threshold) remain
an **open question** (§3).

**4.5-Sign-off (the optional human gate).** Controlled by `signoff: on|off` (default `on` for
a Lane-A surface). It is **only the human's decision** on the reviewed result (the run report
+ diff) — there is no second critic; 4-Review already did the automated audit + fresh final
verify, so reaching `REVIEWED` means everything checkable is already green. **Pass** = the
human accepts → commit → `COMPLETED`. **Block** = the human wants changes →
`REVIEW_REVISION_REQUIRED` → re-build. `signoff: off` skips the gate entirely: `REVIEWED`
commits straight to `COMPLETED`. `signoff: on` in an unattended run simply **pauses at 4.5**
until a human signs off — it is never auto-waived.

**Two planning loops (do not conflate).** (a) The **authoring loop** is internal to 1-Plan:
`DRAFTED` is a **self-loop** — keep revising `specs/temp/draft-plan.md` until the
plan-readiness checklist above is fully green; no status changes and nothing is promoted out
of it. (b) The **1.5-Vetting loop** is the optional independent re-check on top: block →
`PLAN_REVISION_REQUIRED` → fix (re-enter the authoring loop) → re-vet; pass or accept-as-is →
`COMPILED`. Vetting judges, it never authors.

**Each gate has its own revision receipt** (a block happens at a different stage and must
return to a different place — one shared `REVISION_REQUIRED` could not tell a broken *plan*
from a broken *build*):
- **1.5-Vetting block** → `PLAN_REVISION_REQUIRED` → back to `DRAFTED` (the authoring loop).
- **4.5-Sign-off block** → `REVIEW_REVISION_REQUIRED` → back to `BUILDING` (re-build).

Either revision receipt has **three exits** (a blocked gate is a decision, not a dead end):
**fix** (redo the judged phase — 1.5 re-enters the authoring loop, 4.5 re-builds),
**accept-as-is** (waive the gate, proceed to the next receipt), or **abort** (stop the spec).
The 1.5 fix loop is additionally bounded by the 3-try exit (3 blocks → escalate/abort) and by
human control.

**Transition table** (engine-enforced; what the `status` subcommand checks):

```
DRAFTED → COMPILED → BUILDING → BUILT → REVIEWED → COMPLETED

authoring loop (not a gate; no status change):
  DRAFTED   → DRAFTED                         (re-draft until goals / inconsistencies /
                                               decisions / ambiguities are all resolved)

non-linear (gate-blocked; each gate has its OWN revision receipt):
  DRAFTED   → PLAN_REVISION_REQUIRED   → DRAFTED    (1.5 block: fix, re-enter authoring loop, re-vet; 3-try cap)
  REVIEWED  → REVIEW_REVISION_REQUIRED → BUILDING   (4.5 block: re-build)
  {PLAN|REVIEW}_REVISION_REQUIRED → {next receipt}  (accept-as-is: waive the gate)
  {PLAN|REVIEW}_REVISION_REQUIRED → {abort}         (human abort → ABORTED; 3-try cap hit → ESCALATED)
```

Only `DRAFTED` (via 1.5-Vetting) can reach `PLAN_REVISION_REQUIRED`, and only `REVIEWED`
(via 4.5-Sign-off) can reach `REVIEW_REVISION_REQUIRED` — those are the only receipts a gate
sits behind. No skipping — you can't `COMPILE` before `DRAFTED`.

**No auto-purge.** Reaching `COMPLETED` deletes nothing — the group stays in `specs/`
indefinitely. Purging is a **manual, human, optional** action, run through the engine's
`purge` subcommand (never a hand `rm`): it removes the whole group — all five file types
(`NNN-SPEC-*`, `NNN-TASK-*`, `NNN-REPORT-*`, `NNN-APPROVALS-*`, `NNN-ESCALATION-*`) — and
regenerates `specs/README.md`. A companion `sync` subcommand regenerates the TOC without
deleting anything, so `specs/README.md` never dangles. `NNN`
numbers are never reused while any spec with a number ≥ that exists, so a purge
cannot create an identity collision.

**Handoff** (`COMPILED`) is the "compile" step: it takes the approved task list and writes
the per-task files. It keeps STOP semantics (the session halts; the build is a new session).

**Why:** the phase receipts + two gates give auditable save-points (stop at any gate, switch
session/model, resume); the terminal `COMPLETED` ends the "permanently in-progress" feeling;
and no-auto-purge means nothing is ever lost by accident — deletion is always a deliberate
human act.

### 2.2 Specs, task files & backlog

A spec is a **disposable task list** — `NNN-SPEC-<slug>.md` — and **nothing references it
back**: no code, doc, or README cites a spec ID or filename (durable knowledge lives only
in topic docs, whose decision IDs `<TOPIC>-D<nn>` are permanent, and the reference series
`docs/NNN-*.md`). The "no back-reference" rule applies to **durable knowledge** (topic
docs, `docs/`, `docs/README.md`) — `specs/README.md` is a **group-internal navigation TOC**,
not durable knowledge, so it is exempt: it lists only `NNN-SPEC-*` titles for browsing and
is **regenerated by a script** (no LLM tokens) at every spec update — promote, the new
`purge` subcommand, and the new `sync` subcommand — and on manual request, so deleting a
group never leaves a dangling reference. Purge and sync are engine subcommands (§2.1): the
human never `rm`s a group by hand and never edits the TOC by hand:

- `NNN-SPEC-<slug>.md` — the plan (authored at **1-Plan**): goal, outcomes, contracts, and
  the **task list** (the DAG).
- `NNN-TASK-<NN>-<slug>.md` — per-task files, **generated at 2-Handoff** (the compile
  step, not at draft time).
- `NNN-REPORT-<slug>.md` — the **run report** (§2.6); part of the group, so the purge
  subcommand removes it with the rest (§2.1).
- `NNN-APPROVALS-<slug>.json` — the **approvals** for this spec's verify commands (§2.7);
  **gitignored** (per-clone, not committed), so the purge subcommand just removes the local file.
- `NNN-ESCALATION-<slug>.md` — the **halt report** for a failed spec run (§2.6); written
  when the build is escalated (tasks `FAILED`/`BLOCKED`), committed with the group, purged
  with the rest.

The engine's `NNN` scan, title lookup, and `specs/README.md` TOC recognize only
`NNN-SPEC-*` as spec files and ignore `*TASK*`, `*REPORT*`, `*APPROVALS*`, and `*ESCALATION*`
files and `temp/`. The existing `001-tba-001-...` is renamed to `001-SPEC-<slug>.md` (one
`git mv`) **and migrated**: no old status survives — its header is brought onto the new
`Status:` receipt set and the new template as a one-time migration step (there is no
permanent grandfather clause). After migration the §7 status audit must find zero
old-status matches in `specs/`.

**Bootstrap note.** This spec replaces the very validator that gates promotion, so it is
promoted **once with the old structure check disabled** — the old `### Task N:` gate check is
turned *off*, not deleted, and is removed with the rest of the old logic once the new template
lands (goal: full replacement). The waiver is recorded in the `Gates` section, and "update
`check` to the new template" is task #1 in §5.

**Spec file structure** (the `implementation-plan-template.md`, updated by this change):
0. **Frontmatter** — `tags:` plus the per-spec flow flags set at draft time: `vetting: on|off`,
   `signoff: on|off`, `review_revision: auto|halt` (§2.1). This block is the single,
   easy-to-flip home for these decisions.
1. Goal & Context
2. **The Change** (end state, by area) — **thematic subsections, not a list of items**
   (mirrors how this plan's §2 reads)
3. Risks & Open Questions
4. Affected Files & Contracts — usable signatures/stubs (the contract source, §2.3)
5. **Tasks & Outcomes** — the task list (task → `Depends On` + verify) with the `R#`
   outcomes attached (§2.7); the source handoff compiles into task files
6. **Gates** — the gate log (§2.1): one entry per gate that ran (which gate, when, the
    critic's note, pass/block; a blocked entry records the issues that triggered
    `PLAN_REVISION_REQUIRED` / `REVIEW_REVISION_REQUIRED`). Empty until a gate runs; a gate
    that is off writes nothing. This
    is a new mechanism — deliberately small, to be re-evaluated after use.
7. Verification Commands
8. Rollback Strategy

Section 5 **merges** the old "Task DAG" and the new "Outcomes" into one table: the task list
stays in the spec (it is the source for task-file generation), and each task row carries the
outcomes it delivers, so the two are not duplicated.

**The phase boundaries are the save points.** Each boundary in §2.1 is a place you can
stop, switch session or model, and resume with no information loss: the draft (before
"approve draft"), the permanent spec + task files (before "approve handoff"), and the built
diff (before "say ok"). Only at "approve draft" does **handoff "compile"** the task list
into per-task files (+ the `Handoff:` stamp); only at "approve handoff" does code get
written. The precaution: a long build can be interrupted mid-way (a crash, a context
limit, a human stepping away) — because the spec + task files are already on disk at the
handoff boundary, a fresh session can pick up exactly where the interrupted one left off
instead of re-planning from scratch.

**Backlog.** `BACKLOG.md` at the repo root is a permanent, flat list of entries. Each entry
answers **who / what / when / where / how** — the complete set; fill all five (use `—` when
one is unknown) so both a human and an agent can understand the issue without context:

`- [ ] <when: YYYY-MM-DD> | what: <one-liner> | where: <file/area> | who: <raised-by / owner> | how: <approach / repro>`

Root placement keeps it outside `specs/temp/`, so task-cleaner can never purge it. In
review, an issue the human decides not to fix now is **parked** here as one such entry;
issues that still block route back to Plan/Build. The **human owns the lifecycle** — agents
may add or propose entries, but only the human closes/completes one. The human later promotes
entries into specs (the `how` + `where` seed the new spec's plan).

**Why:** the only durable record is the topic docs + reference series — which is exactly
what makes deleting a spec safe (a human removes the group through the purge subcommand
when they choose to).

### 2.3 Task file = targeted context for a 32k coder

The task file is the **coder's own working file**: exactly one task file is owned by exactly
one coder, and only that coder writes it. It carries the **subtask checklist** it works
through and the **evidence block** (the per-task verification record, §2.5, written by
`verify.py`). The **global** task list — which tasks are done — lives only in the spec's §5
and is written by the orchestrator (§2.6); it is **not** copied into task files. This 1:1
ownership is what keeps parallel coders from touching a shared file.

A **task** is the atomic unit of work: **~10-30 minutes of work (≈ 3-5 file edits) + 1
scoped verification**, sized so a single ~32k-context agent can hold it. The hierarchy is
**spec → task list (the DAG) → task → subtasks**. Subtasks are **optional** steps
*inside* the task file (not top-level units): because a 10-30-min task is usually several
small edits, most task files carry a short ordered `subtasks` list that breaks the
implementation into steps the 32k coder works through one at a time (the *how*, inside the
task). A trivial single-edit task omits the list. Subtasks are the coder's **own checklist**:
because it owns this file, it may tick them off (`[ ]` → `[*]` → `[x]`) as it works. They are
not a second verification gate — the task's `Verify` still decides pass/fail.

The task file is a **self-contained briefing** (copied, not referenced, so the coder never
needs the full spec):
- **Role & rules** — implement exactly this task, obey the given signatures;
- **Project overview** — 1-2 lines; the global task list is **not** copied here (it lives in
  the spec's §5, orchestrator-owned);
- **Task** — objective + requirements, with a **Progress** checklist (the steps the owning
  coder ticks off as it works; §2.3);
- **Owns** — the files this task edits (the ownership-lease surface, §2.6);
- **Reads / Context (read-only)** — context files/docs to read (never edited), decided by the
  planning agent (the coder skips the full AGENTS.md boot loop);
- **Skills to use** — the exact skills to load, named by the planning agent (no runtime matching);
- **Upstream interfaces** — signatures/type stubs only (never full dependency files);
- **Verification** — one fenced command plus an **Expect** marker (a literal substring match);
- **`doctor:`** *(optional)* — a scoped pre-check (side-constraint/drift) a task may name; it
  does **not** gate the task — `Verification` still decides pass/fail (§2.6).

**Canonical task-file schema (the shape the engine checks against).** Every generated task
file is standard Markdown with these `##` headings, in order: `Role & rules`,
`Project overview`, `Task`, `Progress` (an `###` under Task), `Owns`,
`Reads / Context (read-only)`, `Skills to use`, `Upstream interfaces`, `Verification`.
`Verification` MUST contain one fenced code block (the command) and a `**Expect:**` line.
`promote_spec.py compile` emits exactly this and **validates every file it writes** — a
missing/misordered heading, or a missing fence or `Expect`, is an error. The schema lives in
`.agents/skills/spec-builder/references/task-file-format.md`.

If more context is needed, the coder fetches it on demand via tools (stated in the task
file as a fallback, not an invitation). Explicitly excluded: planning discussions, other
tasks' internals, the whole repo. For large files the coder returns search/replace blocks,
not full rewrites.

**Contract-first:** spec section 4 (Affected Files & Contracts) is the single source of
truth for cross-task interfaces, written as usable signatures/stubs; the task generator
extracts them verbatim into dependent tasks. (Dumping full files into each task would blow
the 32k budget and couple tasks to each other's internals.)

**Worked example** (how a generated task file reads — this is how you write one; grounded
in this repo):

````markdown
# TASK 003 — add `verify.py doctor` pre-flight subcommand

## Role & rules
Implement ONLY this task. Obey the given signatures. Do not plan, do not touch files you
don't Own, do not commit.

## Project overview
Dev-agent: a meta-framework that drives coding tasks through a phase protocol.
(the global task list lives in the spec §5 — not copied here)

## Task
Add a `doctor` subcommand to verify.py that checks the unattended preconditions and fails
fast with a named list of gaps.

### Progress
- [ ] add `doctor` subparser to the argparse setup
- [ ] implement the pre-flight checks (root, imports, state files, spec status, approvals, canonical commands)
- [ ] write the "named list of gaps" failure output
- [ ] wire `Expect: PRECONDITIONS OK` on the success path

## Owns
- `.agents/skills/verification-runner/scripts/verify.py`

## Reads / Context (read-only)
- `.agents/skills/spec-builder/scripts/promote_spec.py`   (reuse find_root + spec parse)

## Skills to use
- verification-runner

## Upstream interfaces
```python
def find_root() -> Path
def load_spec(path) -> dict
```

## Verification
```bash
python .agents/skills/verification-runner/scripts/verify.py doctor
```
**Expect:** `PRECONDITIONS OK`
````

Everything the coder might need is copied in; it never opens the full spec.

### 2.4 Deterministic coder subagent (harness-agnostic)

**Task-level code edits — Lanes A and B — are executed by a `coder` subagent.** The
orchestrator/lead session dispatches the task file (or, for Lane C, an inline brief) to a
coder, runs verification via `verify.py`, and updates the task-list state. The
coder's prompt is the task file only (§2.3) — no AGENTS.md chain, no MAP, no skill
matching, no planning skills. The orchestrator is the **sole writer** of the spec (including
the §5 global task state), the approvals store, and the reports; each **task file is owned by
exactly one coder**, its only writer. Coders never write the spec or another task's file —
this is what keeps parallel coders from racing.

**Trivial fixes go direct.** The lead may edit code **directly** for trivial, single-file,
low-risk fixes (a one-line bug fix, a typo, a small config tweak) — no coder dispatch, no
task file. The bar is *trivial*: if the fix spans more than one file, touches a contract in
§2.3, or could affect a task's `Owns` set, it is dispatched to a coder instead. Direct
edits still run the relevant verify command and update the task-list state; they are
recorded in the run report as `direct` (vs `dispatched`) so the audit trail stays complete.
This keeps the interactive build feel (quick fixes are immediate) while keeping task-level
work deterministic.

The coder is defined **once, portably**: `.agents/agents/coder.md` is the behavioral
contract (role, input = the task file, fetch more context on demand, return search/replace
blocks for large files, run the listed verification, never commit, never expand scope,
never plan). Any harness loads that file as the subagent's system prompt/rules, with a
**thin per-harness adapter** (the harness's own subagent mechanism, a small/32k-class model
binding, and its permission surface). The framework mandates behavior, never model or
harness mechanics — the same portable-core + thin-shim pattern as AGENTS.md. Bootstrap
seeds `coder.md` + the adapter notes.

**Commit rule:** a run commits **at the end of each spec**, on that spec's own branch, after
4-Review is green and any required sign-off has passed. **Commit is terminal** — the spec is
stamped `COMPLETED` immediately, with **no post-commit checks**. The run contract's stop point
chooses the behavior: `commit` (default; commit + complete) or `pre-commit` (stop at
`REVIEWED` for the human to commit). The orchestrator freely edits planning artifacts
(specs/, BACKLOG.md, task-list state) and, for trivial fixes, code directly (§2.4); a harness
*may* restrict *task-level* edits to the coder via permissions (optional, per-harness)
without affecting direct trivial-fix edits.

**Two commit kinds.** (1) **Planning commit** (at 2-Handoff, on `main`): the spec + its task
files. (2) **Run commit** (at spec end, on the spec's branch): the implementation **code**
(the updated task files + run report ride with it). A run commits nothing else.

**Hard guardrail — never merge or push to the default/release branch.** A run commits only to
its own spec branch; opening a PR is fine, but **merging is human-only, always**. The framework
must never push to a protected/release branch, even when triggered headless.

**Lane C:** delegation yes, artifacts no — the lead agent (full context) composes a short
inline brief (task + target files + verify) and dispatches it directly; no committed
spec/task files.

**Why:** task-level determinism = one rule for all lanes; harness-agnostic = the framework
runs identically on whatever harness hosts it. The full planning context is exactly what a
32k coder cannot pay for — so task work goes to a coder; but a trivial one-line fix does not
need that context, so the lead handles it directly.

### 2.5 Verification from the repo root + derived completion

`verify.py` resolves the repo root (its existing `find_root()`) and runs subprocess with
`cwd=<root>`; the approval fingerprint is `command | expect | cwd` — **`executor` is dropped**,
so a human's pre-approval matches the coder's run. The **canonical
AGENTS.md commands** (Build/Test/Lint) are written repo-root-relative — these are the
**whole-repo** commands (and fill the current `<command>` placeholders). **Per-task**
verify commands live in the task list / task files (§2.3) and may be narrower (a small
task may change behavior the full suite flags, so per-task verify may be partial by
design; the canonical commands are always re-run in full at the end). This also lets a
harness permission list allowlist the literal command strings.

**Completion is derived, not asserted** (the "unlazy" model). The task-list checkboxes are
a *cache for humans*, not the source of truth. Each task file carries its own **evidence
block** (the per-task evidence ledger, written by `verify.py` when the task's verify
passes): the command, the pass timestamp, and a **content hash** (`sha256`) of every owned
file at that moment. `verify.py
status` re-derives each task's state from that block: **MET** (verify passed and every owned
file's current hash still matches), **NOT MET** (no passing evidence, or the command now
fails), **STALE** (an owned file's hash changed since the evidence was recorded, so re-verify
is required), **NO-EVIDENCE** (marked done but no evidence block exists). Keeping the evidence inside the task file means
there is no separate ledger to lose or sync — the task file *is* the record. The engine and
any subagent read derived status. The per-task retry limit is **3 total attempts** (the
first try + 2 retries) to pass a task's verify — a task that uses all 3 without a green
verify is **`FAILED`**, and every task whose `Depends On` includes a non-`MET` task is
**`BLOCKED`** (it never ran). Failed + blocked tasks are what the consolidated escalation
(§2.6) records; independent tasks keep running to exhaustion.

**Two verification levels.** (1) the **per-task verify** above (3 attempts), and (2)
**4-Review** (§2.6) — the cross-task level: a fresh re-run of every task's verify plus the
canonical commands. Subtasks carry no verify (generation-time guidance only); only 4-Review
sees the tasks combined, so integration failures surface there.

**Why:** running from the root makes permission allowlisting possible and fixes the current
CWD-dependence; derived completion closes the "checkbox says done but the code drifted"
gap.

### 2.6 Full-plan execution (unattended) & dispatch

**Trigger = an explicit run contract (the only way a run starts).** The framework never
self-starts. The trigger is free-form text (`implement / execute / complete <spec>`) that the
lead agent resolves into a **run contract**:

- **targets** — which specs (`this`, a list, or `all`), each already `COMPILED`.
- **mode** — `supervised` (ask) | `unattended` (don't ask). Default comes from the auto-router
  **session type** (Option A): Interactive → `supervised`, Non-Interactive → `unattended`, no
  signal → `unattended` (fail toward caution). The trigger may override either way ("run it
  overnight" / "wait for me at 4.5").
- **stop point** — `commit` (default; commit → `COMPLETED`) | `pre-commit` (run to `REVIEWED`,
  stop before commit so the human inspects/commits).

**Start condition is opt-in (the cost gate).** In CI, a ticket existing is only an *event* —
the wrapper maps an event to a trigger **only when it matches an allowlist** (a label, a
`/agent` command, an approval, a schedule). Nothing runs, and nothing costs money, unless a
trigger explicitly fires. When several specs are targeted, **they run one at a time, in order**
(see below).

**Unattended behavior.** The run does not ask for approvals or gate answers; it runs to the
stop point. It **pauses** only at a spec-level human point — `signoff: on` (at 4.5) or a
`review_revision: halt` review failure — and then waits for a human.

**The doctor** (`verify.py doctor`, a single stdlib script) runs at two levels:
- **Per spec** — before the first dispatch (pre-flight), `verify.py doctor` checks in order:
  1. repo root resolved; 2. engine scripts importable; 3. state files parseable; 4. the spec is
  `Status: COMPILED` and `Handoff:`-stamped; 5. a task file exists for every task in §5;
  6. `Depends On` forms a valid DAG (no cycles, no missing tasks); 7. every task's verify
  command is pre-approved (fingerprint = `command | expect | cwd`, no `executor`); 8. the
  canonical AGENTS.md Build/Test/Lint commands resolve; 9. a branch/worktree can be created off
  `main`. Output: `PRECONDITIONS OK` on success, else a **named list of gaps** + non-zero exit.
- **Per task** — *optional*, only when the task file's verification section names it: a
  scoped check that looks for issues introduced by *this task* (e.g. a side-constraint
  change that can't be verified within one task, or a quick scoped/full test run to catch
  drift early). It does not gate the task's pass/fail — the task's own verify command
  does. The per-spec doctor always runs; the per-task doctor is opt-in per task.
- **`Status: COMPILED`** (handoff cleared) — a run never executes a spec still at
  `DRAFTED`; the gate model makes `COMPILED` unreachable without the "approve draft" gate.
- **Handoff stamp** present (task files exist).
- **All verify commands pre-approved** — approving the spec records pre-approval for every
  command in its task list (§2.7), so the run never halts on a command approval.

These preconditions are enforced for **unattended** runs (no human present to answer an
approval prompt). An **interactive/supervised** build with a human in the loop still requires
`COMPILED` + the handoff stamp, but a command that isn't pre-approved simply asks the human at
that moment instead of halting the run. A `signoff: on` spec is **not** refused unattended — it
runs and **pauses at 4.5** until a human signs off.

**Dispatch is rolling, not wave-based.** The orchestrator reads the current spec's task
list, finds every **unblocked** task (all its `Depends On` green), and dispatches coder
subagents for as many as the harness can run concurrently (the harness's max-parallel
subagent setting — a per-harness number the orchestrator reads from its config; if
unknown, it defaults to 1 and runs tasks one at a time). Newly unblocked tasks start
immediately, no waiting for unrelated work. Planning is hierarchical (the planning agent
may spawn read-only research subagents); nesting is allowed (a task's coder may spawn
sub-coders for its subtasks, depth-limited by the harness).

**Specs live on `main`; each run gets its own branch.** Planning artifacts (spec, task files,
reports) are authored on `main`. When a run starts, the orchestrator creates one **branch per
spec off `main` (+ worktree)** and does all coding there — it **never works directly on
`main`**. Specs run sequentially, each on its own branch, so nothing crosses between them:
spec N runs through 4-Review on its branch, and only once its final verification is green does
it commit **on that branch** and spec N+1 start. Each spec has its own task list, its own 3-attempt per-task limit, its own
consolidated `NNN-ESCALATION`, its own `NNN-REPORT`, and its own commit. An escalation stops
**that spec's branch** (writing its `NNN-ESCALATION`) and the batch **continues** to the next
spec — a bad spec cannot cascade, and an unattended batch ends with a chat summary.

*Example — single spec, task list `A → B, A → C, D` (D independent), capacity = 2:*

```
rolling (what we do):
  t0  dispatch A, D            # both unblocked, capacity = 2
  t1  A done -> B unblocks -> dispatch B      # C still blocked (needs A), D running
  t2  D done -> dispatch C                # C unblocked (A done), capacity free
  t3  B, C done
not wave/sequential:  A -> B -> C -> D          # one at a time
```

**Parallelism is gated by an ownership lease.** A file is owned by exactly one task — the
owning task owns **every** change to that file. Two tasks dispatch concurrently only if
their **Owns** sets are disjoint (a mechanical set-intersection check); if they overlap on
even one file, both tasks are **not dispatched in the same run** — they are serialized by
the `Depends On` edge. This is what stops two tasks touching the same file from wiping
each other.

**The build runs the DAG to exhaustion (no "consecutive failures" breaker).** When a task
uses all 3 attempts it is marked `FAILED` and its dependents become `BLOCKED`; every
**independent** task still runs to its own completion. There is no "3 consecutive failed
tasks" rule. Only when **no unblocked task remains** is the outcome decided: all `MET` →
`BUILT`, otherwise the orchestrator writes **one consolidated `NNN-ESCALATION-<slug>.md`**
covering *every* failed task (its 3 attempts, last output) and every `BLOCKED` task, and
stops that spec. Nothing else halts the run — model + harness + framework run the whole plan
without asking for extra permissions.

**Consequences.** After the last task of a spec the orchestrator stamps `BUILT`, then runs
**4-Review** (audits the diff vs spec, §2.1) and re-runs the final verification itself (a fresh
re-run of every task's **verify command** — not the decimal gates — plus the canonical
AGENTS.md commands; old evidence is not re-execution).
- **Review failure** (all tasks MET but the **combined** result fails — final verify red or an
  unmet `R#` observation): this means the **plan** is wrong, so it always ends at a human. The
  orchestrator writes the consolidated `NNN-ESCALATION` (`kind: review`) and **halts for human
  intervention regardless of mode** (`ESCALATED`); the human decides whether to re-plan or
  re-build. (`review_revision: auto` may attempt up to 3 re-builds first; `halt` goes straight
  to the human. Picking *which* tasks is a human call — the report records the failure.)
- **Sign-off** (`signoff: on`): pause at `REVIEWED` until the human accepts; `signoff: off`
  skips it.
- **Commit is terminal.** Per the stop point, the run commits on the spec's branch → stamps
  `COMPLETED` immediately → moves to the next spec; **no post-commit checks**. `pre-commit`
  stops at `REVIEWED` for the human to commit.
- **Commit failure** (e.g. a pre-commit hook) leaves the spec `REVIEWED`; the run report
  records it and the human resolves it.

The run commits **only on its own branch** — never merged or pushed to the default/release
branch (hard guardrail, §2.4).

**On halt** the spec's tree stays dirty on its branch (see Escalation, above) — no
auto-revert — and the orchestrator does **not** commit that spec: it writes the run report
(in its halted form) and the `NNN-ESCALATION`, then **continues to the next spec**. A halted
spec never cascades into another, and the batch ends with a chat summary (no combined file).

**The run report** (`NNN-REPORT-<slug>.md`, one per spec, §2.2) is the proof of completion:
the resolved run contract (session type, mode, stop point), the spec's branch, per-task verify
result (command + pass/fail + evidence path), how each task was executed (`dispatched` vs
`direct`, §2.4), the derived task-list state (all MET?), any escalation events, the 4-Review
result + outcome reconciliation (§2.7), the 4.5 human sign-off verdict (§2.1, when `signoff:
on`), and the commit outcome. Generated at spec end on success and on halt (alongside that
spec's `NNN-ESCALATION`); also regenerable on demand (`verify.py report`). Reports are
**per spec only** — there is no combined batch file. At the end of a multi-spec run the
orchestrator posts a **chat summary** (per spec: committed / paused-for-signoff / escalated).

**Escalation** (`NNN-ESCALATION-<slug>.md`, in the spec group under `specs/`) is the
**consolidated** halt report for a failed spec run, with a `kind: build | review` header:
*build* lists every `FAILED` task (its 3 attempts + last output) and every `BLOCKED` task;
*review* records the combined/integration failure and the failing check (naming any tasks it
points to, if identifiable). Both keep the
dirty edits left in the tree (the run **does not** revert them — they stay for the human to
inspect when they return) and park the spec as `Status: ESCALATED`, where a human decides the
next move. (`ABORTED` is reserved for a human deliberately stopping a spec at a gate.) It is NNN-named so several failing specs don't collide, and it is part of the spec
group (committed, survives a session switch, purged with the group by the purge subcommand).

**Why:** removes the friction of manually looping tasks; the no-halt contract is only
possible because pre-approval + no-ask commands are enforced up front by the doctor.

### 2.7 Outcomes & approvals

**Outcomes.** Section 5 of the spec is **Tasks & Outcomes** (see §2.2): the task list
(task → `Depends On` + verify) with the outcomes attached. Each `R#` = an *outcome* (what
the user actually gets), its **owner task** (which task delivers it), and its **observation**
(how to verify it was achieved). The task list stays in the spec because handoff compiles it
into the per-task files — only the detail moves out. Two checks: (a) at **draft/plan**, the
engine verifies every outcome has an owner task — a plan that promises an outcome nobody
delivers fails `check` (prevents "we built the tasks but not the thing the user asked for");
(b) at **review (reconciliation)**, every `R#` must have a recorded observation (proof the
outcome was achieved, not just that its owner task passed) — a task can pass its verify yet
fail to deliver the outcome. The observation is written into the **run report**
(`NNN-REPORT-<slug>.md`), one line per `R#`; a **missing observation fails 4-Review**, routing
to the review-failure path (§2.6).

**Approvals.** Approvals are **per spec**: each spec gets its own `NNN-APPROVALS-<slug>.json`
(verify-command pre-approvals). Approving the spec writes pre-approval for every command in
its task list into that file (at promote time), which lets `verify.py` run unattended without
its own exit-4 halt. The file is **gitignored** — a per-clone, per-machine record, so a fresh
clone re-approves (the safer default). **Real execution permission is the harness's job**: its
permission surface allowlists the repo-root command strings; the framework's approvals file is
the record, not the gate.

## 3. Risks & Open Questions

**Risks (consequences of settled decisions awaiting acceptance):**
- Approvals are pre-recorded at compile time, so the fingerprint must **not** include a
  per-session `executor` (M1) — otherwise an unattended run halts on the first command.
- Derived completion is **hash-based** (M9): a build that reformats a file without semantic
  change still marks the task `STALE` (safe — it just re-verifies).
- The run commits automatically at spec end unless `stop point: pre-commit`; a spec branch is
  private until a human merges it.
- If the harness reports no max-parallel, the run defaults to 1 (sequential tasks).

**Open Questions:**
- 1.5-Vetting mechanics (parallel vs sequence, tie-break, threshold) — **deferred** (not
  blocking; `vetting` defaults off).
- The cross-case flow is mapped in `specs/temp/flow.md`.

> The current-state gaps this change fixes and the new tests it adds are build work, not
> risks or open questions; they are captured in §4 (Affected Files & Contracts) and §5
> (Tasks & Outcomes) when those sections are filled at final.

## 4. Affected Files & Contracts

> Contracts are the CLI/function shapes the tasks must honour. `.agents/**` edits must stay
> **small** (context budget); full explanation goes in `docs/`.

### Engine scripts
- **[MODIFY]** `.agents/skills/spec-builder/scripts/promote_spec.py`
  - `check <draft> --lane <A|B>` → validates the **new** template (sections 0–8): §5 task
    shape, `R#` owner coverage, tag lint; prints `structure: ok` on success. The old
    `### Task N:` gate check is **retired**.
  - `promote <draft> --lane <A|B> --status <COMPILED>` → writes `NNN-SPEC-<slug>.md`.
  - `compile <spec>` → **new**: writes `NNN-TASK-<NN>-<slug>.md` per §5 task in the
    **canonical task-file shape** (`references/task-file-format.md`) and validates each file
    before writing — `validate_task_file(text: str) -> list[str]`.
  - `status <spec>` / `status <spec> <receipt>` → enforces the transition table (§2.1).
  - `purge <spec>` / `sync` / `accept <spec>` → **new**; `toc`, `topic`, `tag-*` retained.
- **[MODIFY]** `.agents/skills/verification-runner/scripts/verify.py`
  - `doctor --spec <n>` → **new**: 9 preconditions (§2.6); prints `PRECONDITIONS OK`.
  - `run --command <c> --expect <m> --task <id> --lane <l>` → `cwd=<root>`; fingerprint
    `command | expect | cwd` (**no `executor`**); writes **hash** evidence into the task file.
  - `status --task <id>` → **new** semantics: `MET | NOT MET | STALE | NO-EVIDENCE` from hashes.
  - `report --spec <n>` → **new**: regenerates `NNN-REPORT-<slug>.md`.
- **[MODIFY]** `.agents/skills/task-cleaner/scripts/clean.py` → new `specs/temp/` scope (§2.6/M6).
- **[MODIFY]** `.agents/skills/map-generator/scripts/generate_map.py` → only if the docs index changes.

### Agent contracts
- **[NEW]** `.agents/agents/coder.md` — portable coder contract (input = task file; never
  commit/plan/expand scope).
- **[NEW]** `.agents/agents/critic.md` — *optional, deferred with vetting*.

### Task-file schema
- **[NEW]** `.agents/skills/spec-builder/references/task-file-format.md` — the canonical
  task-file skeleton + required-heading list (the shape `compile` validates against).

### Rules & skills (text; keep lean, defer detail to `docs/`)
- **[MODIFY]** `.agents/rules/system.md` — boot chain, phases, run contract, guardrails
  (never merge/push to `main`).
- **[MODIFY]** `.agents/skills/phase-protocol/SKILL.md` + `references/{plan,handoff,build,review}.md`.
- **[MODIFY]** `.agents/skills/auto-router/SKILL.md` + `references/lane-matrix.md` — session → mode.
- **[MODIFY]** `.agents/skills/spec-builder/SKILL.md` + `references/*`.
- **[MODIFY]** `.agents/skills/verification-runner/SKILL.md`.
- **[MODIFY]** `.agents/skills/task-cleaner/SKILL.md`.
- **[MODIFY]** `.agents/skills/bootstrap/SKILL.md` + `reference/*` (seed the new framework).
- **[GENERATED]** `.agents/MAP.md`.

### Root & specs
- **[MODIFY]** `AGENTS.md` — canonical commands filled; phase/status references updated.
- **[NEW]** `BACKLOG.md`.
- **[MODIFY]** `specs/README.md`, `docs/README.md` — engine-generated TOC.
- **[RENAME+MIGRATE]** `specs/001-tba-001-*.md` → `specs/001-SPEC-<slug>.md` (new status/template).

### Docs (the explanation lives here)
- **[NEW]** `docs/lifecycle.md`, `docs/task-files.md`, `docs/verification.md`,
  `docs/run-contract.md`, `docs/branching.md`.
- **[NEW]** `docs/flow.md` — the mermaid charts moved from `specs/002-flow-design.md`.
- **[MODIFY]** the existing reference series — `docs/001-framework-overview.md`,
  `docs/002-skill-discovery-and-indexing.md`, `docs/003-triage-lane-taxonomy-and-escalation.md`,
  `docs/004-phases-gates-and-autonomy.md`, `docs/005-docs-architecture-and-spec-lifecycle.md`,
  `docs/006-verification-and-circuit-breakers.md`,
  `docs/007-parallel-execution-and-worktrees.md`, `docs/decision-records.md` — brought onto the
  new phases / single `Status:` / gates / run contract / branch model.
- **[GENERATED]** `docs/README.md`, `docs/_topics.md`.

### Tests
- **[NEW]** `tests/test_promote_spec.py`, `tests/test_verify.py`, `tests/test_clean.py`,
  `tests/test_drift_phases.py`.

## 5. Tasks & Outcomes

> This list is the **source** handoff compiles into per-task files. `Depends On` reads the
> DAG. **Bootstrap caveat:** this spec is promoted once with the old check waived (§2.2); its
> own task files are compiled after T1/T2 land (or generated by hand if needed).

**Outcomes:**

| ID | Outcome (what the user gets) |
|----|------------------------------|
| R1 | Phases/status renamed end-to-end: `1-Plan … 5-Done`, a single `Status:` field (no `Phase:`), consistent across `.agents`, root docs, and the migrated spec |
| R2 | An approved spec compiles into self-contained per-task files at 2-Handoff |
| R3 | Task-level edits run through a portable `coder` subagent contract; trivial direct fixes are recorded |
| R4 | Verification runs from the repo root; per-task evidence is content-hash based; `doctor`/`report`/`status` exist; completion is derived |
| R5 | Full-plan execution: explicit trigger/run-contract, rolling DAG dispatch, run-to-exhaustion + consolidated escalation, branch-per-spec, commit-terminal, never-merge-main guardrail |
| R6 | `.agents/{rules,skills}` stay context-lean; deep explanation lives in `docs/` |
| R7 | `docs/` documents the new system, including the flow diagrams |
| R8 | `specs/` group model + `purge`/`sync`/`accept`, `specs/README` TOC, `BACKLOG.md`, migrated `001` |
| R9 | Tests cover the engines; canonical build/test/lint green |

---

### Task 1: new-template `check` + canonical `Status:` set
- Target Files: [MODIFY] `.agents/skills/spec-builder/scripts/promote_spec.py`, [NEW] `tests/test_promote_spec.py`
- Depends On: None
- Outcomes: R1, R8
- Verify: `python .agents/skills/spec-builder/scripts/promote_spec.py check specs/temp/draft-plan.md --lane A`
- Expect: "structure: ok"

### Task 2: `compile` + `purge`/`sync`/`accept` subcommands
- Target Files: [MODIFY] `.agents/skills/spec-builder/scripts/promote_spec.py`, [MODIFY] `tests/test_promote_spec.py`
- Depends On: Task 1
- Outcomes: R2, R8
- Verify: `python -m unittest tests.test_promote_spec -v`
- Expect: "OK"

### Task 3: `verify.py` — root cwd, fingerprint, hash evidence, `doctor`/`status`/`report`
- Target Files: [MODIFY] `.agents/skills/verification-runner/scripts/verify.py`, [NEW] `tests/test_verify.py`
- Depends On: None
- Outcomes: R4
- Verify: `python -m unittest tests.test_verify -v`
- Expect: "OK"

### Task 4: portable `coder` contract + bootstrap seeding
- Target Files: [NEW] `.agents/agents/coder.md`, [MODIFY] `.agents/skills/bootstrap/SKILL.md`
- Depends On: None
- Outcomes: R3
- Verify: `bash -c 'grep -q "never commit" .agents/agents/coder.md && echo CODER-CONTRACT-OK'`
- Expect: "CODER-CONTRACT-OK"

### Task 5: phase renumber + single `Status:` across `.agents`, `AGENTS.md`, `MAP.md`
- Target Files: [MODIFY] `.agents/rules/system.md`, `phase-protocol/SKILL.md`+`references/*`, `auto-router/*`, `spec-builder/SKILL.md`, `verification-runner/SKILL.md`, `task-cleaner/SKILL.md`, `AGENTS.md`; [GENERATED] `.agents/MAP.md`
- Depends On: None
- Outcomes: R1
- Verify: `bash -c 'test -z "$(grep -rn "Phase:" .agents AGENTS.md)" && echo PHASE-AUDIT-OK'`
- Expect: "PHASE-AUDIT-OK"

### Task 6: run contract in `auto-router` + `system.md`
- Target Files: [MODIFY] `.agents/skills/auto-router/SKILL.md`, `auto-router/references/lane-matrix.md`, `.agents/rules/system.md`
- Depends On: Task 5
- Outcomes: R5
- Verify: `bash -c 'grep -q "run contract" .agents/skills/auto-router/references/lane-matrix.md && grep -q "unattended" .agents/skills/auto-router/references/lane-matrix.md && echo RUN-CONTRACT-OK'`
- Expect: "RUN-CONTRACT-OK"

### Task 7: branch-per-spec, commit-terminal, never-merge guardrail
- Target Files: [MODIFY] `.agents/rules/system.md`, `.agents/skills/phase-protocol/references/build.md`, `review.md`
- Depends On: Task 5
- Outcomes: R5
- Verify: `bash -c 'grep -qi "never merge" .agents/rules/system.md && grep -qi "commit is terminal" .agents/skills/phase-protocol/references/build.md && echo BRANCH-GUARD-OK'`
- Expect: "BRANCH-GUARD-OK"

### Task 8: spec-builder spec — new template + task-file format
- Target Files: [MODIFY] `.agents/skills/spec-builder/references/implementation-plan-template.md`, `references/topic-template.md`, `references/todo-checklist-format.md`, `SKILL.md`
- Depends On: Task 1
- Outcomes: R1, R2
- Verify: `bash -c 'grep -q "Tasks & Outcomes" .agents/skills/spec-builder/references/implementation-plan-template.md && grep -q "Gates" .agents/skills/spec-builder/references/implementation-plan-template.md && echo TEMPLATE-OK'`
- Expect: "TEMPLATE-OK"

### Task 9: `docs/` topic set + move flow charts from `specs/temp/flow.md`
- Target Files: [NEW] `docs/lifecycle.md`, `docs/task-files.md`, `docs/verification.md`, `docs/run-contract.md`, `docs/branching.md`, `docs/flow.md`
- Depends On: None
- Outcomes: R6, R7
- Verify: `bash -c 'test -f docs/flow.md && grep -Eq "flowchart|stateDiagram" docs/flow.md && echo DOCS-FLOW-OK'`
- Expect: "DOCS-FLOW-OK"

### Task 10: slim `.agents` skills (detail moved to `docs/`)
- Target Files: [MODIFY] `.agents/skills/*/SKILL.md`, `.agents/rules/system.md`
- Depends On: Task 9
- Outcomes: R6
- Verify: `bash -c 'test "$(wc -l < .agents/skills/phase-protocol/SKILL.md)" -lt 120 && echo LEAN-OK'`
- Expect: "LEAN-OK"

### Task 11: bootstrap reference seeds match the new framework
- Target Files: [MODIFY] `.agents/skills/bootstrap/reference/AGENTS.md`, `reference/rules/system.md`, `reference/.cursorrules`, `reference/.windsurfrules`, `reference/.gitignore`
- Depends On: Task 5, Task 6, Task 7
- Outcomes: R1, R5
- Verify: `bash -c 'test -z "$(grep -rn "Phase:" .agents/skills/bootstrap/reference)" && grep -qi "never merge" .agents/skills/bootstrap/reference/rules/system.md && echo BOOTSTRAP-OK'`
- Expect: "BOOTSTRAP-OK"

### Task 12: `task-cleaner` scope / `specs/temp` fate
- Target Files: [MODIFY] `.agents/skills/task-cleaner/scripts/clean.py`, `.agents/skills/task-cleaner/SKILL.md`, [NEW] `tests/test_clean.py`
- Depends On: Task 3
- Outcomes: R8
- Verify: `python -m unittest tests.test_clean -v`
- Expect: "OK"

### Task 13: migrate `001`, add `BACKLOG.md`, regenerate TOCs
- Target Files: [RENAME] `specs/001-tba-001-*.md` → `specs/001-SPEC-*.md`, [NEW] `BACKLOG.md`, [MODIFY] `specs/README.md`, `docs/README.md`
- Depends On: Task 1, Task 2
- Outcomes: R8
- Verify: `bash -c 'ls specs/001-SPEC-*.md >/dev/null 2>&1 && test -f BACKLOG.md && test -z "$(grep -rn "| Phase:\|Status: DRAFT " specs/ | grep -v README)" && echo MIGRATE-OK'`
- Expect: "MIGRATE-OK"

### Task 14: drift test + full canonical verification
- Target Files: [NEW] `tests/test_drift_phases.py`, [MODIFY] `AGENTS.md`
- Depends On: Task 5, Task 6, Task 7, Task 11, Task 13, Task 15
- Outcomes: R9
- Verify: `python .agents/skills/verification-runner/scripts/verify.py run --command "python -m unittest discover -s tests -v" --expect "OK" --task T14 --lane A`
- Expect: "OK"

### Task 15: update the docs reference series (001–007 + decision-records)
- Target Files: [MODIFY] `docs/001-framework-overview.md`, `docs/002-skill-discovery-and-indexing.md`, `docs/003-triage-lane-taxonomy-and-escalation.md`, `docs/004-phases-gates-and-autonomy.md`, `docs/005-docs-architecture-and-spec-lifecycle.md`, `docs/006-verification-and-circuit-breakers.md`, `docs/007-parallel-execution-and-worktrees.md`, `docs/decision-records.md`
- Depends On: Task 5, Task 6, Task 7
- Outcomes: R7
- Verify: `bash -c 'grep -q "1-Plan" docs/004-phases-gates-and-autonomy.md && test -z "$(grep -rln "1\\.5-Handoff\\|Phase: 2-Build\\|Phase: 3-Review" docs/)" && echo REFDOCS-OK'`
- Expect: "REFDOCS-OK"

## 6. Gates

_(empty until a gate runs — §2.1. This spec sets `vetting: off` because vetting mechanics are
deferred, §3.)_

## 7. Verification Commands

- Build Command: `python -m compileall -q .agents tests` (repo-root-relative; also fills
  the AGENTS.md placeholder)
- Test Command: `python -m unittest discover -s tests -v`
- Lint Command: `python -m ruff check .agents tests`
- Audit (phase set): `grep -rn "1\.5-Handoff\|1\.5-Consensus\|4\.5-Consensus\|Phase:" .agents docs README.md AGENTS.md` → expect no matches (the `Phase:` field is dropped in favour of a single `Status:`); canonical stage set is `1-Plan`, `1.5-Vetting`, `2-Handoff`, `3-Build`, `4-Review`, `4.5-Sign-off`, `5-Done` (enforced by the drift test, §5)
- Audit (status set): `grep -rn "Status: DRAFT \|Status: HANDOFF\|Status: APPROVED\|Status: DONE\|Status: PROVISIONAL" specs` → expect no matches; canonical `Status:` receipt set is `DRAFTED`, `COMPILED`, `BUILDING`, `BUILT`, `REVIEWED`, `COMPLETED`, `PLAN_REVISION_REQUIRED`, `REVIEW_REVISION_REQUIRED`, `ESCALATED`, `ABORTED` (§2.1)


## 8. Rollback Strategy

The run **never reverts** — a mid-build failure leaves the working tree dirty for a human to
inspect. Instead of a revert, the run writes `NNN-ESCALATION-<slug>.md` (the consolidated
halt report: every `FAILED` task with its 3 attempts and last output, every `BLOCKED` task,
and the dirty edits left in the tree) and stops that spec's branch. The run commits only at the
end of a spec (§2.6), so a **mid-build** failure has no commit yet; a **completed-but-wrong**
task is re-dispatched to a coder (bounded to its own `Owns` set). Once a spec's commit lands on
its branch, any task reverts as one `git revert`; because each spec has its own branch +
commit, reverting one spec never touches another.
