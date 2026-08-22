tags: [circuit-breaker, core-skill, test-execution, verification-runner]

# 005: verification-runner — Fifth Core Skill (Test Execution & Circuit Breaker)

Status: APPROVED | Phase: 2-Build | Date: 2026-08-15

> **Derived from:** `docs/architecture/000-modular-agent-orchestration-v7.md` (master reference, approved, verbatim; §5.5: test execution & circuit breaker; §9: max 3 consecutive failed attempts, escalation.md, human handoff; §4 lane table: Lane B "Full circuit breaker (3-retry)", Lane A "Full circuit breaker + review phase", Lane C "Single pass; 3-fail escalates to Lane B"), `AGENTS.md` (`autonomy_level: supervised`), `.agents/rules/system.md` (behavioral contract, accepted; §2 step 4 is verification-runner's boot position, §4 already names "verification & circuit breaker in `verification-runner`"), `docs/specs/004-spec-builder-core-skill.md` (D1: plan §5 `- Build Command:` / `- Test Command:` lines are the verification source), and `.agents/skills/phase-protocol/references/build.md` (§2: "On failure, call `verification-runner`: max 3 consecutive failed attempts, then escalation.md + revert broken dirty edits + handoff").
> **Supersedes:** the untracked scaffold `.agents/skills/verification-runner/` (legacy frontmatter violating the 001 D4 contract - `type: core`, `trigger_tags`, no `version`/`author`, and a corrupted non-ASCII em-dash `�?` in the description; flat numbered sections; no engine). phase-protocol `build.md` already delegates circuit-breaker duty to this skill — this spec makes that forward contract real.
> This spec designed the framework's fifth core skill in full - verification engine with an enforced retry counter and escalation report generator, SKILL.md doc, framework references, and the system.md boot-chain edit. **Implemented and verified on 2026-08-15 (all §5 checks green).**

## 1. Goal & Context

The Modular Agent Orchestration framework requires a verification skill (000 §5.5) that executes the plan's verification commands, enforces the circuit breaker (000 §9: maximum **3 consecutive failed attempts**, then cease modifications, revert broken dirty edits, write `docs/temp/escalation.md` detailing attempts/error logs/hypothesis/remediation options, halt and request human handoff), and treats "blocked" as a valid terminal state - never a silent pass. The lane table (000 §4) makes the breaker mandatory for Lanes B and A and a 3-fail escalator for Lane C. Per `.agents/rules/system.md` §2, verification-runner is the second on-demand skill in step 4 of the boot chain (after spec-builder), loaded whenever a build step must be verified or the retry threshold is reached. phase-protocol's `build.md` already treats this skill as a forward contract: §2 mandates calling it on verification failure with the 3-attempt rule.

The current `.agents/skills/verification-runner/` scaffold is untracked and stale: its frontmatter uses legacy fields (`type: core`, `trigger_tags`, no `version`/`author`) violating the 001 D4 frontmatter contract, its description contains a corrupted em-dash (`�?`) that `map-generator` would sanitize, and its retry discipline ("Track consecutive failures per fix attempt") is judgment, not mechanics — a safety gap because an agent under pressure can lose count, reset the counter silently, or write a free-form escalation report. It is replaced in place by this spec's design.

## 2. Architectural Decisions & Trade-offs

**D1. `verify.py` engine — the retry counter is a persisted, engine-owned ledger.** The skill owns an assist engine: `.agents/skills/verification-runner/scripts/verify.py` (skill-local scripts per 001 D1; stdlib-only Python, styled after `promote_spec.py` / `resolve_gate.py` / `generate_map.py`; `find_root` via the `AGENTS.md` marker). The engine owns the counter: state lives in `docs/temp/verify-state.json` (gitignored scratchpad, per-session, purged by task-cleaner on acceptance - the counter is per-task by design), keyed by task ID, written on every outcome. Because state persists on disk, the 3-attempt limit survives across agent turns and cannot be silently reset by forgetting. Trade-off: a state file vs. agent judgment — justified because the counter is the framework's retry-limit guarantee (000 §9); a judgment-tracked counter is exactly the failure mode this skill exists to prevent. The engine is a ledger, never a judge: it records what the command actually returned.

**D2. The engine executes commands via subprocess.** `verify.py run --command "<cmd>" --task <id> [--timeout <s>]` runs the command with a 300s default timeout, captures stdout/stderr verbatim for the failure log, refuses interactive/TTY commands (a TTY check on the command string and an explicit `--interactive` ban), and maps the outcome: exit 0 -> green, counter reset to 0, print `PASS (attempt <n>)`; non-zero or timeout -> failure, counter incremented, print `FAIL (attempt <n>/3)`; counter at 3 -> exit 2, write `docs/temp/escalation.md` (D4), print `CIRCUIT BREAKER TRIPPED - escalation written, halt`. Trade-off: the engine runs arbitrary commands from a plan — justified because deterministic counting requires the engine to observe the real exit code; `--timeout` and the TTY ban keep it safe; harness-agnostic per 000 §13 (any harness can run `python ... verify.py run ...`).

**D3. Exit-code contract.** `0` green (counter reset); `1` failed (counter incremented, retry remaining); `2` circuit breaker tripped (escalation.md written, halt — no further modifications, per 000 §9); `3` command source unresolved (no plan §5 lines, no AGENTS.md Commands, no detectable manifest — the agent asks Socratically per the scaffold's rule, or applies the framework reference's default). The codes mirror `resolve_gate.py`'s precedent (0 proceed / 1 halt / 2 fail-closed): agents read the contract from stdout + exit code, never from prose alone.

**D4. `escalation.md` is engine-generated, template-enforced.** On the 3rd consecutive failure, `verify.py` writes `docs/temp/escalation.md` in a fixed structure: header (task ID, attempt count, date), `Attempts` (the captured failure logs, appended per attempt), `Hypothesis` (from `--hypothesis`), `Remediation Options` (guided A/B options with recommended default, from `--options "A (Recommended): ...; B: ..."` — the Socratic format from phase-protocol), and a `Handoff` line (halt, human required). The agent supplies hypothesis and options; the engine supplies the structure and the attempt logs verbatim. Trade-off: engine-formatted reports vs. agent-written prose — justified because the escalation report is the audit record for a halted task (000 §9); a consistent structure is what makes it reviewable, and verbatim logs make it truthful.

**D5. Framework expansion is selection-only references.** The generic workflow (counter, breaker, escalation) lives in SKILL.md; per-framework knowledge lives in `references/frameworks/<stack>.md`, loaded on demand after detection — the skill-creator "domain organization by variant" pattern (SKILL.md = workflow + selection; references = per-domain). `verify.py detect` reads repo manifests (`pyproject.toml` -> python-uv, `package.json` -> node-npm, `Cargo.toml` -> rust-cargo, `go.mod` -> go, `.csproj` -> dotnet) and prints the suggested framework page + canonical build/test/lint commands. Version 1 ships `python-uv.md` (dogfoods this repo: `python`, pytest, ruff) and `node-npm.md` (npm ci, jest/vitest) — two pages prove the pattern generalizes; more pages are added per project need, never speculatively. Trade-off: references are knowledge, not mechanics — the counter works identically on any stack because the engine only sees commands.

**D6. Command resolution order is deterministic.** `run` resolves its command: (1) explicit `--command` from the agent (who reads the plan's §5 `- Build Command:` / `- Test Command:` lines per 004 D1, or AGENTS.md Commands); (2) `--suggest` prints the framework reference's canonical commands without running (agent confirms Socratically); (3) no source -> exit 3. The plan's §5 is the primary source per phase-protocol `build.md` §1 ("Run the plan's verification commands (section 5 of the template) after each step"); AGENTS.md Commands is the project's documented contract; manifests are the fallback. Trade-off: the engine never invents commands — the agent decides what to run, the engine runs exactly what it is given; `--suggest` keeps the framework knowledge one step away from execution.

**D7. system.md §2 step 4 edit.** Step 4 gains the engine invocation line, mirroring the spec-builder edit pattern: verification runs via `python .agents/skills/verification-runner/scripts/verify.py run --command "<cmd>" --task <id>`; escalation is engine-written on attempt 3. Trade-off: one more explicit path in the behavioral contract — consistent with the step-2/3/4 precedent.

## 3. Affected Files & Scope

- Overwritten in place: `.agents/skills/verification-runner/SKILL.md` — skill doc (frontmatter per 001 D4 + standard body; overwrites the untracked scaffold in place, no git delete needed; the corrupted `�?` em-dash is fixed to ASCII `-`)
- Created: `.agents/skills/verification-runner/scripts/verify.py` — run/status/escalate/detect engine (D1–D4)
- Created: `.agents/skills/verification-runner/references/frameworks/python-uv.md` — uv/python canonical commands, single-test vs full-suite, venv pitfalls (D5)
- Created: `.agents/skills/verification-runner/references/frameworks/node-npm.md` — npm canonical commands, jest/vitest, lockfile mismatch (D5)
- Modified: `.agents/rules/system.md` — §2 step 4: verification-runner engine invocation (D7)
- Generated: `.agents/MAP.md` — regenerated (row `*Use when: <tags>*`; snapshot hash changes; index already committed)
- Created: `docs/specs/005-verification-runner-core-skill.md` — this spec
- Untouched: `AGENTS.md`, `docs/architecture/000-modular-agent-orchestration-v7.md`, `docs/specs/001/002/003/004`, `.agents/skills/map-generator|auto-router|phase-protocol|spec-builder/`, `docs/temp/`

## 4. Actionable TODO Checklist

- [x] Step 1: Create `.agents/skills/verification-runner/scripts/verify.py` — stdlib-only; `find_root` via the `AGENTS.md` marker; state at `<root>/docs/temp/verify-state.json` keyed by task; `run` mode (subprocess, 300s default timeout, TTY-ban, counter semantics per D1/D2, exit codes per D3, escalation.md generation per D4); `status` mode (read-only counter print); `escalate` mode (standalone escalation.md writer); `detect` mode (manifest scan -> framework page, D5); `--state-dir` override for testing (verification and evals never touch the real `docs/temp/`); ASCII output; BOM-safe reads.
- [x] Step 2: Create `.agents/skills/verification-runner/SKILL.md` — frontmatter per 001 D4 (no `type:`/`trigger_tags`; ASCII description); body per the standard structure (Overview, When to Use, Instructions, Output Contract, Notes); framework selection rule pointing at `references/frameworks/`.
- [x] Step 3: Create `references/frameworks/python-uv.md` and `references/frameworks/node-npm.md` per D5.
- [x] Step 4: Update `.agents/rules/system.md` §2 step 4 (verification-runner engine invocation) per D7.
- [x] Step 5: Regenerate `.agents/MAP.md` via `map-generator` (first `regenerated`, second `MAP.md is fresh`); verify the verification-runner row shows Active Condition `*Use when: <tags>*`.
- [x] Step 6: Verify engine behavior per §5 — green run resets counter, fail increments, breaker trips at 3 with escalation.md, unresolved exits 3, detect maps manifests; confirm `git status --short` shows only §3 files.

## 5. Verification Commands

All runs use fixture commands and a sandbox `--state-dir`; the real `docs/temp/` and the real test suite are never touched by verification.

- Green run: `verify.py run --command "python -c \"import sys; sys.exit(0)\"" --task t1 --state-dir <sandbox>` -> exit 0, `PASS (attempt 1)`; `status t1` -> `attempts: 0`
- Fail then pass: run an exit-1 fixture twice (attempts 1, 2), then the exit-0 fixture -> `PASS (attempt 3)`; `status` -> `attempts: 0` (green resets)
- Circuit breaker: three consecutive exit-1 runs -> attempts 1, 2, `CIRCUIT BREAKER TRIPPED` exit 2 on the third; `escalation.md` exists in `<root>/docs/temp/` with the captured failure logs, hypothesis, and remediation options; `status` -> `attempts: 3`
- Status persistence across invocations: `status` after each run reflects the ledger, not judgment
- Unresolved: `run` with no `--command` and no suggestions -> exit 3
- Detect: a sandbox dir containing `pyproject.toml` -> `python-uv`; containing `package.json` -> `node-npm`
- MAP.md idempotency: `generate_map.py` twice -> `regenerated`, then `MAP.md is fresh`; verification-runner row `*Use when: ...*`
- Visual: `system.md` §2 step 4 includes the verification-runner engine path
- `git status --short` shows only §3 files

## 6. Rollback Strategy

- Delete `.agents/skills/verification-runner/scripts/` (`verify.py`) and `references/frameworks/`.
- `git checkout .agents/rules/system.md` reverts the §2 step 4 edit.
- `git checkout .agents/MAP.md` restores the committed index; regenerable by map-generator at any time.
- Delete `docs/specs/005-verification-runner-core-skill.md`.
- The superseded scaffold was uncommitted (untracked) — no git copy exists; its content is fully covered by 000 §§5/9 and this spec, so recreation from history is unnecessary.
- No verification or eval run ever writes into the real `docs/temp/` state file (sandbox `--state-dir` only), so no ledger state requires rollback.