# Repository Audit — Open Issues

- **Date:** 2026-10-19
- **Scope:** full repo — shipped skills (`skills/`), dogfood mirror (`.agents/`), engines, docs, specs, tests, maintainer tools
- **Method:** manual read-through plus the canonical commands (see [Checks run](#checks-run))
- **Status:** C1–C4, H2 and H7 have since been fixed (see those entries); all other findings are unchanged.

> These are captured here at the repo root because the request was to preserve the audit in one place. Entries that are promoted into work should move to `BACKLOG.md` (or a spec) using its five-field format.

## Severity summary

| ID | Severity | Issue |
| :-- | :-- | :-- |
| C1 | Critical | ✅ **Fixed 2026-10-19** — compile pre-approvals now use the same sha256 key as `verify.py`, and `run` honors `specs/NNN-APPROVALS-*.json` |
| C2 | Critical | ✅ **Fixed 2026-10-19** — each compiled task file's `## Owns` now comes from its own section-5 `Target Files`; `check`/`compile` reject missing or overlapping targets |
| C3 | Critical | ✅ **Fixed 2026-10-19** — the circuit-breaker writes the durable `NNN-ESCALATION-<slug>.md` and stamps `ESCALATED` (scratchpad only as the no-spec fallback) |
| C4 | Critical | ✅ **Fixed 2026-10-19** — `APPROVED`/`PROVISIONAL` are canonical; build/report/gate own their transitions; `check`/`doctor` validate and a drift test guards `specs/` |
| H1 | High | `drafted.md` Lane-A section map is stale and fails `check` |
| H2 | High | ✅ **Fixed 2026-10-19** — the documented convention is `NNN-SPEC-<slug>.md` everywhere; the fresh README scaffold and the dead tag-index block are corrected |
| H3 | High | Documented CLI invocations (`doctor/report/status --spec|--task <NNN>`) do not work; `report` writes a stray file |
| H4 | High | `verify.py report` omits the `R#` outcome observations the docs require |
| H5 | High | Approvals are documented as gitignored but are committed, and embed machine-absolute CWDs |
| H6 | High | `specs-lint` is unusable in this repo, scans gitignored eval output, and crashes on Windows/cp1252 |
| H7 | High | ✅ **Fixed 2026-10-19** — `doctor` precondition 9 resolves the default branch and accepts `main` or `master` |
| M1 | Medium | MAP freshness ignores persona files (`.agents/agents/*.md`) |
| M2 | Medium | Global `npx skills -g` installs break four engines' root resolution and every documented command path |
| M3 | Medium | Contradictory statements: Lane C escalation, subtask gating, autonomous status, review promotion |
| M4 | Medium | Doc drift: `compile --lane`, fail-closed gate location, Personas table claim |
| m1 | Minor | Duplicated `AGENTS.md` check in two engines |
| m2 | Minor | `.gitattributes` references a nonexistent `PLAN.md` |
| m3 | Minor | `BACKLOG.md` has a stale (already fixed) entry and empty template entries |
| m4 | Minor | `specs/002-SPEC` is `DRAFTED` while 15 task files exist (13 without evidence) |
| m5 | Minor | Task slug truncation leaves trailing hyphens |
| m6 | Minor | Tag contract claims every `specs/` doc carries tags; task files do not |
| m7 | Minor | Stale TOC/status/report for spec 003; task files reference deleted paths |
| m8 | Minor | `docs/` one-way rule is contradicted by the docs themselves |

---

## Critical

### C1 — Compile pre-approvals are inert; `doctor` precondition 7 always fails

**Status: ✅ Fixed (2026-10-19).** Both engines now share one fingerprint, `sha256(command|expect|cwd)` (whitespace-stripped), and `verify.py run --lane A/B` also accepts a fingerprint found in `specs/NNN-APPROVALS-*.json` (not just the manual `specs/temp/approvals.json`). Regression test: `tests/test_approval_integration.py` exercises compile → `doctor` precondition 7 → `run --lane A` with no manual `approve`. The approvals file stays human-readable — each entry keeps its `command`/`expect`/`cwd` fields; only the `fingerprint` key is a digest (a hash, not encryption). Out of scope here: H5 (absolute CWDs pinned in committed approvals).

**Where**

- `skills/spec-builder/scripts/promote_spec.py:516-518` — `_fingerprint()` returns the plain string `command|expect|cwd`.
- `skills/verification-runner/scripts/verify.py:228-240` — `command_fingerprint()` returns `sha256(command|expect|cwd)`.
- `verify.py:646-667` — `_verify_preapproved()` (used by `doctor`) compares the stored value against the sha256.
- `verify.py:892-904` — `run` checks only `specs/temp/approvals.json` and never reads `specs/NNN-APPROVALS-*.json`.

**Evidence**

```text
$ python .agents/skills/verification-runner/scripts/verify.py doctor \
    --spec specs/003-SPEC-stop-the-engine-from-knowing-about-docs-readme-md.md
PRECONDITIONS FAILED:
- 4: spec Status is not COMPILED
- 7: Task 1 verify command not pre-approved
- 9: no 'main' branch to branch from
```

The command *is* present in `specs/003-APPROVALS-*.json`; the stored fingerprint is plain text while the engine compares a sha256. Running the same command through `run --lane A` returns exit 4 even though the per-spec approvals file exists.

**Impact**

- A fresh post-compile lane A/B run is refused until `verify.py approve` is called again.
- `doctor` can never reach `PRECONDITIONS OK` on a compiled spec, so unattended runs can never start.
- The two test suites pin the conflicting formats (`tests/test_promote_spec.py:399` vs `tests/test_verify.py:217`), so the suite stays green.

**Suggested fix**

1. Make one fingerprint function the shared source of truth (sha256), used by compile, `approve`, `run`, and `doctor`.
2. Seed the run-time approvals store from `NNN-APPROVALS-*.json` (or check it directly in `run`).
3. Add an integration test: compile a sandbox spec → `doctor` → `run --lane A` without a manual `approve`.

---

### C2 — Every compiled task file owns the whole spec's file set

**Status: ✅ Fixed (2026-10-19).** `_parse_tasks()` now reads each task's section-5 `Target Files:`; `_render_task_file()` copies only that task's files into `## Owns`; and `_validate_target_files()` (run by `check` and by `compile`) rejects a task with no target files, an entry with no `[OP]` tag, or two tasks claiming the same path. Regression tests: `tests/test_promote_spec.py::TestTargetFilesPerTask`. Pre-existing compiled specs (001–003) are not regenerated by this change — recompile them if their per-task `Owns` should be corrected.

**Where**

- `skills/spec-builder/scripts/promote_spec.py:549-563` — `_render_task_file()` builds `## Owns` from the **entire** section 4 body.
- `promote_spec.py:296-329` — `_parse_tasks()` ignores each task's `Target Files:` line completely.

**Evidence**

`specs/003-TASK-01` … `003-TASK-06` all list the same seven `Owns` paths (promote_spec.py, docs/README.md, SKILL.md, rules/system.md, docs/005-…, decision-records.md, test file), even though the spec assigns each task a different target set (`specs/003-SPEC-…md:118-164`). `verify.py` then hashes all seven files for every task, so all six tasks show `STALE` as soon as any file changes.

**Impact**

- The documented "one file = one task = one writer; disjoint `Owns` sets" invariant (`docs/task-files.md:19`, `task-file-format.md:103`) is false.
- Parallel coders can collide; the mechanical set-intersection dispatch check has nothing meaningful to check.
- Evidence goes stale for every task on any edit.

**Suggested fix**

Parse `Target Files:` per task and render only that task's files into `## Owns`; fail validation when a task has no target files or when two tasks overlap.

---

### C3 — The durable escalation record does not exist

**Where**

- `verify.py:352-355` — `write_escalation()` writes `<state-dir>/escalation.md` (default `specs/temp/escalation.md`).
- `verify.py:300-349` — `format_escalation()` titles the file `# ESCALATION - <task-id>` and has no spec number/slug.
- Nothing in either engine writes `specs/NNN-ESCALATION-<slug>.md` or stamps `Status: ESCALATED`.

**Docs that promise otherwise**

- `docs/verification.md:99-103`
- `docs/branching.md:27-29`
- `docs/flow.md:72`
- `docs/overview.md:54`

**Additional contradiction**

`format_escalation()` says "revert broken dirty edits" (`verify.py:347`), while the framework rule is that a run never reverts (`docs/branching.md:29`, `docs/verification.md:42`).

**Impact**

The failure audit trail — the whole point of the 3-attempt circuit breaker — lives in the scratchpad and is deleted by `task-cleaner` on the next acceptance.

**Suggested fix**

Write the consolidated escalation to `specs/NNN-ESCALATION-<slug>.md` in the spec group and stamp the spec `ESCALATED`; keep `specs/temp/escalation.md` only as a pre-spec (Lane C/no-spec) fallback. Make the "no revert" wording consistent.

**Status: ✅ Fixed (2026-10-19).** `verify.py` now routes the circuit-breaker escalation through `escalation_target()`: a task id carrying a spec number (`NNN-…`) whose spec file exists writes the durable `specs/NNN-ESCALATION-<slug>.md` and stamps the spec `Status: ESCALATED` (via `_stamp_escalated()`, preserving trailing metadata); otherwise (no spec number, or the spec is not on disk yet — Lane C / ad-hoc) it falls back to the ephemeral `specs/temp/escalation.md`. `format_escalation()` gained a `Spec:` line and no longer says "revert broken dirty edits" — the hand-back now states the run never reverts mid-build. Regression tests: `tests/test_verify.py::EscalationRecordTest`. Scope note: `phase-protocol/scripts/resolve_gate.py` also writes the scratchpad `escalation.md`, but its fail-closed gate is a *vetting*-stage block (lifecycle target `PLAN_REVISION_REQUIRED`), not the build-red `ESCALATED` transition, so it is intentionally not changed here.

---

### C4 — The `Status:` lifecycle is not engine-enforced; `promote` emits a non-canonical state

**Where**

- `promote_spec.py:1181-1185` — `normalize_status("APPROVED")` returns the literal `"APPROVED"`.
- `promote_spec.py:119-130` — `CANONICAL_STATUSES` does **not** contain `APPROVED`.
- `promote_spec.py:699-712` — `accept` is the only status transition with an engine command (`COMPLETED`).
- No engine command stamps `BUILDING`, `BUILT`, `REVIEWED`, or `ESCALATED`.

**Evidence of drift in this repo**

- `specs/003-SPEC-…md:10` → `Status: COMPLETED`
- `specs/003-REPORT-…md:5` → `Status: REVIEWED`
- `specs/README.md:36` → `BUILDING`

Also, spec 002 explicitly retires `Status: APPROVED` (`specs/002-SPEC-subagent-task-files-full-plan.md:874`), yet the current engine writes it.

**Impact**

The "single canonical receipt" claim (`docs/lifecycle.md:13-21`) is not enforceable; statuses drift silently because they are hand-edited. A promoted-but-not-compiled spec is in a state the engine does not recognize (e.g. `resolve_gate.find_active_spec` omits `APPROVED`).

**Suggested fix**

Add explicit `transition` support (or set status as part of `report`/`escalate`/`build`) and either add `APPROVED` to the canonical set or promote straight to `COMPILED`. Add a drift test that every `specs/*-SPEC-*.md` status is canonical and matches its report.

**Status: ✅ Fixed (2026-10-19).** `APPROVED` and `PROVISIONAL` joined `CANONICAL_STATUSES`; `resolve_gate.ACTIVE_STATUSES` gained both (plus `BUILT`). The missing transitions now have engine owners: `verify.py` advances `COMPILED → BUILDING` on the first PASS and `→ BUILT` once every section-5 task is `MET` (build), and a green `report` advances `BUILDING`/`BUILT` → `REVIEWED` (review); `resolve_gate.py` parks a fail-closed gate's target `PLAN_REVISION_REQUIRED` (Vetting) or `REVIEW_REVISION_REQUIRED` (Sign-off); `promote_spec.py transition <spec> --to <STATUS>` is the edge-checked writer for the rest (`ABORTED`, manual corrections), refusing a non-canonical target or an illegal edge. Enforcement: `check` rejects a non-canonical `Status:` receipt, `doctor` accepts only a canonical `COMPILED`/`BUILDING` spec, and `tests/test_drift_phases.py::SpecStatusDriftTest` asserts every `specs/*-SPEC-*.md` status is canonical. The cited `specs/README.md` drift (003 `BUILDING`) is refreshed via `promote_spec sync`. Regression tests: `tests/test_promote_spec.py::TestStatusTransitions`, `tests/test_verify.py::StatusAdvanceTest`, `tests/test_resolve_gate.py::GateBlockStatusTest`. Note: the transition semantics follow `docs/lifecycle.md`; the point-in-time `NNN-REPORT` status is not re-derived after acceptance, so a report may lag its spec's final `COMPLETED` (not enforced).

---

## High

### H1 — `drafted.md` Lane-A checklist lists the wrong sections

**Where**

`skills/phase-protocol/references/drafted.md:13-15` — "all seven sections … 6 Verification Commands, 7 Rollback Strategy".

**Contradicted by**

- `promote_spec.py:112` — Lane A requires sections `{1,2,3,4,5,6,7,8}`.
- `skills/spec-builder/references/implementation-plan-template.md` — 0 Frontmatter, 1 Goal, 2 Change, 3 Risks, 4 Affected Files, 5 Tasks, **6 Gates**, 7 Verification Commands, **8 Rollback**.
- `docs/decision-records.md:147` states the same 0–8 layout.

**Impact**

A plan authored by following the shipped checklist omits Gates/8 and fails `check`; the agent then has to re-plan.

**Suggested fix**

Rewrite section 2 of `drafted.md` to the actual 0–8 template (or, for Lane B, 1/4/5).

---

### H2 — Spec filenames are documented three ways; the README generator is wrong

**Where**

- `skills/spec-builder/SKILL.md:53` — says `specs/: NNN-<slug>.md`.
- `promote_spec.py:480-485` (`_spec_identity`) — only accepts `NNN-SPEC-<slug>.md`.
- `promote_spec.py:1621` — promotes as `NNN-SPEC-<slug>.md`.
- `promote_spec.py:983-1008` (`_specs_readme_stub`) — generates prose saying `specs/<NNN>-<feature-slug>.md`.
- `specs/README.md:5-11` — the same stale prose plus `NNN-<feature-slug>.md`.

**Also**

`_specs_readme_stub` still emits empty `<!-- TAG-INDEX:START/END -->` markers, although the `tag-index` subcommand was removed by spec 003. The constants (`promote_spec.py:136-137`) are now dead except for this scaffold.

**Impact**

A corrected skill cannot be followed literally; a fresh repo's `specs/README.md` describes a naming scheme the engine rejects.

**Suggested fix**

Use `NNN-SPEC-<slug>.md` in the skill, the stub, and `specs/README.md`; remove the dead tag-index markers/constants.

**Status: ✅ Fixed (2026-10-19).** The canonical spec filename is `NNN-SPEC-<slug>.md` everywhere it is documented: `skills/spec-builder/SKILL.md` (compile + ID-conventions lines), `skills/phase-protocol/references/compiled.md`, the `_specs_readme_stub()` scaffold in `promote_spec.py`, and `specs/README.md`. The dead `<!-- TAG-INDEX:START/END -->` scaffold and its `TAG_START`/`TAG_END` constants (orphaned when the `tag-index` subcommand was removed by spec 003) are gone. Regression test: `tests/test_promote_spec.py::TestSpecsReadmeScaffold`.

---

### H3 — Documented CLI forms do not work; `report` creates a stray file

**Where**

- `verification-runner/SKILL.md:25-27` advertises `doctor --spec <NNN>` and `report --spec <NNN>`.
- `verify.py:1163,1170` declare `--spec` as `Path`.
- `verify.py:1027-1032` only derives `MET/STALE` when `--task` is a `.md` path.
- `verification-runner/SKILL.md:42` says `status --task <id>` reports `MET`/`STALE`.

**Evidence**

```text
$ verify.py status --task "003-03"
task: 003-03
attempts: 0
state: green

$ verify.py doctor --spec 003
PRECONDITIONS FAILED:
- 4: cannot read spec
...

$ verify.py report --spec 003        # run in a temp repo
report: 003-REPORT-spec.md           # stray file written to CWD, exit 0
```

`report` does not validate the argument, derives `num` from `int(name[:3])`, uses slug `"spec"`, and writes to `Path("003").parent / "003-REPORT-spec.md"` — i.e. the current directory.

**Impact**

Following the docs silently produces wrong state or a stray file; a user cannot rely on the derived-status feature.

**Suggested fix**

Accept both a path and a bare `NNN` (resolve `specs/NNN-SPEC-*.md`), error when unresolved, and require a path for `status` or add a `--task-file` option. Update the skill text to match.

---

### H4 — `verify.py report` omits `R#` outcomes

**Where**

`docs/verification.md:105` — "the `R#` outcome observations (one line each — a missing observation **fails** review)".

`verify.py:822-858` — `report()` writes only `## Task Status` and `## Review (fresh re-run of verify commands)`; it never parses the Outcomes table or records `R#`.

**Impact**

Review cannot fail on a missing outcome, contrary to the documented gate.

**Suggested fix**

Parse the section-5 Outcomes table and emit one observation line per `R#`, with an explicit FAIL when absent.

---

### H5 — Approval files: "gitignored" vs committed, and non-portable CWDs

**Docs saying gitignored**

- `docs/decision-records.md:75`
- `skills/task-cleaner/SKILL.md:19,34`
- `skills/spec-builder/references/task-file-format.md:17`
- `specs/002-TASK-02-…md:17`

**Docs saying committed**

`docs/verification.md:56` — "Approvals travel with the spec group (committed as the group's companion)".

**Reality**

- `specs/003-APPROVALS-stop-the-engine-from-knowing-about-docs-readme-md.json` **is tracked by git**.
- `.gitignore` has no `*-APPROVALS-*` rule.
- The fingerprint embeds `/mnt/HDD2TB/Projects/dev-agent`, so it is invalid on any other machine/checkout (including this Windows one).

**Impact**

The approval store is either leaked machine state or silently invalid, depending on which doc you believe.

**Suggested fix**

Decide one model. If committed, hash a repo-relative CWD (or exclude CWD) so pre-approvals are portable; if scratch, add the ignore rule and stop calling it part of the group.

---

### H6 — `specs-lint` is unusable here, scans ignored eval output, and crashes on Windows

**Where**

- `promote_spec.py:253-257` — `SPECS_LINT_SKIP_DIRS` lacks `.behavior-review` (and does not skip `skills/`, `tests/`, root docs).
- `promote_spec.py:1565-1574` — prints raw file lines with `print()`, no encoding guard.

**Evidence**

- `specs-lint` reports **228 references**, including its own source, `skills/`, `tests/`, `AGENTS.md`, `README.md`, and all of `docs/`.
- The gitignored `.behavior-review/*.html` files are scanned; their 172 KB single-line embedded JSON is dumped to the console.
- Without `PYTHONIOENCODING=utf-8`, a piped/Windows run crashes:

```text
UnicodeEncodeError: 'charmap' codec can't encode character '\u2192'
```

**Impact**

The canonical enforcement command (named in the consumer rulebook) is unusable in the framework repo, noisy on any repo with generated HTML, and broken in CI on Windows.

**Suggested fix**

Add `.behavior-review` (and any other gitignored output) to the skip list; print with `errors="replace"` or wrap stdout; scope the scan to consumer-safe surfaces; and either exempt this repo's docs or narrow the rule to *links/dependencies* rather than any `specs/` substring.

---

### H7 — `main` is hardcoded; this repo uses `master`

**Where**

`verify.py:698-708` — precondition 9 runs `git rev-parse --verify refs/heads/main`.

**Evidence**

```text
$ git branch --show-current
master
$ git branch -a
* master
  spec/003-docs-readme-human-maintained
  v2
  remotes/origin/HEAD -> origin/master
```

**Impact**

`doctor` precondition 9 fails on every spec in this repo, blocking unattended runs; the rulebook's "never merge to `main`" guardrail names a branch that does not exist here; the framework is not project-agnostic as advertised.

**Suggested fix**

Resolve the default branch (`git symbolic-ref refs/remotes/origin/HEAD`, `init.defaultBranch`, or a project setting) with `main` as fallback.

**Status: ✅ Fixed (2026-10-19).** `verify.py`'s precondition 9 (`_branch_possible`) now resolves the base branch: it prefers the remote's declared default (`git symbolic-ref refs/remotes/origin/HEAD`) and otherwise accepts `refs/heads/main` **or** `refs/heads/master`, failing only when neither exists. The shipped skill docs (`phase-protocol/SKILL.md`, `references/building.md`) and `docs/branching.md` now say "the default branch (`main`/`master`)" instead of hardcoding `main`. Regression test: `tests/test_verify.py::BranchPossibleTest` (master accepted, main accepted, non-repo rejected).

---

## Medium

### M1 — MAP freshness ignores personas

`generate_map.py:146-180` hashes only `SKILL.md` files (`snapshot_of(scan_skills(root))`), but `build_map()` renders `.agents/agents/*.md` as `## Personas & Roles` (`:339-356`). Editing `coder.md` does not regenerate MAP; only `--force` does. (This is why MAP had no Personas row until it was regenerated during the audit.)

**Fix:** include `.agents/agents/*.md` in the snapshot, or drop personas from the generated index.

### M2 — Global installs break the boot chain

`generate_map.py:46-58`, `match_skills.py:157-169`, `clean.py:45-57`, and `bootstrap.py:51-60` resolve the repo root by walking up from the **script location**; `verify.py` and `promote_spec.py` walk up from the **CWD** first. README recommends `npx skills add … -g` (global to `~/.config/opencode/skills/`), but every documented command uses the project-relative `.agents/skills/...` path. A global install therefore cannot find the target repo or the documented script path.

**Fix:** resolve root from CWD first in every engine (matching `verify.py`), and document how the harness locates the skill scripts.

### M3 — Contradictory behavioral statements

- **Lane C exhaustion:** `lane-matrix.md:10`, `docs/routing.md:18`, and `docs/lifecycle.md:48` say 3 failures escalate to Lane B; `docs/verification.md:78` says there is no separate 3-consecutive breaker and the 3 attempts are the budget. No engine path escalates C→B.
- **Subtask gating:** `building.md:12` says `[x]` only when the task's `Verify` passes; `docs/task-files.md:23` and `todo-checklist-format.md` say subtasks are the coder's own checklist and never a second gate.
- **Autonomous status:** `docs/lifecycle.md:109` and `docs/decision-records.md:137` say the spec stays `COMPILED` with no topic decisions; `spec-builder/SKILL.md:45` and `compiled.md:15` say `PROVISIONAL - AUTONOMOUS DEFAULT`.
- **Review promotion:** `harness.md:9` says review promotes the spec to `specs/`; `reviewed.md:19` says it was promoted at approval and review only finalizes.

**Fix:** pick one rule per pair, align the docs and the engine, and add drift tests.

### M4 — Doc drift

- `docs/decision-records.md:115` documents `promote_spec.py compile <spec> --lane <B|A>`; `compile` has no `--lane` (`promote_spec.py:1786-1791`).
- `docs/lifecycle.md:83` says a fail-closed gate records the question/options in the spec's `Gates:` section; the engine writes `specs/temp/escalation.md` (`resolve_gate.py:313-324`).
- `docs/skill-discovery.md:36` says the Personas table is "not present in this repo"; `.agents/agents/coder.md` exists and MAP now emits it.
- `docs/README.md:9` says every doc except the landing page is a topic doc; `_topics.md` is generated and is not.

---

## Minor / hygiene

| ID | Finding | Location |
| :-- | :-- | :-- |
| m1 | Duplicated `AGENTS.md` check (`(current / "AGENTS.md").is_file() or (current / "AGENTS.md").is_file()`), and the error message repeats it | `match_skills.py:161`, `resolve_gate.py:48-57` |
| m2 | Comment cites a nonexistent `PLAN.md` | `.gitattributes:1-2` |
| m3 | Stale oracle-lint item (the substring rule was already relaxed in `_unfailable_expect`), plus three empty template entries | `BACKLOG.md:24`, `:26-32` |
| m4 | `002-SPEC` is `DRAFTED` but has 15 task files; 13 have no evidence block and most progress boxes are unchecked | `specs/002-SPEC-…md:10`, `specs/002-TASK-*` |
| m5 | Task slugs truncate at 40 chars without re-stripping, leaving trailing hyphens | `promote_spec.py:507-513` → `003-TASK-02-…readme-.md` |
| m6 | "Every committed doc in `specs/` carries tags" is false for task/report files, and `tag-lint` does not enforce it | `docs/decision-records.md:81`, `promote_spec.py:1043-1059` |
| m7 | TOC/status/report are inconsistent for 003, and its task files reference deleted paths (`.agents/rules/system.md`, `docs/005-…md`); `toc --dry-run` would add the missing REPORT row and fix the status | `specs/README.md:36-42`, `specs/003-TASK-*` |
| m8 | The one-way `specs/` rule is contradicted by the docs it ships with (see H6) | `docs/README.md:96` vs `docs/README.md:19,59,60,66,76` |

---

## Checks run

| Check | Result |
| :-- | :-- |
| `python -m unittest discover -s tests` | 215 tests, **OK** (2 skipped) |
| `python -m ruff check skills tools tests` | **All checks passed** |
| `python -m compileall -q .agents skills tools tests` | exit 0 |
| `python tools/promote.py --check` | **promote: clean** |
| `python tools/suite_report.py` | **no drift: 215 tests match the baseline** |
| `python .agents/skills/map-generator/scripts/generate_map.py` | `regenerated` (was stale) |
| `python .agents/skills/spec-builder/scripts/promote_spec.py tag-lint` | `tag-lint: ok` |
| `python .agents/skills/spec-builder/scripts/promote_spec.py specs-lint` | **exit 1 — 228 refs** (see H6) |
| `verify.py doctor --spec specs/003-SPEC-…md` | **FAILED** (gaps 4, 7, 9 — see C1/H7) |
| `verify.py status --task specs/003-TASK-03-…md` | `STALE` (the 003 report claims all `MET`) |

## Why the suite is green

The gaps are in **integration seams**, not unit logic: no test compiles a spec and then runs `doctor`; no test asserts that `Owns` is per-task; no test exercises the documented bare-`NNN` CLI forms; no test runs `specs-lint` against the real repo; and the status set test asserts the canonical list without checking what `promote` actually writes.

## Suggested next step

Fix the four critical items first (C1–C4) as one Lane B spec, with an integration test per seam. The docs-only items (H1–H5, M3–M4) can ride along or follow as a separate consistency pass; H6 and H7 are small, self-contained engine fixes.
