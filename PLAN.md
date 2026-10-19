# Dev Agent — Shared Runtime Refactor Plan

> **Status:** Proposed (not started)
> **Scope:** Restructure the shipped framework so all engine code lives in one
> shared runtime package per consumer project, the wrapper skills become thin,
> and install/update/global-install behave deterministically.
> **Note:** This is a plain working plan. It intentionally does **not** use the
> repo's `specs/` phase lifecycle.

---

## 1. Goal

Today each shipped skill carries its own copy of a stdlib Python engine, and
`find_root`, hashing, frontmatter parsing, and other helpers are copy-pasted
across 7 scripts (~4,600 LOC). That duplication blocks DRY/SOLID and has already
produced drift bugs (e.g. `ISSUES.md`: `_fingerprint` vs `command_fingerprint`).

We will instead:

- ship **one shared runtime package** per consumer project,
- keep the skills as **thin wrappers** (SKILL.md + references only) that call the
  runtime,
- make **one skill (`dev-agent`)** the installer that seeds the runtime, the
  rulebook/AGENTS/coder files, and (opt-in) the other skills,
- make **global installs work** by never depending on where the skill folder lives.

Precedent: this is the BMAD v6/v7 model (many skills, one `_bmad/` runtime, a
`setup` step).

---

## 2. Decisions (locked)

| # | Decision |
|---|----------|
| D1 | One runtime package installed at `<repo>/.agents/scripts/devagent/`. |
| D2 | `bootstrap` is renamed **`dev-agent`** and becomes the framework skill: it bundles the runtime, the seed files, and the installer. |
| D3 | The other 6 skills (`auto-router`, `map-generator`, `phase-protocol`, `spec-builder`, `task-cleaner`, `verification-runner`) become wrappers with no `scripts/`. |
| D4 | Invocation is by path: `python .agents/scripts/devagent/main.py <cmd>`. Added to the harness's always-allow execution list. |
| D5 | Manifest at `.agents/.devagent.json`, **runtime-only** (no per-skill version snapshot). |
| D6 | `setup` reconciles the runtime; `--check` is read-only; `--update` is explicit; setup never downgrades. |
| D7 | Skill install is **opt-in**: `setup --skills mandatory\|all\|<list>`, delegating to `npx skills add`. Plain `setup` is stdlib-only and offline. |
| D8 | Runtime discovery walks up from **CWD** for `.agents/.devagent.json`; the script-location fallback is removed for the runtime. |
| D9 | Install scope (`project` / `global`) and agent are recorded in the manifest. |
| D10 | A future `worktree` engine ships as an **optional, lazily-imported** command. |

### Rationale notes

- **D5 (runtime-only manifest):** the manifest is per-project, but with a global
  install the wrapper skills live outside the project. A per-project skill
  snapshot either can't see them or must reach into the global dir, which
  reintroduces the path coupling we are removing. Skill versions already live in
  the skills CLI (`npx skills list`, `skills-lock.json`). Compatibility is
  enforced from the skill side via a `requires_runtime` frontmatter field and an
  engine preflight.
- **D7 (opt-in skills):** `setup` may be invoked unattended (session-start
  freshness). It must therefore never prompt and never do a network install on
  its own. The agent renders the choice (checkbox menu); the script takes a list.

---

## 3. Target repository layout

This repo (the framework source):

```
skills/
  dev-agent/                      # was `bootstrap` — the framework skill
    SKILL.md                      # setup + install/update policy + skill menu
    reference/                    # AGENTS.md, rules/, agents/coder.md, dotfiles (unchanged)
    runtime/
      devagent/                   # CANONICAL runtime package (source of truth)
        __init__.py
        main.py                   # path launcher + argparse dispatch + preflight
        common/                   # shared helpers (dedupe target)
          __init__.py
          root.py                 # find_root (project), find_runtime
          hashing.py              # normalize_bytes, sha256, cache-skip
          frontmatter.py          # frontmatter parse/serialize
          text.py                 # sanitize_ascii, section parsing
          specparse.py            # spec/task/status parsing shared by specs+verify
        routing.py                # was auto-router/scripts/match_skills.py
        map.py                    # was map-generator/scripts/generate_map.py
        gates.py                  # was phase-protocol/scripts/resolve_gate.py
        specs.py                  # was spec-builder/scripts/promote_spec.py
        verify.py                 # was verification-runner/scripts/verify.py
        clean.py                  # was task-cleaner/scripts/clean.py
        worktree.py               # optional, lazy (not yet implemented)
    scripts/
      bootstrap.py                # installer: reference/ + runtime/ + manifest + --skills
  auto-router/                    # wrappers: SKILL.md + references only
  map-generator/
  phase-protocol/
  spec-builder/
  task-cleaner/
  verification-runner/
```

A consumer project after `dev-agent setup`:

```
<repo>/
  AGENTS.md
  .cursorrules / .windsurfrules
  .agents/
    rules/dev-agent-framework.md        # seeded, points at the runtime
    agents/coder.md                     # seeded
    scripts/devagent/                   # INSTALLED runtime (committed)
    .devagent.json                      # manifest
    skills/                             # only if project-scope install
```

---

## 4. Manifest contract — `.agents/.devagent.json`

```json
{
  "schema": 1,
  "framework": "dev-agent",
  "runtime_version": "1.2.0",
  "python": ">=3.10",
  "scope": "project",
  "agent": "opencode",
  "installed_at": "2026-10-19T14:03:11Z",
  "source": { "channel": "skills", "installed_by": "skills/dev-agent", "skills_version": "1.2.0" },
  "files": {
    "devagent/__init__.py": "sha256:9f2c…",
    "devagent/main.py": "sha256:…",
    "devagent/common/root.py": "sha256:…"
  }
}
```

Rules:

- The **version comes from the dev-agent skill's bundled runtime** (a `VERSION`
  file or `devagent.__version__`), not from the consumer.
- Never hash `__pycache__` / `*.pyc` (same skip as `tools/promote.py`).
- Write the manifest **last**, after the runtime files, so an interrupted install
  is detectable.
- `.agents/scripts/` and `.agents/.devagent.json` are **committed** in the
  consumer repo (they are the runtime, not scratch).

### Command semantics

| Command | Writes | Behaviour |
|---|---|---|
| `setup` | reconciles | absent → install; same version + clean → no-op; same version + modified/missing → repair; newer packaged version → upgrade; packaged older than installed → **refuse, exit 2** |
| `--check` | no | report `ok` / `stale` / `modified` / `missing` / `orphan`; exit 1 on drift (CI guard, parallel to `promote --check`) |
| `--update` | yes | upgrade, write `*.bak` for user-modified files, remove orphans, apply `schema` migrations, write manifest last |
| `setup --skills mandatory\|all\|<list>` | yes | delegate to `npx skills add …`; opt-in; needs Node; see §6 |

---

## 5. Invocation contract

- Launcher: `python .agents/scripts/devagent/main.py <cmd> [args]`.
  `main.py` inserts its **parent-of-package** into `sys.path`, imports `devagent.*`,
  and dispatches. (`.agents` is not a valid Python identifier, so `python -m
  .agents.…` cannot work; the path launcher is the supported form.)
- Subcommand map (old engine → new command):

  | Old engine | New command |
  |---|---|
  | `auto-router/scripts/match_skills.py` | `route` |
  | `map-generator/scripts/generate_map.py` | `map` (incl. `sync-docs`, `--force`) |
  | `phase-protocol/scripts/resolve_gate.py` | `gate` |
  | `spec-builder/scripts/promote_spec.py` | `spec` (all subcommands) |
  | `verification-runner/scripts/verify.py` | `verify` |
  | `task-cleaner/scripts/clean.py` | `clean` |

- **Preflight** (every command): read `.agents/.devagent.json`; if missing → exit
  with `error: this project is not set up — run the dev-agent skill's setup`. If
  `runtime_version` is below the skill's `requires_runtime` → exit with the
  upgrade instruction. This is the guard that makes runtime/skill drift visible
  instead of an `ImportError`.
- Add the exact prefix `python .agents/scripts/devagent/main.py` to the harness
  always-allow list.

---

## 6. Installer (`scripts/bootstrap.py`, in the `dev-agent` skill)

Two independent jobs:

1. **`setup` (stdlib-only, offline, default).** Copies `reference/` seeds
   (AGENTS.md, .gitignore merge, rules, coder, dotfiles) and `runtime/devagent/`
   into the target, then writes `.agents/.devagent.json`. Atomic: copy to
   `.agents/scripts/.devagent.tmp/` → rename → manifest last.
2. **`setup --skills …` (needs `npx`).** Reads a descriptor bundled with the
   skill:

   ```json
   {
     "source": "github/sinhaaritro/dev-agent",
     "mandatory": ["auto-router","map-generator","phase-protocol",
                   "spec-builder","task-cleaner","verification-runner"],
     "optional": []
   }
   ```

   Delegates to `npx skills add <source> --skill <x> --skill <y> … -y` (never
   copies skill folders itself). Detection/idempotency via `npx skills list`.
   Passes scope through (`-g`, `-a <agent>`) to match the manifest's `scope`.
   If `npx` is missing → install the runtime, print the manual command, exit 0.
   Partial failure (offline) → report per-skill status, exit non-zero if a
   mandatory skill failed; never claim "framework ready".

- Self-bootstrap guard stays for the runtime/rules install. The repo's own
  workspace install is handled separately (see §9).
- Keep the existing dry-run + per-file report style.

---

## 7. Global install — the fix

Problem today: with `npx skills add … -g`, skill folders live in
`~/.config/opencode/skills/`, but the seeded rulebook hardcodes
`.agents/skills/<name>/scripts/*.py`, so every command is dead.

Fixes:

1. **Route all engine calls through the runtime** (`.agents/scripts/devagent/main.py`),
   which is project-relative and scope-independent.
2. **Runtime discovery = CWD walk-up** for `.agents/.devagent.json`; remove the
   `Path(__file__).resolve().parent` fallback for the runtime (keep AGENTS.md
   CWD-first for project root).
3. **Setup is the only skill-relative command**, and it lives **only** in the
   `dev-agent` SKILL.md as `python <this-skill>/scripts/bootstrap.py setup
   --target .`. It must never appear in the seeded rulebook (first install is
   user-initiated, not a session-start step).
4. **Record `scope`/`agent`** so `setup --skills` matches the install scope and
   duplicate installs are detectable.
5. A global skill copy serves many projects; each project runs `setup` once.

---

## 8. Task breakdown

> Suggested order; each task should end in a green `python -m unittest discover
> -s tests` (adjusting tests as it goes).

**T1 — Package skeleton + common helpers.**
Create `skills/dev-agent/runtime/devagent/` with `__init__.py`, `main.py`, and
`common/` (`root.py`, `hashing.py`, `frontmatter.py`, `text.py`, `specparse.py`).
Move the duplicated helpers here: `find_root` (one copy), `find_runtime`,
`normalize_bytes`, sha256 hashing with cache-skip, frontmatter parse/serialize,
`sanitize_ascii`, spec/status/section parsing shared by `specs` + `verify`.

**T2 — Move engines into the package.**
Relocate each engine to its module (`routing.py`, `map.py`, `gates.py`,
`specs.py`, `verify.py`, `clean.py`); replace the inlined duplicates with
`common.*`. Behaviour-preserving move first, dedupe second.

**T3 — `main.py` dispatch + preflight.**
Argparse subcommands per §5; `sys.path` shim; runtime preflight; preserve exit
codes; lazy `worktree` registration (hidden when absent).

**T4 — Rename `bootstrap` → `dev-agent`.**
`git mv skills/bootstrap skills/dev-agent`; update SKILL.md (setup policy,
`--skills` menu, global note); keep `reference/`; rewrite `scripts/bootstrap.py`
for the setup/`--check`/`--update`/`--skills` contract and atomic install.

**T5 — Manifest.**
Implement write/read/compare per §4, including never-downgrade (exit 2) and
cache-skip.

**T6 — `--skills` installer.**
Descriptor + `npx` delegation, scope passthrough, idempotency, dry-run, partial
failure reporting, graceful no-`npx` path.

**T7 — Global fixes.**
Remove runtime script-location fallback; add `find_runtime`; make the rulebook
use only the runtime path; keep setup skill-relative in SKILL.md only.

**T8 — Rewrite paths across surfaces.**
- `.agents/rules/dev-agent-framework.md` **and** its seed
  `skills/dev-agent/reference/rules/dev-agent-framework.md`.
- 6 wrapper `SKILL.md` files + their `references/*.md`.
- `docs/*.md` and the `docs/_topics.md` generator inside `map.py`.
- `tests/fixtures/behavior/cases/*` (paths in prompts/expectations).
- `skills.sh.json` (rename grouping + repo command string), `README.md`,
  `AGENTS.md`.

**T9 — Tests.**
- Migrate the ~10 files that load engines via `importlib.spec_from_file_location`
  (`test_promote_spec`, `test_verify`, `test_clean`, `test_generate_map`,
  `test_resolve_gate`, `test_gate_labels`, `test_drift_phases`,
  `test_approval_integration`, …) to import the **canonical** package from
  `skills/dev-agent/runtime/`.
- New tests: dispatch contract; manifest setup/`--check`/`--update`/
  never-downgrade; preflight version mismatch; CWD-walk-up runtime resolution;
  atomicity (interrupted install detectable); `--skills` idempotency/no-`npx`.
- Update `test_bootstrap`, `test_no_leak`, `test_shipping_set`,
  `test_shipping_paths` for the rename and new path shapes.
- Extend `tools/promote.py --check` to cover the runtime (see T10).

**T10 — Mirror + dogfood.**
`tools/promote.py` mirrors `skills/dev-agent/` (incl. `runtime/`) into
`.agents/skills/dev-agent/`; add the runtime to its `--check`. The repo's own
`.agents/scripts/devagent/` (needed so the local rulebook is truthful) is written
by a maintainer path — either relax the self-bootstrap guard for a
`--self` target or have `promote` write it. Add a drift guard so the local
runtime can't rot.

**T11 — Docs.**
Update `README.md`, `AGENTS.md` (maintainer briefing, repo map, commands),
`docs/README.md` and affected topic docs; regenerate `docs/_topics.md`.

---

## 9. Risks / watch-items

- **Rename blast radius.** `bootstrap` appears in `skills.sh.json`, README,
  AGENTS.md, docs, `tests/test_bootstrap.py`, the behavior fixture
  `b8-3-bootstrap-confirms-policy`, and `.agents/.promoted.json`. Mechanical but
  broad — do it as its own task (T4/T8).
- **Two update channels.** `npx skills update` (skills) vs `setup --update`
  (runtime). Detection = manifest + preflight; resolution = re-run setup. Make
  `setup` cheap/idempotent so the rulebook can call it at session start.
- **Node dependency at install time only.** Runtime install stays stdlib-only;
  only `--skills` needs `npx`. Must degrade gracefully.
- **Scope mismatch → duplicate commands.** Mitigated by `scope`/`agent` in the
  manifest and passing them through to `npx`.
- **Interpreter drift.** Manifest records `python: >=3.10`; setup warns before
  the first `X | Y` failure in a consumer project.
- **`doctor` must learn the new layout.** Import `devagent.main` and verify
  manifest hashes, not just glob syntax-check scripts.
- **Fork safety.** The baked-in `source` repo id is correct until someone forks;
  document that it is editable.

---

## 10. Definition of done

- `python .agents/scripts/devagent/main.py <cmd>` runs every engine from the
  installed runtime; no rulebook/SKILL.md path points at
  `.agents/skills/*/scripts/*.py`.
- `dev-agent setup` installs runtime + seeds + manifest, is idempotent, atomic,
  and never downgrades; `--check` is a clean CI guard; `--update` reconciles.
- `setup --skills mandatory` installs the 6 wrappers in the recorded scope;
  degrades cleanly without `npx`.
- A global skill install works end-to-end in a fresh project.
- Full suite green; `python tools/promote.py --check` clean; `python -m ruff
  check skills tools tests` clean.

## 11. Progress

**T1-T3 done (suite green: 265 tests, 2 skipped; ruff/compileall/promote --check clean).**

- Created `skills/dev-agent/runtime/devagent/` (`__init__.py`, `main.py`,
  `cli.py`) with `common/` (`root.py`, `text.py`, `frontmatter.py`).
- Moved all six engines in: `routing.py`, `mapgen.py`, `gates.py`, `specs.py`,
  `verify.py`, `clean.py`. Deduped the verbatim copies of `find_root` (was 6x),
  `sanitize_ascii` (2x), and `parse_front_matter` (2x) into `common.*`.
- `main.py` is the path launcher; `cli.py` owns command dispatch + the runtime
  preflight. `verify.py`'s `AGENT_SCRIPT_GLOBS` now also syntax-checks
  `.agents/scripts/devagent/**/*.py`.
- Deviations from the written plan, and why:
  - Engine module is `mapgen.py`, not `map.py` (avoids shadowing the `map`
    builtin). Command name is still `map`.
  - Dispatch lives in `cli.py`; `main.py` stays a thin path launcher.
  - Modules import shared helpers as `from common.<mod> import ...` (top-level
    sibling), so a module still runs standalone by path. Tests put the runtime
    dir on `sys.path`; `main.py` adds its own dir.
  - Preflight is **non-fatal when the manifest is absent** for now: it warns on
    stderr and continues, with an exemption when the tree is the framework's own
    source checkout (`skills/dev-agent/runtime/devagent` present). T5/T6 tighten
    it to a hard exit-2 once `setup` writes manifests.
  - Test sandboxes that drive `main.py` in a fake project now seed a minimal
    `.agents/.devagent.json`; `test_clean`/`test_verify` sandboxes that used to
    copy a single engine file no longer need to (they run the canonical module
    with `cwd` in the sandbox, which CWD-first `find_root` already handles).
- Still open in T2's "dedupe second" pass (deliberately deferred - the copies
  differ subtly): `parse_options`, `_is_noop_verify`, and the
  `_fingerprint`/`command_fingerprint` split called out in `ISSUES.md`.

**T4 done (suite green: 272 tests, 2 skipped; ruff/compileall/promote --check clean).**

- `skills/bootstrap/` renamed to `skills/dev-agent/` (SKILL.md, `reference/`,
  and `scripts/bootstrap.py` moved with history; the pre-existing
  `runtime/devagent/` is untouched). `.agents/skills/bootstrap` removed and
  `.agents/skills/dev-agent` installed by `promote`.
- `SKILL.md` rewritten: name `dev-agent`, new trigger surface, setup policy,
  `--check` / `--update` / `--skills` documented, and a "Global installs"
  section.
- `scripts/bootstrap.py` rewritten to the §6 installer contract:
  - `setup` (default command, `--target` defaults to `.`): seeds + bundled
    runtime staged in `.agents/scripts/.devagent.tmp/` then renamed, manifest
    written last. `--dry-run`, `--scope project|global`, `--agent`.
  - `--check`: read-only `ok` / `stale` / `modified` / `missing` / `orphan`,
    exit 1 on drift.
  - `--update`: repair + upgrade, backs up files the user modified (relative to
    the manifest) to `*.bak`, rewrites the manifest.
  - `--skills mandatory|all|<list>`: opt-in, delegates to `npx skills add`
    (never copies folders); graceful when `npx` is absent.
  - never-downgrade guard (packaged older than installed → exit 2).
- Bundled `skills/dev-agent/skills.json` descriptor (source + mandatory/optional).
- Manifest `.agents/.devagent.json` written with schema/framework/
  runtime_version/python/scope/agent/installed_at/source + per-file sha256.
- Rename surfaces kept green now: `skills.sh.json`, `.agents/.promoted.json`
  (via promote), `.agents/MAP.md` (regenerated), `tests/test_bootstrap.py`
  (rewritten to the new contract), `tests/test_consumer_rulebook.py`,
  `tools/behavior_eval.py` (`BOOTSTRAP_SCRIPT` + `setup` arg), and the
  `b8-3-...` fixture's `skills:dev-agent`.
- Note: T5/T6 behaviour (manifest read/compare, never-downgrade, `--check`,
  `--update`, `--skills`) landed in T4 because T4's own definition ("rewrite
  `bootstrap.py` for the setup/`--check`/`--update`/`--skills` contract") pulls
  it in; T5/T6 are now hardening/verification rather than net-new.
- Deferred to T7/T8 (per plan): the rulebook + all other paths still reference
  `.agents/skills/*/scripts/*.py` and `bootstrap`, and this repo has no
  `.agents/scripts/devagent/` yet (T10). Docs/AGENTS/README/rulebook text
  updates are intentionally not done here.

**T7+T8 done (suite green: 272 tests, 2 skipped; ruff/compileall/promote --check clean).**

- T7 (global fixes):
  - `common/root.py` gains `find_runtime()` - walks up from the CWD for
    `.agents/.devagent.json` and returns its path (or `None`); it deliberately
    does **not** consult the running script's location, so a globally installed
    skill resolves the project it is *run in*. `find_root()` keeps its CWD-first
    walk plus the script-location fallback for project-root resolution.
  - `cli.py` preflight now uses `find_runtime()`: a missing manifest hard-exits 2
    (unless the tree is the framework's own source checkout), and an installed
    `runtime_version` older than the running build (`devagent.__version__`, read
    from `__init__.py` without importing) hard-exits 2 with `setup --update`
    guidance. Manual sandbox check confirmed all three paths (missing / stale /
    current).
  - `setup` remains the only skill-relative command and appears only in the
    `dev-agent` SKILL.md (and the preflight error hint).
- T8 (path rewrite): every `.agents/skills/<name>/scripts/<engine>.py`
  invocation now reads `python .agents/scripts/devagent/main.py <cmd>` in the
  repo rulebook and its seed, the six wrapper `SKILL.md` files and their
  `references/*.md`, `docs/*.md`, `README.md`, and `AGENTS.md`. Engine docstrings
  and the `mapgen` generated banners/footers were rewritten too, and `verify.py`
  dropped the now-dead `.agents/skills/*/scripts/*.py` doctor glob.
  `docs/_topics.md` and `.agents/MAP.md` were regenerated (via promote + the
  runtime's `map`/`sync-docs`).
- Tests: `test_consumer_rulebook` (`spec specs-lint`) and `test_shipping_paths`
  (allowed-path sample) updated for the new path shapes.
- Deviations / notes:
  - `tests/fixtures/behavior/cases/*` carried no engine paths (T8 listed them,
    but there was nothing to rewrite); the `bootstrap` *setup-step keyword* in
    `tools/behavior_eval.py` is kept - it now drives the renamed
    `dev-agent/scripts/bootstrap.py`.
  - `specs/*` and `BACKLOG.md` still name the old engine files on purpose -
    `specs/` is disposable history and BACKLOG is resolved history; neither is a
    live surface.
  - `ENGINE_RELPATH` in `mapgen.py` was updated (not removed) to the runtime
    launcher path; it is currently unreferenced.

**T9+T10 done (suite green: 293 tests, 2 skipped; ruff/compileall clean; `promote --check` clean; `suite_report.py` no drift).**

- T9 (tests):
  - New `tests/test_runtime_cli.py`: the dispatch contract (help, no-args help,
    unknown command exits 2 *before* preflight, every mapped module importable,
    argv hand-through proven by `verify -h`); the runtime preflight (missing
    manifest → exit 2 + setup hint; stale `runtime_version` → exit 2 + update
    hint; current → proceeds and writes `MAP.md`); and `find_runtime` CWD-walk-up
    (nested CWD, nothing-above, default-to-CWD).
  - `tests/test_bootstrap.py` additions: atomicity (a leftover
    `.agents/scripts/.devagent.tmp/` is consumed by the rename; an interrupted
    install - manifest present, runtime dir gone - is detectable by `--check`),
    and the `--skills` contract (descriptor names the six wrappers;
    `_resolve_skill_names` for mandatory/all/list; a missing descriptor errors;
    no-`npx` is a graceful no-op that prints the manual `npx` command including
    `-g`/`-a`).
  - The ~10 engine-loading tests were already pointed at the canonical runtime
    package (T3); re-verified every `RUNTIME` is
    `skills/dev-agent/runtime/devagent`.
- T10 (mirror + dogfood):
  - `tools/promote.py` now also mirrors the installed runtime from
    `skills/dev-agent/runtime/devagent/` into `.agents/scripts/devagent/`
    (`RUNTIME_SRC`/`RUNTIME_DEST`), covered by `--dry-run`/`--check`/apply. Its
    report line is `ok|new|overwrite: .agents/scripts/devagent`.
  - Ran `promote`: the repo now has its own `.agents/scripts/devagent/`, so the
    local rulebook (`python .agents/scripts/devagent/main.py <cmd>`) is truthful
    and runnable in-repo (the source-tree preflight exemption means no manifest
    is required here).
  - Drift guard: `test_promote.RuntimeMirrorTest` asserts the local copy
    byte-matches the bundled source (caches excluded);
    `test_promote.RuntimeDriftGuardTest` proves `--check` catches runtime drift
    and `apply` repairs it; `LiveRepoTest` keeps the live `--check` clean.
- Baseline: `tests/.suite-baseline.json` was stale from the T4 rename (it still
  listed the pre-rewrite `test_bootstrap` names). Refreshed with
  `python tools/suite_report.py --update` (293 tests); `suite_report.py` now
  reports no drift.

**T11 (docs) done** (suite/ruff/compileall clean; `promote --check` clean;
`suite_report.py` no drift; 293 tests, 2 skipped).

- Swept every remaining bare engine-module reference in `docs/` **Current State**
  prose to the runtime command form: `verify.py` -> the runtime's `verify`
  command, `resolve_gate.py` -> `gate`, `promote_spec.py` -> `spec`,
  `match_skills.py` -> `route`, `generate_map.py` -> `map`. Decision-Log entries
  were deliberately left untouched (they are history). Touched `docs/README.md`
  (vocabulary + how-to-change), `overview.md`, `verification.md`, `lifecycle.md`,
  `decision-records.md`, `routing.md`, `flow.md`, `task-files.md`,
  `skill-discovery.md`.
- Recorded the refactor's architecture in `overview.md`'s previously-empty
  Decision Log: `OVERVIEW-D01` (one shared runtime behind thin skills),
  `OVERVIEW-D02` (a single installer owns the runtime + manifest; reconcile
  semantics), `OVERVIEW-D03` (scope-independent runtime discovery for global
  installs).
- `AGENTS.md` repo map + `tools/` blurb now name `.agents/scripts/devagent/` and
  promote's runtime mirror; `docs/README.md` "Where things live" gained the
  runtime row.
- Regenerated `docs/_topics.md` (`map sync-docs`) - only its header command line
  changed.
- Follow-up landed in the same pass (user-authorized): every bare engine name
  was removed from the *shipped* surfaces and the runtime's own usage text.
  `skills/*/SKILL.md` + `references/*.md` now show
  `python .agents/scripts/devagent/main.py <cmd>`; the runtime engines print
  `devagent <cmd>` in `-h` (added `prog=`) and in hints/escalation text; and the
  behavior harness's `map` setup step now runs the installed runtime instead of
  the deleted `map-generator/scripts/generate_map.py` (the b5-1 case expectation
  followed). `promote` re-mirrored; all gates held.
