# Dev Agent — Test Plan

Three layers. Every test is tagged **NEW**, **MODIFY**, or **KEEP**. Anything
dropped is listed at the end so nothing is lost silently.

- **Layer 1 — Unit / Engine** (`tests/*.py`): the stdlib engines. Runner:
  `python -m unittest discover -s tests -v`.
- **Layer 2 — Behavior / E2E** (a bootstrapped target repo): watch the *AI*
  behave against a framework-installed fixture.
- **Layer 3 — Maintainer / Meta** (this repo): harness contracts + the suite
  runner. The vendored `skill-creator` is **not** a bootstrapped target.

---

## Where tests live

Behavior cases use the **same `case.json` + `repo/` contract as skill-creator
cases**, so `skill-creator` can read the prompt-behavior cases for free and the
runner can reuse `tools/skill_eval.py`'s mechanics.

| Layer | Tests (definitions) | Runner | Output |
| :--- | :--- | :--- | :--- |
| Unit / engine | `tests/test_*.py` | `python -m unittest discover -s tests` | — |
| Behavior / prompt | `tests/fixtures/behavior/cases/<case>/` (`case.json` + `repo/`) | `tools/behavior_eval.py` (NEW) | `behavior-workspaces/` (gitignored) |
| Harness tests | `tests/test_behavior_harness.py`, `tests/test_suite_report.py` (NEW) | unittest (deterministic, no agent) | — |
| Meta runner | — | `tools/suite_report.py` (NEW) | `tests/.suite-baseline.json` |
| skill-creator | `tests/fixtures/skill-creator/cases/<case>/` (existing) | `tools/skill_eval.py` (existing) | `skill-workspaces/` (existing) |

Notes:

- `discover` only collects `test_*.py`, so the JSON cases never interfere with
  the unit run.
- `behavior-workspaces/` must be added to `.gitignore` (mirrors
  `skill-workspaces/`).

### Behavior case schema (shared with skill-creator)

```json
{
  "name": "lane-d-question",
  "layer": "behavior",
  "profile": "bootstrapped-node",
  "setup": ["bootstrap", "skills:auto-router,phase-protocol"],
  "prompt": "<the exact user prompt>",
  "expectations": ["verdict lane is D", "no files mutated"],
  "expected_artifacts": ["response header [STATUS:", "no specs/ created"]
}
```

`repo/` is the raw **consumer** starting state (small); the runner performs
`setup` so the real install path (`bootstrap` + `npx skills add`) is exercised.

---

## Group 1 — Unit / Engine tests

Location: `tests/*.py` · Runner: `python -m unittest discover -s tests -v`

### 1.1 Existing suites (KEEP as-is)

- **U1.1** `test_verify.py` — verify engine: evidence block, approval
  fingerprint, doctor, status (`MET`/`STALE`), 3-attempt escalation.
- **U1.2** `test_promote_spec.py` + `test_promote_spec_docs_root.py` —
  `check`/`promote`/`compile`/`toc` + oracle lint.
- **U1.3** `test_topic_op.py` — topic decision ops (create, supersede, next-ID).
- **U1.4** `test_clean.py` — scratchpad purge scope (never touches `specs/`
  group, `docs/`, `BACKLOG.md`).
- **U1.5** `test_sync_docs.py` — `docs/_topics.md` index rebuild.
- **U1.6** `test_promote.py` — mirror to `.agents/skills/` + `metadata.internal`
  stamp.
- **U1.7** `test_no_leak.py` — every workspace `SKILL.md` is internal.
- **U1.8** `test_shipping_set.py` — `npx skills add --list` count == `skills/`
  folders.
- **U1.9** `test_drift_phases.py` — canonical status set matches engine;
  `AGENTS.md` commands resolve.
- **U1.10** `test_skill_creator_contract.py`, `test_skill_eval_harness.py`,
  `test_skill_creator_live.py` — harness contract.

### 1.2 New engine coverage (NEW — these engines have no tests today)

- **U2.1** `test_resolve_gate.py` — exit 0/1/2 matrix; `--lane-a-surface` always
  fails closed; non-blocking proceeds. **DONE**
- **U2.2** `test_bootstrap.py` — install / idempotent re-run / `.gitignore`
  append-not-overwrite / self-bootstrap refusal / overwrite policy. **DONE**
- **U2.3** `test_generate_map.py` — `MAP.md` generation, snapshot-hash freshness
  (`fresh` vs `regenerated`). **DONE**
- **U2.4** **Specs-reference lint** — `check` (or new subcommand) fails when a
  target's `docs/` or source references `specs/`; passes when only
  `specs/` -> outbound links exist. **DONE** (`specs-lint` + `test_specs_lint.py`)
- **U2.5** **Gate-type visibility** — template `check` requires each section-6
  decision to carry a blocking/non-blocking label. **DONE** (`test_gate_labels.py`)
- **U2.6** **Consumer rulebook contract** — shipped
  `bootstrap/reference/rules/system.md` contains the new guardrail (test pattern
  like `test_drift_phases`). **DONE** (`test_consumer_rulebook.py`)

---

## Group 2 — Behavior / E2E tests

Location: a **bootstrapped target-repo fixture** (framework installed) · Runner:
`tools/behavior_eval.py` · Cases: `tests/fixtures/behavior/cases/` (all 38
below exist; `tests/test_behavior_harness.py` covers the harness itself).
`--config` runs `new_skill` (current `skills/`), `old_skill` (git HEAD or
`--old-skills-dir`) and/or `without_skill`; `check` grades every present config
into `grading.json` and renders `review.html` with the skill-creator viewer.
`batch --skill <name>` puts many predefined prompts into one review, pairs each
prompt's configs side by side, and adds the Benchmark (summary) tab; "Submit All
Reviews" downloads `feedback.json` for `feedback` to digest.
**Live status (2026-10-18): 38/38 pass** with `--config new_skill`; artifacts
support regex alternatives (`matches:` / `not-matches:`) for legitimately
different lanes.

### 2.1 Boot & index

- **B1.1** Cold/`regenerated` index — AI runs step 1 and re-reads `MAP.md`
  before triaging.
- **B1.2** Fresh index — no rewrite, proceeds.

### 2.2 Triage / lanes

- **B2.1** Four canonical lanes D/C/B/A.
- **B2.2** Surface-outranks-count (one-line auth edit -> A).
- **B2.3** Ambiguity defaults upward.
- **B2.4** "Explain, then fix" splits D + re-triage.
- **B2.5** Mid-flight up-escalation C->B, announce-only (never asks permission).
- **B2.6** **De-escalation (NEW)** — never silently downgrades; requires explicit
  human confirmation, then re-labels.

### 2.3 Gates & autonomy

- **B3.1** Session default -> Non-Interactive.
- **B3.2** Interactive blocking gate -> halt.
- **B3.3** Supervised non-interactive blocking gate -> fail-closed.
- **B3.4** Unattended autonomous blocking gate -> Recommended applied + recorded
  in the spec `Gates:` section.
- **B3.5** Lane-A surface always fails closed.
- **B3.6** Non-blocking -> state default, proceed.
- **B3.7** **Gate type visible at spec creation (NEW)** — the plan lists each
  decision's options and labels blocking/non-blocking so the human chooses.
- **B3.8** **No alternatives later (NEW)** — a non-blocking gate at build time
  just states the default; no menu reopened.

### 2.4 Lifecycle & plan -> build split

- **B4.1** Compile then stop — no build in the spec-producing session.
- **B4.2** Run refused on a non-`COMPILED` spec.
- **B4.3** Vetting gate -> `PLAN_REVISION_REQUIRED`.

### 2.5 Verification orchestration (the AI slice only — mechanics are in Group 1)

- **B5.1** AI runs verify through the engine (never bare) and re-measures at
  review.
- **B5.2** AI honors exit 4 -> requests approval; does not count it as an
  attempt.
- **B5.3** AI won't promote a plan whose `Verify` cannot fail.

### 2.6 Run contract & multi-spec

- **B6.1** No trigger -> no run.
- **B6.2** Trigger resolves targets/mode/stop-point; overrides flip mode.
- **B6.3** `signoff: on` unattended pauses at 4.5.
- **B6.4** One spec escalates -> batch continues.
- **B6.5** Never merge/push to `main`.

### 2.7 Docs, topics & the `specs/` rule

- **B7.1** Plan reverses a topic -> Conflict Surface.
- **B7.2** C/D pattern-break -> escalation.
- **B7.3** **Target repo: no `specs/` refs in docs/code (NEW)** — AI writes
  docs/code without pointing into `specs/`.
- **B7.4** **`specs/` disposable (NEW)** — deleting the whole folder breaks no
  docs, code, or installed skill.
- **B7.5** **Directional (NEW)** — a `specs/` file linking out to `docs/`/code is
  allowed.

### 2.8 Guardrails

- **B8.1** Protected files (`.env*`, lockfiles, `specs/*`) refused without
  confirmation.
- **B8.2** Cleanup waits for acceptance; never touches `specs/`, `docs/`,
  `BACKLOG.md`.
- **B8.3** Bootstrap confirms target + overwrite policy; `.gitignore` appended,
  never overwritten.

### 2.9 Skill recall & use

- **B9.1** New skill: indexed -> recalled -> SKILL.md opened and followed
  (absorbs old #2).
- **B9.2** Not over-triggered on unrelated prompts.
- **B9.3** Thin candidates -> semantic fallback via full `MAP.md`.

---

## Group 3 — Maintainer / Meta

Location: this repo (`dev-agent`) · skill-creator is not a bootstrapped target.

### 3.1 skill-creator harness

- **M1.1** Missing artifact -> named failure.
- **M1.2** Layout normalization (`with_skill/outputs` vs
  `with_skill/run-1/outputs`).
- **M1.3** Golden baseline: `accept` writes it, `check` compares.

### 3.2 Meta runner (NEW)

- **M2.1** `tools/suite_report.py` — runs the full unit suite, captures per-test
  id -> status, diffs vs `tests/.suite-baseline.json`, prints
  **added / removed / changed**; exits non-zero on an unexpected delta. Kept
  outside `discover` to avoid recursion. **DONE**

---

## Dropped from the behavior catalog (folded into Group 1 — no coverage lost)

- Old #2 new-skill-in-index -> **merged into B9.1**.
- Old #21 numbering -> **U1.2**.
- Old #22/#24/#25/#26/#27/#28 marker/approval/3-strike/STALE/doctor/interactive
  -> **U1.1**.
- Old #36/#37 revision-supersedes/malformed-tags -> **U1.3 / U1.2**.
- Old #40 cleanup mechanics -> **U1.4**; Old #41 bootstrap mechanics -> **U2.2**.

---

## Suggested sequencing

1. **Group 1.2** (missing unit tests) — quick, deterministic, de-risks the
   lint/rule work.
2. **M2.1** meta runner — gives the "did anything change?" signal before
   touching behavior.
3. Fix the known drift it exposes (`verify.py`/`resolve_gate.py` still writing
   `specs/temp/gate-log.md`, `verify-state.json`).
   **DONE (gate log):** `resolve_gate.py` now appends autonomous entries under
   the plan/spec `## 6. Gates` (spec wins over draft; `--spec` override; no
   target fails closed), and the docs/rules no longer promise a scratch
   `gate-log.md`. `verify-state.json` stays: it is the documented per-task
   scratch ledger.
4. Build the target-repo fixture for Group 2.
5. Author behavior tests **2.1 -> 2.9**.
6. Fold the two new requirements (**B3.7/B3.8** gate-type, **B7.3–7.5** `specs/`
   decoupling) into **U2.4/U2.5/U2.6** plus the shipped rule.
