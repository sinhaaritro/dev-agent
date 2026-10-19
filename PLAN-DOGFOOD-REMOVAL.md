# Dev Agent — Stop Dogfooding (Shape 2) Plan

> **Status:** In progress
> **Scope:** Collapse the repo's two-tree dogfood model to a single source
> tree. `skills/` stays the canonical, shipped product; the repo stops running
> the framework on itself. Pure maintainer tooling/evals stay.
> **Note:** A plain working plan. It intentionally does **not** use the repo's
> `specs/` phase lifecycle.

---

## 1. Why

Today the repo keeps **two copies** of the framework:

- `skills/` — the canonical product (what `npx skills add` ships).
- `.agents/skills/` — a derived dogfood mirror so *this repo's own agent*
  can load and run the framework on itself, plus `.agents/scripts/devagent/`
  (the mirrored runtime), `.agents/rules/dev-agent-framework.md` (the gateway
  rulebook this repo loads every session), and `.agents/.promoted.json`.

The mirror is maintained by `tools/promote.py` and guarded by
`tests/test_promote.py` (`RuntimeMirrorTest`, `RuntimeDriftGuardTest`,
`LiveRepoTest`). It is the only reason for the second tree.

But the framework is *not* actually used to develop itself: the shared-runtime
refactor (see `PLAN.md`) was driven by a plain working plan, deliberately
outside the spec/phase machinery. The dogfood copy is overhead with no payoff.

Precedent (see research): BMAD, Spec Kit, and SpecOps all keep **one canonical
source** and **generate** derived artifacts; self-development uses a
**maintainer-specific surface** (BMAD's `bmd` module), never a hand-maintained
duplicate of the consumer product.

## 2. Decisions

| # | Decision |
|---|----------|
| D1 | `skills/` stays the single source of truth. The product is untouched. |
| D2 | Delete the dogfood mirror (`.agents/skills/<7 consumer skills>`) and the mirrored runtime (`.agents/scripts/devagent/`). |
| D3 | Delete `.agents/.promoted.json` and `.agents/MAP.md`. |
| D4 | Retire `tools/promote.py`, `tests/test_promote.py`, and the repo-only `promote` skill. Nothing left to mirror. |
| D5 | Stop loading the framework gateway in this repo: delete `.agents/rules/dev-agent-framework.md` and `.agents/agents/coder.md` (both are dogfood copies; the canonical seeds live under `skills/dev-agent/reference/`). |
| D6 | Stop pointing this repo's IDE at the gateway: delete root `.cursorrules` / `.windsurfrules`. |
| D7 | Root `AGENTS.md` drops the "DEV AGENT" gateway section and gains a short **Maintainer contract** (the `bmd` analog): source is `skills/`; verify with `tools/` + `tests/`; do not use the spec/phase gates for framework work. |
| D8 | Keep repo-only tooling skills under `.agents/skills/`: `author-skill` (rewritten, no promote) and vendored `skill-creator`. They still carry `metadata.internal: true`. |
| D9 | Keep the evals (`tools/behavior_eval.py`, `tools/skill_eval.py`, `tools/suite_report.py`). They never depended on the mirror: behavior evals read `skills/` (working tree vs `git HEAD`) and install into a throwaway consumer workspace **outside** the repo. |

## 3. Keep / delete

| Path | Keep? | Why |
|---|---|---|
| `skills/` | Keep | The product. |
| `.agents/skills/{author-skill,skill-creator}` | Keep | Repo-only tooling. |
| `.agents/skills/{dev-agent,auto-router,map-generator,phase-protocol,spec-builder,task-cleaner,verification-runner}` | Delete | Derived mirror. |
| `.agents/skills/promote` | Delete | Mirror engine's skill; obsolete. |
| `.agents/scripts/devagent/` | Delete | Mirrored runtime. |
| `.agents/rules/`, `.agents/agents/` | Delete | Dogfood copies of seeds. |
| `.agents/.promoted.json`, `.agents/MAP.md` | Delete | Mirror bookkeeping. |
| `.cursorrules`, `.windsurfrules` (root) | Delete | Repo IDE pointers to the removed gateway. |
| `tools/{behavior_eval,skill_eval,suite_report}.py` | Keep | Maintainer tooling. |
| `tools/promote.py`, `tests/test_promote.py` | Delete | Mirror engine + its tests. |
| `docs/`, `specs/`, `tests/`, `README.md`, `AGENTS.md` | Keep | Update references. |

## 4. Tasks

**T1 — Delete the mirror.** Remove the paths above (git rm where tracked;
plain delete for untracked generated files).

**T2 — Root `AGENTS.md`.** Rewrite "What this repo is", the repo map, the
commands, and the hard rules to the single-tree model; replace the "DEV AGENT"
section with a **Maintainer contract**.

**T3 — Author-skill rewrite.** `.agents/skills/author-skill/SKILL.md`: drop the
`promote` handoff; the loop becomes "edit `skills/<name>/` → verify with
`tools/` + `tests/`".

**T4 — Tests.**
- Delete `tests/test_promote.py`.
- `tests/test_no_leak.py`: keep the invariant; reword the docstring (it now
  guards `author-skill` + vendored `skill-creator`).
- `tests/test_shipping_paths.py`: drop `promote` from the forbidden engine
  regex and the guard example.
- Refresh `tests/.suite-baseline.json`.

**T5 — Docs.**
- `README.md`: repo map (drop `promote.py`), architecture paragraph, dev
  commands, "only skills/ ships" wording.
- `docs/README.md`: "Where things live" rows; "How to make a change" step 1.
- `docs/overview.md`: directory map; add an `OVERVIEW-D0x` Decision Log entry.
- `docs/skill-discovery.md`, `docs/routing.md`, `docs/decision-records.md`:
  verify remaining `.agents/skills/...` references describe the **consumer**
  install layout (keep) vs the repo mirror (fix).
- Regenerate `docs/_topics.md`.
- `pyproject.toml`: comment wording only.

**T6 — Verify.** `compileall`, `ruff`, `unittest`, `suite_report`, plus a
manual `npx skills add . --list` sanity check.

## 5. Out of scope (Phase 2 — designed, not built)

**Behavior-eval baseline.** The evals already work without dogfood, but nothing
records an *accepted* run in the repo. Add the skill_eval `accept` analog:

- `behavior_eval accept --case X --run-id Y` writes
  `tests/fixtures/behavior/baselines/<case>.json` with the accepted grading plus
  a hash of the `skills/` subtree under test.
- `batch`/CI compare against the baseline; a skill edit that regresses flips it
  to drift (same shape as `suite_report.py`).

Flow: change skills on a branch → `batch` there → green → `accept` → merge code
+ baseline together → main CI re-checks the baseline. Optional git worktrees
give isolation/parallelism; they are not required.

## 6. Definition of done

- No `.agents/skills/<consumer skill>` mirror, no `.agents/scripts/devagent/`,
  no `.agents/rules/` / `.agents/agents/`, no `promote`.
- Root `AGENTS.md` documents a Maintainer contract and does not load the
  gateway rulebook.
- Suite green; `ruff` clean; `compileall` clean; `suite_report` no drift.
- `npx skills add . --list` still shows exactly the `skills/` folders (the
  dogfood model's removal changes nothing about what ships).

## 7. Progress

**Shape 2 implemented; all gates green (276 tests, 2 skipped; `ruff` clean;
`compileall` clean; `suite_report` no drift; product `setup`/`--check` smoke
tested into a temp target).**

- Deleted the 7 consumer-skill mirrors, the mirrored runtime
  (`.agents/scripts/devagent/`), `.agents/.promoted.json`, `.agents/MAP.md`,
  `.agents/rules/`, `.agents/agents/`, root `.cursorrules` / `.windsurfrules`,
  `tools/promote.py`, and `tests/test_promote.py`.
- `.agents/skills/` now holds only `author-skill` (rewritten, no promote
  handoff) + vendored `skill-creator`.
- Root `AGENTS.md`: single-tree wording, commands without promote, a new
  "Do not reintroduce the dogfood layer" hard rule, and a **Maintainer
  contract** replacing the "DEV AGENT" gateway section.
- `README.md`, `docs/README.md`, `pyproject.toml` comment updated; `docs/_topics.md`
  regenerated (no change).
- Tests: `test_no_leak` docstring; `test_shipping_paths` drops `promote`;
  `tests/.suite-baseline.json` refreshed.

### Deviations from the written tasks

- **`docs/overview.md` Decision Log entry: skipped.** `overview.md` documents the
  *framework* in a consumer repo (its directory map is `<repository-root>/` =
  a consumer install); the dogfood removal is a maintainer-repo decision, so it
  lives in `AGENTS.md`'s Maintainer contract, not a framework topic doc.
- **`tests/test_drift_phases.py` was added to scope.** It read the deleted
  mirror at `.agents/skills/phase-protocol/references/drafted.md` (and scanned
  `.agents/` / `.agents/rules/`). Repointed to the canonical `skills/` product:
  `_product_sources()` scans `skills/`, the drafted.md path and the shipped-doc
  scan now use `skills/`, and the canonical build command matches `AGENTS.md`
  (`compileall -q skills tools tests`).
- **Consumer-path references kept on purpose.** Shipped skills and `docs/` still
  say `.agents/skills/<name>/...`, `.agents/scripts/devagent/main.py`, and
  `.agents/rules/dev-agent-framework.md` — those describe the *consumer* install
  layout the `dev-agent` skill creates, not this repo. `test_shipping_paths`
  still allows `.agents/...`.
- `specs/`, `BACKLOG.md`, `tests/TEST-PLAN.md`, `PLAN.md`, and Decision-Log
  history are intentionally left untouched (resolved/historical).
