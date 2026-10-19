# Behavior Evals - Multi-Step Scenarios (one repo, many prompts) Plan

> **Status:** In progress
> **Scope:** `tools/behavior_eval.py` + `tests/fixtures/behavior/` +
> `tests/test_behavior_harness.py`. Additive and backward-compatible.

---

## 1. Why

Today one **case** = one prompt + N artifact checks, seeded into its **own**
repo *per config*:

```
<case>/<run-id>/repo/            new_skill
<case>/<run-id>/old_skill/repo/  old_skill
<case>/<run-id>/without_skill/repo/
```

`batch --skill auto-router` over 6 cases x 2 configs = **12 repos and 12
installs**. Each prompt is isolated, so the harness cannot express a *session* of
related prompts against one repo.

## 2. Decision

A **scenario** is a case that carries `steps` instead of a flat `prompt`:

- One repo **per config** (not per prompt) - repo/install count drops from
  `M x configs` to `configs`.
- The M prompts are **independent**: before each step the working repo is reset
  from a pristine snapshot, so a step never sees an earlier step's mutations.
  (Chosen over sequential carry-over.)
- Each step keeps its own N artifact checks and is graded independently.

`M prompts x N checks` is preserved; only the *repo* is shared.

## 3. Schema

```json
{
  "name": "b2-lane-triage",
  "layer": "behavior",
  "profile": "bootstrapped-node",
  "setup": ["bootstrap", "skills:auto-router,phase-protocol"],
  "steps": [
    { "id": "surface-outranks-count", "prompt": "...",
      "expectations": ["..."], "expected_artifacts": ["..."] },
    { "id": "ambiguity-defaults-upward", "prompt": "...",
      "expectations": ["..."], "expected_artifacts": ["..."] }
  ]
}
```

**Backward compatible.** A case with a flat `prompt` is normalized to one
implicit `Step(id=name, ...)` with `legacy=True` and keeps the *exact* current
on-disk layout (transcript/outputs/result.json at the config root). All existing
cases and tests keep working untouched.

`assertion_labels` stays case-level and applies to every step's artifact
strings.

## 4. Layout (multi-step)

```
<scenario>/<run-id>/
  run.json                       # + "multi_step": true, "steps": [ids]
  repo/                          # shared working repo (reset per step)
  _base_repo/                    # pristine snapshot used for the reset
  steps/1-<id>/
    transcript.md                # this step's stdout
    outputs/answer.md
    repo/                        # repo snapshot after this step
    result.json  grading.json
  steps/2-<id>/ ...
  old_skill/{repo,_base_repo,steps/...}
  without_skill/{repo,_base_repo,steps/...}
```

A step dir is shaped exactly like a legacy run dir (`repo/` + `transcript.md`
at its root), so the existing artifact DSL and `check_artifact` work unchanged.

## 5. Tasks

- **E1 - Model.** Add `Step`; `Case` gains `steps` + `legacy`; `Case.load`
  parses/normalizes and validates (no `prompt` + `steps` together; each step
  needs `id`/`prompt`/`expected_artifacts`; ids unique).
- **E2 - Run.** `drive_opencode` gains `capture_dir`; add
  `snapshot_base_repo`/`reset_working_repo`; `run_config` resets + runs each
  step and snapshots the repo per step. `cmd_run`/`cmd_batch` call it.
- **E3 - Grade.** `check_config` routes multi-step cases to
  `check_config_steps` (per-step `result.json`/`grading.json` + a config
  aggregate).
- **E4 - Review.** `review_units(case, config, base)` expands a multi-step
  config into per-step pseudo-cases (`<case>#<step>`) so `render_review` /
  benchmark render one page per step with configs side by side.
- **E5 - Demo.** Merge `b2-2..b2-6` into `b2-lane-triage` (5 steps); keep
  `b2-1-four-lanes` as the single-prompt control; delete the 5 old case dirs.
- **E6 - Tests/docs.** Update the catalog count (39 -> 35) and per-step
  validation; add multi-step unit tests; refresh the module docstring.
- **E7 - Verify.** `compileall`, `ruff`, `unittest`, `suite_report`.

## 6. Definition of done

- Existing single-prompt cases behave identically (legacy layout preserved).
- A multi-step case installs once per config, runs M independent prompts, and
  grades N checks per step with one review page per step.
- Suite green; `ruff` clean; `compileall` clean; `suite_report` no drift.

## 7. Progress

**Implemented; all gates green** (`286 tests OK, 2 skipped`, `ruff` clean,
`compileall` clean, `suite_report` no drift).

- **E1** `Step` dataclass; `Case` gained `steps` + `legacy`; `Case.load`
  normalizes a flat case to one implicit step and validates scenarios
  (no `prompt`+`steps`; per-step `id`/`prompt`/`expected_artifacts`; unique ids).
- **E2** `drive_opencode(capture_dir=...)`; `snapshot_base_repo` /
  `reset_working_repo` / `step_dir`; `run_config` resets, runs each step, and
  snapshots the repo per step. `run.json` carries `steps` + `multi_step`.
- **E3** `_grading` / `_step_checks` shared; `check_config_steps` writes
  per-step `result.json`/`grading.json` plus a config aggregate.
- **E4** `review_units` expands a scenario into per-step pseudo-cases
  (`<case>#<step>`) so `render_review` gives one page per step with configs side
  by side + Benchmark.
- **E5** `b2-2..b2-6` merged into `b2-lane-triage` (5 steps); `b2-1-four-lanes`
  kept as the legacy control; old dirs deleted. Case count 39 -> 35.
- **E6** Catalog test validates per step and asserts 35; new `MultiStepTest`
  (10 tests) covers normalize/validate/grading/review/reset. Module docstring
  updated.
- **E7** Gates green; CLI smoke test: `b2-lane-triage --config compare` seeds
  one repo per config (2 installs) with `multi_step: true` and the 5 step ids.

### Deviations

- **Kept `b2-1` instead of merging all 6.** Many harness tests reference
  `b2-1-four-lanes` as the single-prompt fixture; keeping it preserves that
  regression coverage and gives a legacy-vs-scenario pair.
- **`case_steps(case)` accessor** added so hand-built `Case` objects in tests
  (no `steps`) still grade through the legacy path.

## 8. All-families merge (pass 2)

Merged by **input state**, not by name prefix. Compatibility key =
`(profile, setup, byte-identical overlay repo)`. The audit found **18 groups**;
only four had more than one member:

| group (setup, overlay) | members | result |
|---|---|---|
| default, none | 13 | 4 scenarios + `b2-1` kept |
| spec-builder, none | 4 | `b4-spec-planning` |
| spec-builder + verification-runner, none | 2 | `b6-run-discipline` |
| spec-builder + verification-runner + map-generator, `map` | 2 | `b9-skill-recall` |

The 14 remaining cases each have a **unique** input state (different setup
and/or overlay) and cannot share a repo.

**Same prefix is not same input state.** `b4-2-run-refused-not-compiled` and
`b4-3-vetting-gate-revision` share the `b4-` prefix and setup, but their
`specs/001-SPEC-cache.md` overlays differ (different bytes) - so they seed
*different* repos and were **not** merged. Same for `b1-1` (no map) vs `b1-2`
(map), and the five distinct `specs/001-SPEC-cache.md` overlays in
`b5-1`/`b6-2`/`b6-3`/`b6-4`/`b4-2`/`b4-3`.

**New scenarios (all members of each mergeable group):**

- `b3-session-autonomy` (5): the session/autonomy/blocking-gate cases.
- `b4-spec-planning` (4): autonomous decision, gate-type label, compile-then-stop,
  unfailable-verify refusal.
- `b6-run-discipline` (2): no-alternatives-later, never-merge-main.
- `b6-guardrails` (2): no-op on chit-chat, refuse protected file.
- `b7-docs-and-lanes` (4): pattern-break escalation, docs-without-specs links,
  specs disposal, route-a-plan.
- `b9-skill-recall` (2): not-over-triggered, thin-candidates map fallback.

`b2-lane-triage` (5) stays; `b2-1-four-lanes` stays single as the harness'
legacy-layout fixture.

**Result:** 39 prompts now live in **22 case dirs** (7 scenarios + 15 singles),
down from 39 dirs. Within the four mergeable groups, dirs fell 21 -> 8, so
`batch --config compare` over them drops from 42 installs to 16. Gates green
(286 tests; `ruff`/`compileall` clean; `suite_report` no drift).


