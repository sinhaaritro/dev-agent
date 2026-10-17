# PLAN - `skills/` product tree with a hidden `.agents/skills/` dogfood mirror

Status: IN PROGRESS - W1-W8 done, next W9
Owner: framework maintainer
Related: `docs/002-skill-discovery-and-indexing.md`, `README.md`, `AGENTS.md`

---

## Progress

- W1 - DONE (commit 5114d4c): the 7 shipped skills moved to `skills/`; `.agents/skills/` now holds only `skill-creator`.
- W2 - DONE: `skill-creator` marked `metadata.internal: true`.
- W3 - DONE: `tools/promote.py` implemented; 7 skills mirrored into `.agents/skills/` with `internal: true` injected; `--check` detects drift.
- W4 - DONE: repo-only `promote` skill wraps the engine (commit 7b1146e).
- W5 - DONE: repo-only `author-skill` wraps `skill-creator` with repo overrides.
- W6 - DONE: root `AGENTS.md` rewritten as the maintainer briefing.
- W7 - DONE: `tests/test_promote.py`, `tests/test_no_leak.py`, `tests/test_shipping_set.py`.
- W8 - DONE: `.gitattributes` (LF for skills/mirror/tools), `.gitignore` `skill-workspaces/`, Guard CI workflow.
- W9 - TODO.

## 1. Problem

The AI that works on this repo gets confused about what the repo *is*. It cannot
reliably tell:

- whether it is **authoring the framework** or **consuming the framework**, and
- which files are the **deliverable** (shipped to users) versus the repo's own
  **workspace** (rules, specs, tooling).

Evidence already in the tree:

- Root `AGENTS.md` is a lightly filled copy of the **consumer** template
  (`bootstrap/reference/AGENTS.md`). Its "Repo map" lists `src/ - application
  source code`, which does not exist here. It describes a generic app repo.
- `.agents/rules/system.md` is the **consumer** behavioural contract ("You are an
  AI software development agent under the DEV Agent Orchestration protocol"), yet
  it always loads in the **source** repo with nothing stating "you are the
  author."
- `.agents/skills/` is simultaneously the shipped payload and the locally
  executed engine set, with nothing declaring which is which.
- Third-party `skill-creator` is committed under `.agents/skills/`. NOTE
  (corrected during W2): it was **not** actually shipping - the repo-root
  `skills-lock.json` entry for `skill-creator` suppresses it from discovery by
  name (verified with the CLI; see W9). It still needs the durable
  `metadata.internal: true` guard, because that lock is stale and is slated for
  reconciliation in W9.

## 2. Hard facts (verified with skills CLI v1.7.2)

The `skills` CLI (`vercel-labs/skills`) scans **both** `skills/` and
`.agents/skills/` as skill containers. Measured behaviour on a throwaway fixture:

| Fixture | CLI result |
| :--- | :--- |
| `skills/beta/SKILL.md` only | discovered / ships |
| `.agents/skills/gamma/SKILL.md` only, not internal | **discovered / ships** |
| same name in `skills/` and `.agents/skills/` | one entry; the `skills/` copy wins on install |
| `.agents/skills/secret` with `metadata.internal: true` | hidden by default; shown only with `INSTALL_INTERNAL_SKILLS=1` |

Consequences:

1. Committing `.agents/` does **not** stop `.agents/skills/` from shipping. It is a
   first-class discovery container.
2. The only native lever to stop a skill shipping is `metadata.internal: true`
   (soft hiding: a determined user can reveal it with
   `INSTALL_INTERNAL_SKILLS=1`, or surface non-container paths with
   `--full-depth`).
3. `skills.sh.json` controls only the repo *page* layout; it cannot exclude a
   skill from installs.

## 3. Decisions (locked)

- **Canonical direction:** `skills/` is the product and the single source of
  truth. `.agents/skills/` is derived (mirror) plus repo-only tooling. The
  derived copy can never leak because it is marked internal.
- **Hiding model:** soft hiding via `metadata.internal: true`, committed. This is
  acceptable; a hard "never public" guarantee would require not committing the
  skills at all, which is out of scope.
- **Repo-only tooling lives in `.agents/skills/`**, marked internal (no separate
  `tools/skills/` tree).
- **The promote engine is a plain script** (`tools/promote.py`), never a skill
  folder, so it can never become a root-container skill.

## 4. Target layout

```
dev-agent/
├── AGENTS.md                     # maintainer-facing: states the two-space model
├── skills/                       # PRODUCT (shipped). Source of truth.
│   ├── bootstrap/
│   ├── auto-router/
│   ├── map-generator/
│   ├── phase-protocol/
│   ├── spec-builder/
│   ├── task-cleaner/
│   └── verification-runner/
├── tools/
│   └── promote.py                # maintainer engine: skills/ -> .agents/skills/
└── .agents/                      # repo workspace; NEVER shipped
    ├── rules/system.md           # unchanged
    ├── agents/coder.md
    ├── .promoted.json            # manifest of skills owned by promote
    └── skills/                   # dogfood instance; EVERY SKILL.md internal:true
        ├── bootstrap/            #   mirrored (owned)
        ├── auto-router/          #   mirrored (owned)
        ├── ... (7 shipped)       #   mirrored (owned)
        ├── promote/              #   repo-only (internal, hand-maintained)
        ├── author-skill/         #   repo-only (internal, hand-maintained)
        └── skill-creator/        #   third-party (internal, committed)
```

Rules that fall out of this:

- User-facing install set == the top-level folders in `skills/`.
- Every `SKILL.md` under `.agents/skills/` MUST carry `metadata.internal: true`.
  This single invariant is what keeps the workspace private.
- `system.md` and `map-generator` keep reading `.agents/skills/` unchanged, so the
  repo still dogfoods a complete skill set.

## 5. Work items

### W1. Create `skills/` (move the shipped set) - DONE

Move the 7 shipped skill folders from `.agents/skills/` into `skills/`:
`bootstrap`, `auto-router`, `map-generator`, `phase-protocol`, `spec-builder`,
`task-cleaner`, `verification-runner`.

- Frontmatter in `skills/` stays clean: **no** `metadata.internal`.
- `skill-creator` does NOT move (it is third-party/repo-only).
- Line endings: ensure LF for all skill files (W8).

### W2. Mark every `.agents/skills/` skill internal - DONE

- For mirrored skills, W3 injects it.
- For repo-only / third-party (`promote`, `author-skill`, `skill-creator`),
  hand-add. `skill-creator`'s frontmatter currently has only `name` +
  `description`; add:
  ```yaml
  metadata:
    internal: true
  ```
- Add an invariant test (W7) that fails if any `.agents/skills/*/SKILL.md` lacks
  `internal: true`.

### W3. `tools/promote.py` - the mirror engine - DONE

Stdlib-only, no dependencies, mirroring the report vocabulary of
`bootstrap.py` (`new:` / `ok:` / `overwrite:` / `remove:`).

Interface:

```
python tools/promote.py apply       # reconcile .agents/skills/ from skills/
python tools/promote.py --dry-run   # print planned changes, write nothing
python tools/promote.py --check     # exit non-zero on any drift (CI)
```

Behaviour:

- **Ownership.** Owns exactly the top-level `skills/*` folders that contain a
  `SKILL.md`. Recorded in `.agents/.promoted.json`
  (`{"version": 1, "skills": ["auto-router", ...]}`).
- **Mirror, whole folder.** Copy each owned folder to `.agents/skills/<name>/`,
  including subfolders (`scripts/`, `references/`, `reference/`, etc.). Delete
  destination files that no longer exist in the source, so stale references do
  not linger.
- **Inject `internal: true`.** The ONLY transformed file is the destination
  `SKILL.md`: merge `internal: true` into the frontmatter `metadata:` map
  (create the block if absent). Everything else is copied byte-identical.
  Because the destination legitimately differs by this field, `--check` compares
  against the *expected derived* bytes, not the raw source bytes.
- **Never touch unmanaged names.** Any `.agents/skills/<name>` that is not an
  owned source name (`promote`, `author-skill`, `skill-creator`, third-party) is
  left alone and never deleted.
- **Collision guard.** If a source folder's name collides with an existing
  unmanaged `.agents/skills/<name>`, stop and report; do not overwrite.
- **Line endings.** Write LF; `--check` compares LF-normalised bytes.
- **Exit codes.** `apply`/`--dry-run` -> 0 on success; `--check` -> 0 clean,
  1 drift, 2 error.

### W4. `.agents/skills/promote/` - thin skill wrapper (internal) - DONE

A repo-only skill (internal) whose `SKILL.md` tells agents to run
`python tools/promote.py`. Triggers when skills change. Description should make
it the default action for "skills changed / sync the skills". Body: run
`--check`; on drift run `apply`, run the fixture install (W7), then tell the
human to start a new session.

### W5. `.agents/skills/author-skill/` - skill-creator override (internal) - DONE

Repo-only skill (internal) that claims any create/edit/fix/optimize of a skill in
this repo and takes precedence over `skill-creator`. It says: load
`skill-creator` for method, with these overrides:

- Author only in `skills/<name>/`; edit in place. Never author in `.agents/skills/`.
- Put eval workspaces in a gitignored `skill-workspaces/<name>/` (pass the path
  explicitly to skill-creator's scripts).
- Skip `.skill` packaging and the copy-to-`/tmp` step.
- Follow dev-agent conventions (frontmatter `name`/`description`/`tags`/
  `metadata`; optional `scope: always`).
- Finish by running `promote` (W4), then the fixture install.

Do NOT edit third-party `skill-creator` itself (updates would overwrite it).

### W6. `AGENTS.md` - identity rewrite (the core fix)

Rewrite the root `AGENTS.md` to be maintainer-facing:

- Add a short preamble: *this repo is the Dev Agent **framework source**; the
  deliverable is the skill folders under `skills/`, installed by users via
  `npx skills`; `.agents/` is the repo's own workspace and is never shipped; you
  are a maintainer, not a consumer.*
- Fix the "Repo map": remove the non-existent `src/`; describe `skills/`
  (product, shipped), `.agents/` (workspace, not shipped), `tools/`
  (maintainer engines), `specs/`, `docs/`, `tests/`.
- Add one hard rule: **skills are authored only in `skills/<name>/`, never in
  `.agents/skills/`** (`.agents/skills/` is generated/hand-held repo-only).
- Note that `bootstrap/reference/AGENTS.md` is the separate **consumer** template;
  the root file is *not* it.

### W7. Tests (stdlib `unittest`, matching `tests/`)

- `tests/test_promote.py`:
  - `--check` clean on a synced tree; drift after editing a `skills/` file;
    removal of a deleted source file; unmanaged folders untouched; collision
    guard.
  - `internal: true` is injected into derived `SKILL.md` and merged with an
    existing `metadata:` block (`version`/`author` preserved).
- `tests/test_no_leak.py` (the invariant): every `.agents/skills/*/SKILL.md`
  contains `internal: true`. Fast, deterministic, no network.
- Optional integration `tests/test_shipping_set.py`: run
  `npx skills add <repo> --list` and assert the visible set equals the `skills/`
  set; with `INSTALL_INTERNAL_SKILLS=1`, the repo-only set additionally appears.
  Skip when `npx`/network is unavailable.

### W8. Hygiene - DONE

- Add `.gitattributes` with `skills/** text eol=lf` (and `.agents/skills/**`) so
  `--check` does not false-positive across machines.
- `.gitignore`: add `skill-workspaces/`.
- CI job: `python tools/promote.py --check` + `tests/` (the "Guard" job).

### W9. Reconcile third-party bookkeeping

- `skills-lock.json` records `skill-creator` at `skills/skill-creator/SKILL.md`,
  which no longer matches its real location `.agents/skills/skill-creator`. The
  entry is currently **load-bearing**: it is what actually hides `skill-creator`
  from discovery today (a `skills-lock.json` entry suppresses a same-named
  skill even when `INSTALL_INTERNAL_SKILLS=1`). Decide whether to update the
  recorded path or drop the lock; either way keep `metadata.internal: true` as
  the durable guard. Document the choice in `AGENTS.md`.
- `skills.sh.json`: groups list 6 of the 7 shipped skills (`bootstrap` missing).
  Align the groupings with the real `skills/` set.
- `README.md`: update the Architecture tree and the install examples to describe
  `skills/` as the product and `.agents/` as non-shipped.

## 6. Migration sequence

1. W6 `AGENTS.md` rewrite (so the maintainer agent has the correct mental model
   before anything moves).
2. W1 create `skills/` by moving the 7 folders (git mv to preserve history).
3. W2 mark `promote` / `author-skill` / `skill-creator` internal.
4. W3 write `tools/promote.py`; run `apply` to rebuild `.agents/skills/` (now
   internal copies).
5. W4/W5 author the two repo-only skills.
6. W7 tests + W8 hygiene + W9 reconciliation.
7. Verify (section 7); commit on a spec branch.

## 7. Verification

- `python tools/promote.py --check` exits 0.
- `python tests` (unittest discover) all green, including the no-leak invariant.
- `npx skills add <repo> --list` shows exactly the `skills/` set (the 7). With
  `INSTALL_INTERNAL_SKILLS=1`, `promote`, `author-skill`, `skill-creator` appear.
- `python .agents/skills/map-generator/scripts/generate_map.py` reports
  `regenerated` once, then `MAP.md is fresh`; `MAP.md` lists the full dogfood set.
- `python .agents/skills/bootstrap/scripts/bootstrap.py --target <tmp> --dry-run`
  still works (bootstrap ships from `skills/`, but its engine is unchanged).
- `python -m compileall -q .agents skills tools tests` clean; ruff clean.

## 8. Risks / notes

- **Leak by omission.** `.agents/skills/` ships unless every `SKILL.md` there is
  internal. Mitigated by the W7 invariant test + `promote` injection, not by
  memory.
- **Soft hiding only.** `INSTALL_INTERNAL_SKILLS=1` reveals repo-only skills;
  `--full-depth` can surface non-container paths. Accepted.
- **Duplicate names are safe** (`skills/` wins; internal copies are not even
  candidates) but require identical names across both trees; `promote` enforces
  that by owning the name list.
- **Root-container trap.** Never leave a `SKILL.md` at the repo root; keep the
  promote engine as `tools/promote.py` (a plain script).
- **Third-party drift.** Hand-editing `skill-creator` (to add `internal`) will be
  lost if it is ever updated via the CLI. Accepted; `author-skill` wraps it
  rather than editing it.

## 9. Out of scope

- Hard (cryptographic) prevention of repo-only skills being revealed.
- Repointing `system.md`/`map-generator` at `skills/` (the mirror keeps the
  existing paths valid).
- Changing skill behaviour, engines, or the lifecycle.
