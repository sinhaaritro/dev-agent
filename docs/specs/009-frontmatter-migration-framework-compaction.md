tags: [frontmatter, migration, sdsc]

# 009: Frontmatter Migration & Framework Compaction

Status: APPROVED
Phase: 3-Review
Handoff: 2026-08-19

## 1. Goal & Context

Migrate all six core skills to the new minimal SKILL.md frontmatter contract
(`name`, `description`, `tags` required; `version` + `author` moved under a nested
`metadata` block; `scope` optional with an on-demand default), fix the stale prose
references that still cite the old flat fields, and compact the framework markdown
(Tier 1 prose tightening + Tier 2 on-demand phase-reference loading) to cut per-session
framework token load by ~35-40% with zero behavioral change. `skill-creator` is
out of scope and untouched; approved specs 001-006 stay byte-identical except a
superseded note on 002/003/004; the `docs/temp` gitignore topic is explicitly dropped.

## 2. Architectural Decisions & Trade-offs

- D1 - Frontmatter contract. Required: `name`, `description`, `tags`, `metadata`
  (nested, carrying `version` + `author`). Optional: `scope` (`always` only for
  auto-router and phase-protocol; omitted elsewhere, on-demand default applies).
  Alternatives: flat `metadata.version` keys (rejected: non-standard YAML, hard to
  read); dropping `metadata` entirely (rejected by the human: version/author are
  kept, just relocated). Trade-off: `generate_map.py` must learn to parse one level
  of nesting; the parser stays stdlib-only and ~10 lines bigger.
- D2 - Engine backward compatibility. `parse_front_matter()` tolerates legacy flat
  `version:`/`author:` lines (parses them into the dict, renders nothing) and keeps
  the existing `scope` default of `on-demand` (generate_map.py line 177 unchanged).
  Trade-off: two shapes accepted during migration; the SKILL.md docs declare only the
  nested shape canonical so drift is one-directional toward it.
- D3 - Compaction scope and protection list. Tier 1 rewrites in place, same headings,
  same meaning: system.md, the six core SKILL.md files, phase-protocol references
  (plan/build/handoff/review/harness), spec-builder templates (implementation-plan,
  adr-template, todo-checklist-format), auto-router lane-matrix. Tier 2 adds one
  load-on-phase-start line to phase-protocol SKILL.md and one clause to system.md so
  only the active phase's reference is loaded. Hard-protected, byte-identical:
  every engine command line/flag/exit-code value, the 5-tag STATUS header, the
  4-block response schema, system.md section 3 guardrails, escalation rules, lane
  criteria, and all spec/ADR/handoff/verify-state contracts (file names, Status:/
  Phase:/Handoff: headers, append-only rules). Trade-off: compaction is judged by
  diff review of the protected list, not by an automated contract test.
- D4 - Records vs live files. Approved specs and ADRs are protected records
  (system.md section 3): they describe what was built. Only 002/003/004 get a single
  `Superseded:` line at the top because their unchecked TODOs still prescribe the old
  flat `version:`/`author:` format; re-running those steps would otherwise re-add the
  fields. Everything else in docs/specs/ and docs/decisions/ is byte-identical.
- D5 - skill-creator stays untouched. The user ruled the whole `.agents/skills/
  skill-creator/` directory out of scope, including the pre-existing
  `quick_validate.py` ALLOWED_PROPERTIES mismatch. Consequence: `quick_validate.py`
  will keep rejecting the new `metadata` key (and `tags`/`scope`); it is not run as
  part of this task's verification and is not fixed here.
- D6 - Verification. No build system exists for this repo; verification is a three-
  command suite: (a) generate_map.py --force rebuilds a MAP.md whose rows and Active
  Conditions are identical to the pre-change index; (b) a python one-liner asserts
  every core SKILL.md's parsed frontmatter matches the canonical contract and legacy
  flat lines still parse (engine smoke); (c) resolve_gate.py exit-code matrix
  (0/1/2 across interactive/non-interactive x blocking/non-blocking) re-confirmed
  against the engine, which must be untouched by compaction.

## 3. Affected Files & Scope

- Modified: .agents/skills/map-generator/scripts/generate_map.py
- Modified: .agents/skills/map-generator/SKILL.md
- Modified: .agents/skills/auto-router/SKILL.md
- Modified: .agents/skills/phase-protocol/SKILL.md
- Modified: .agents/skills/spec-builder/SKILL.md
- Modified: .agents/skills/task-cleaner/SKILL.md
- Modified: .agents/skills/verification-runner/SKILL.md
- Modified: .agents/rules/system.md
- Modified: .agents/skills/auto-router/references/lane-matrix.md
- Modified: .agents/skills/phase-protocol/references/plan.md
- Modified: .agents/skills/phase-protocol/references/build.md
- Modified: .agents/skills/phase-protocol/references/handoff.md
- Modified: .agents/skills/phase-protocol/references/review.md
- Modified: .agents/skills/phase-protocol/references/harness.md
- Modified: .agents/skills/spec-builder/references/implementation-plan-template.md
- Modified: .agents/skills/spec-builder/references/adr-template.md
- Modified: .agents/skills/spec-builder/references/todo-checklist-format.md
- Modified: docs/specs/002-auto-router-core-skill.md (superseded note only)
- Modified: docs/specs/003-phase-protocol-core-skill.md (superseded note only)
- Modified: docs/specs/004-spec-builder-core-skill.md (superseded note only)
- Deleted: none
- Untouched (out of scope): .agents/skills/skill-creator/**, docs/specs/001, 005, 006,
  007, 008, docs/decisions/**, docs/architecture/**, docs/temp/.gitignore

## 4. Actionable TODO Checklist

- [x] Step 1: Extend generate_map.py parse_front_matter() with a nested-block case
       (empty-valued key + indented sub-keys -> dict); keep legacy flat tolerance;
       run the script once to confirm MAP.md regenerates unchanged in shape.
- [x] Step 2: Migrate frontmatter on all six core skills - add metadata (version,
       author) everywhere, scope: always on auto-router + phase-protocol, none on
       the other four; map-generator gets its existing version/author moved under
       metadata and its scope line dropped.
- [x] Step 3: Update live prose - system.md section 1 reworded for the new default,
       map-generator SKILL.md line 47 canonical-format sentence, and any line that
       still describes the old flat fields; confirm auto-router/phase-protocol
       "(scope: always)" claims are now true.
- [x] Step 4: Compact Tier 1 - rewrite system.md, the six core SKILL.md files, the
       five phase-protocol references, the three spec-builder templates, and
       lane-matrix.md in place under the hard-protection list; capture before/after
       line counts.
- [x] Step 5: Apply Tier 2 - add the load-on-phase-start line to phase-protocol
       SKILL.md and the matching clause to system.md section 2 step 3.
- [x] Step 6: Add the one-line Superseded note to docs/specs/002, 003, 004 and verify
       docs/specs and docs/decisions contain no further diffs.
- [x] Step 7: Verify - MAP regeneration diff clean (Step 7a), frontmatter contract
       smoke test passes (Step 7b), resolve_gate.py exit matrix unchanged (Step 7c),
       via verification-runner ledger under task FM-MIG (7a+7b green, ledger attempt 1).
- [x] Step 8: Finalize - all 7 TODOs closed, header to `Phase: 3-Review`, hand the
       finalized spec to review (spec 008 two-step: promotion happened at approval,
       review only finalizes).

## 5. Verification Commands

(No repository build system exists; these are the canonical suite. In the build
session they run through `verify.py run --task FM-MIG`, per spec 005.)

- MAP Command: python .agents/skills/map-generator/scripts/generate_map.py --force && python - <<'EOF'
text = open('.agents/MAP.md').read()
for row in ['**map-generator**', '**auto-router**', '**phase-protocol**', '**spec-builder**', '**task-cleaner**', '**verification-runner**', '**skill-creator**']:
    assert row in text, f'{row} row missing'
assert '*Always active*' in text, 'auto-active condition missing'
assert 'Snapshot:' in text, 'snapshot line missing'
print('MAP OK')
EOF
- Test Command: python - <<'EOF'
import sys
sys.path.insert(0, '.agents/skills/map-generator/scripts')
from generate_map import parse_front_matter, find_root
root = find_root()
core = ['auto-router', 'phase-protocol', 'spec-builder', 'task-cleaner', 'verification-runner', 'map-generator']
for name in core:
    fm = parse_front_matter((root / '.agents/skills' / name / 'SKILL.md').read_text())
    assert fm.get('name') == name, f'{name}: name field'
    assert fm.get('description'), f'{name}: description field'
    assert fm.get('tags'), f'{name}: tags field'
    md = fm.get('metadata')
    assert isinstance(md, dict) and md.get('version') and md.get('author'), f'{name}: metadata block with version+author'
assert parse_front_matter((root / '.agents/skills' / 'auto-router' / 'SKILL.md').read_text()).get('scope') == 'always'
assert parse_front_matter((root / '.agents/skills' / 'phase-protocol' / 'SKILL.md').read_text()).get('scope') == 'always'
for name in ['spec-builder', 'task-cleaner', 'verification-runner', 'map-generator']:
    fm = parse_front_matter((root / '.agents/skills' / name / 'SKILL.md').read_text())
    assert 'scope' not in fm, f'{name}: scope must be omitted (on-demand default)'
# legacy tolerance: flat version/author still parse without breaking the dict
legacy = parse_front_matter('---\nname: x\ndescription: y\nversion: 1.0.0\nauthor: Z\ntags:\n  - a\n---\n')
assert legacy.get('version') == '1.0.0' and legacy.get('author') == 'Z' and legacy.get('tags') == ['a']
print('FRONTMATTER OK')
EOF
- Gate Command: python .agents/skills/phase-protocol/scripts/resolve_gate.py --gate blocking --session Interactive --lane A --question "q" --options "A (Recommended): a; B: b"; echo "exit=$?"
- Lint Command: none (no linter is configured for this repo)

## 6. Rollback Strategy

All edits are text-only and additive in intent; no data or dependency changes. On
circuit-breaker trip (3 consecutive verification failures): `git checkout -- .agents
docs` restores every pre-task file (the scratchpad draft-plan.md is gitignored and
unaffected), then file the escalation report. The promoted spec, the ADR, and the
MAP.md snapshot line remain as the durable record of what was attempted. AGENTS.md
is not modified by this task, so no template re-derivation is needed.

---
