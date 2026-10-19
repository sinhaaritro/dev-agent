#!/usr/bin/env python3
"""Behavior/E2E harness: run prompt-level framework cases against a real install.

A behavior case is the same `case.json` + `repo/` contract as a skill-creator
case, so the two tools share one mental model:

    tests/fixtures/behavior/cases/<case>/case.json
    tests/fixtures/behavior/cases/<case>/repo/          # optional override
    tests/fixtures/behavior/profiles/<profile>/repo/    # shared starting state

`setup` performs the real install path (bootstrap + local skill copy) so the
prompt runs against a framework-installed tree, never a hand-made one.
Workspaces are throwaway and live OUTSIDE this repo by default (a consumer repo
is never nested inside the framework source tree, and `bootstrap.py` rightly
refuses to install into its own source tree):

    <tmp>/dev-agent-behavior-workspaces/<case>/<run-id>/repo/
    <tmp>/dev-agent-behavior-workspaces/<case>/<run-id>/transcript.md
    <tmp>/dev-agent-behavior-workspaces/<case>/<run-id>/result.json

Artifacts are a tiny machine-checkable DSL (scope defaults to `repo`):

    exists:repo:src/app.js          a path or glob has a match
    missing:repo:specs/             a path or glob has no match
    contains:repo:docs/README.md:X  a file contains the text
    not-contains:run:transcript.md:specs/
    contains:run:transcript.md:[STATUS:   (run: = the config dir)

Each case can run in three configurations, like skill-creator's eval loop:

    new_skill      the current `skills/<name>` (the version under test)
    old_skill      the previous version (exported from git HEAD, or a
                   --old-skills-dir snapshot) - the A/B baseline
    without_skill  the raw repo, no framework installed

A case is either a single `prompt` or a **scenario**: a list of `steps`
(`{id, prompt, expectations, expected_artifacts}`). A scenario installs one repo
per config and runs each step as an independent request against a freshly reset
copy of that repo, so M prompts cost `configs` installs instead of `M x configs`.
Every step is graded on its own (N checks) and gets its own review page.

`batch` runs many predefined prompts into ONE review: every prompt gets its own
eval page, configs of the same prompt sit side by side, and the vendored
benchmark aggregator adds the Benchmark (summary) tab. `check` grades one run;
`batch` does init -> run -> grade -> review for N prompts.

`check`/`batch` write `review.html` with the vendored skill-creator viewer. Open
the trusted copy under `.behavior-review/`, read the answers, and click "Submit
All Reviews" to download `feedback.json`; save it at `<run>/feedback.json` and
run `feedback` to turn it into a revision digest.

`accept` records a checked run as the case's baseline under
`tests/fixtures/behavior/baselines/<case>.json`, pinning the hashes of the
skills under test and the case fixture. `baseline` re-hashes those offline, so a
skill edit after `accept` shows up as drift until the case is re-run and
re-accepted.

Usage:
    python tools/behavior_eval.py list --skill spec-builder
    python tools/behavior_eval.py init --case b2-1-four-lanes --config compare
    python tools/behavior_eval.py run  --case b2-1-four-lanes --run-id <id> --config compare
    python tools/behavior_eval.py check --case b2-1-four-lanes --run-id <id>
    python tools/behavior_eval.py accept --case b2-1-four-lanes --run-id <id>
    python tools/behavior_eval.py baseline [--strict]
    python tools/behavior_eval.py batch --run-id <id> --skill auto-router
    python tools/behavior_eval.py feedback --run-dir <batch-dir>

`run` drives OpenCode headlessly; `init`, `check`, `accept`, `baseline` and
`feedback` are offline (tests/test_behavior_harness.py covers them).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FIXTURES_REL = Path("tests") / "fixtures" / "behavior"
DEFAULT_WORKSPACE = Path(tempfile.gettempdir()) / "dev-agent-behavior-workspaces"
SKILLS_SOURCE = REPO / "skills"
BOOTSTRAP_SCRIPT = SKILLS_SOURCE / "dev-agent" / "scripts" / "bootstrap.py"
SKILL_CREATOR = REPO / ".agents" / "skills" / "skill-creator"
REVIEWER = SKILL_CREATOR / "eval-viewer" / "generate_review.py"
PREVIEW_DIR = REPO / ".behavior-review"

CONFIGS = ("new_skill", "old_skill", "without_skill")
ROOT_CONFIG = "new_skill"  # lives at the run root for backwards compatibility
LEGACY_CONFIGS = {"with_skill": "new_skill"}
DEFAULT_SETUP = ["bootstrap", "skills:auto-router,phase-protocol"]

ARTIFACT_KINDS = (
    "exists",
    "missing",
    "contains",
    "not-contains",
    "matches",
    "not-matches",
)
SCOPES = ("repo", "run")

STEPS_DIR = "steps"
BASE_SNAPSHOT_DIR = "_base_repo"

# Accepted-run baselines: tests/fixtures/behavior/baselines/<case>.json
BASELINES_DIR = "baselines"
IGNORE_DIRS = {"__pycache__", ".git", ".venv", "node_modules"}


def find_root() -> Path:
    current = Path(__file__).resolve().parent
    while True:
        if (current / "AGENTS.md").is_file():
            return current
        parent = current.parent
        if parent == current:
            sys.exit(f"error: AGENTS.md not found above {Path(__file__).resolve()}")
        current = parent


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _resolve(path: Path | str, base: Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else base / path


@dataclass
class Step:
    """One prompt in a scenario, with its own artifact checks."""

    id: str
    prompt: str
    expectations: list[str] = field(default_factory=list)
    expected_artifacts: list[str] = field(default_factory=list)


@dataclass
class Case:
    name: str
    profile: str
    prompt: str = ""
    setup: list[str] = field(default_factory=lambda: list(DEFAULT_SETUP))
    expectations: list[str] = field(default_factory=list)
    expected_artifacts: list[str] = field(default_factory=list)
    assertion_labels: dict[str, str] = field(default_factory=dict)
    layer: str = "behavior"
    path: Path | None = None
    # Every case has >= 1 step. A flat `prompt` case normalizes to a single
    # implicit step and keeps the legacy on-disk layout (`legacy=True`); a case
    # that declares `steps` shares one repo across them (`legacy=False`).
    steps: list[Step] = field(default_factory=list)
    legacy: bool = True

    @classmethod
    def load(cls, fixtures_root: Path, name: str) -> Case:
        case_path = Path(fixtures_root) / "cases" / name / "case.json"
        if not case_path.is_file():
            raise SystemExit(f"error: case not found: {case_path}")
        try:
            data = json.loads(case_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"error: unreadable case {case_path}: {exc}") from exc
        for key in ("name", "profile"):
            if not isinstance(data.get(key), str) or not data[key].strip():
                raise SystemExit(f"error: case {case_path} needs a non-empty {key!r}")
        if data.get("layer", "behavior") != "behavior":
            raise SystemExit(f"error: case {case_path} layer must be 'behavior'")
        setup = list(data.get("setup", DEFAULT_SETUP))
        assertion_labels = dict(data.get("assertion_labels", {}))
        layer = data.get("layer", "behavior")

        raw_steps = data.get("steps")
        if raw_steps is not None:
            if isinstance(data.get("prompt"), str) and data["prompt"].strip():
                raise SystemExit(
                    f"error: case {case_path} cannot have both 'prompt' and 'steps'"
                )
            if not isinstance(raw_steps, list) or not raw_steps:
                raise SystemExit(
                    f"error: case {case_path} 'steps' must be a non-empty list"
                )
            steps: list[Step] = []
            seen: set[str] = set()
            for raw in raw_steps:
                if not isinstance(raw, dict):
                    raise SystemExit(f"error: case {case_path} step must be an object")
                step_id = raw.get("id")
                step_prompt = raw.get("prompt")
                if not isinstance(step_id, str) or not step_id.strip():
                    raise SystemExit(
                        f"error: case {case_path} step needs a non-empty 'id'"
                    )
                if step_id in seen:
                    raise SystemExit(
                        f"error: case {case_path} duplicate step id {step_id!r}"
                    )
                seen.add(step_id)
                if not isinstance(step_prompt, str) or not step_prompt.strip():
                    raise SystemExit(
                        f"error: case {case_path} step {step_id!r} needs a non-empty 'prompt'"
                    )
                artifacts = list(raw.get("expected_artifacts", []))
                if not artifacts:
                    raise SystemExit(
                        f"error: case {case_path} step {step_id!r} needs 'expected_artifacts'"
                    )
                steps.append(
                    Step(
                        id=step_id,
                        prompt=step_prompt,
                        expectations=list(raw.get("expectations", [])),
                        expected_artifacts=artifacts,
                    )
                )
            return cls(
                name=data["name"],
                profile=data["profile"],
                setup=setup,
                assertion_labels=assertion_labels,
                layer=layer,
                path=case_path.parent,
                steps=steps,
                legacy=False,
            )

        prompt = data.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise SystemExit(f"error: case {case_path} needs a non-empty 'prompt'")
        expectations = list(data.get("expectations", []))
        expected_artifacts = list(data.get("expected_artifacts", []))
        return cls(
            name=data["name"],
            profile=data["profile"],
            prompt=prompt,
            setup=setup,
            expectations=expectations,
            expected_artifacts=expected_artifacts,
            assertion_labels=assertion_labels,
            layer=layer,
            path=case_path.parent,
            steps=[
                Step(
                    id=data["name"],
                    prompt=prompt,
                    expectations=expectations,
                    expected_artifacts=expected_artifacts,
                )
            ],
            legacy=True,
        )

    @property
    def overlay(self) -> Path | None:
        """Case-local `repo/` overlay applied on top of the profile repo."""
        if self.path is None:
            return None
        local = self.path / "repo"
        return local if local.is_dir() else None


def list_cases(fixtures_root: Path) -> list[str]:
    root = Path(fixtures_root) / "cases"
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if (p / "case.json").is_file())


def seed_repo(case: Case, dest: Path) -> None:
    """Copy the shared profile, then apply the case's optional `repo/` overlay."""
    profile = REPO / FIXTURES_REL / "profiles" / case.profile / "repo"
    if not profile.is_dir():
        raise SystemExit(f"error: profile {case.profile!r} has no repo/")
    shutil.copytree(profile, dest)
    overlay = case.overlay
    if overlay is not None:
        shutil.copytree(overlay, dest, dirs_exist_ok=True)


def _run_bootstrap(target: Path) -> None:
    proc = subprocess.run(
        [sys.executable, str(BOOTSTRAP_SCRIPT), "setup", "--target", str(target)],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise SystemExit(
            "error: bootstrap failed\n" + (proc.stdout or "") + (proc.stderr or "")
        )


def _install_skills(
    target: Path, names: list[str], source: Path = SKILLS_SOURCE
) -> None:
    for name in names:
        src = source / name
        if not src.is_dir():
            raise SystemExit(f"error: skill not found in {source}: {name}")
        dest = target / ".agents" / "skills" / name
        if dest.exists():
            shutil.rmtree(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dest)


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(REPO), *args],
        check=False,
        capture_output=True,
    )


def materialize_old_skills(
    case: Case, dest: Path, old_skills_dir: Path | None = None
) -> None:
    """Stage the previous version of every skill under test at `dest/<name>`.

    `--old-skills-dir` wins when given (a saved snapshot); otherwise the skill
    is exported from `git HEAD`, i.e. the last committed version.
    """
    names = skills_under_test(case)
    if not names:
        return
    dest.mkdir(parents=True, exist_ok=True)
    for name in names:
        target = dest / name
        if old_skills_dir is not None:
            src = Path(old_skills_dir) / name
            if not src.is_dir():
                raise SystemExit(
                    f"error: no old version of '{name}' in {old_skills_dir}"
                )
            shutil.copytree(src, target)
            continue
        listing = _git("ls-tree", "-r", "--name-only", "HEAD", "--", f"skills/{name}")
        paths = [p for p in listing.stdout.decode("utf-8", "replace").splitlines() if p]
        if listing.returncode != 0 or not paths:
            raise SystemExit(
                f"error: no git HEAD copy of skill '{name}' "
                "(commit it first or pass --old-skills-dir)"
            )
        for path in paths:
            blob = _git("show", f"HEAD:{path}")
            if blob.returncode != 0:
                raise SystemExit(f"error: cannot read HEAD:{path}")
            relative = Path(path).relative_to("skills")
            out = dest / relative
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(blob.stdout)


def apply_setup(
    repo: Path, setup: list[str], skills_source: Path = SKILLS_SOURCE
) -> list[str]:
    """Run the case `setup` steps against `repo`; return human-readable notes."""
    notes: list[str] = []
    for step in setup:
        if step == "bootstrap":
            _run_bootstrap(repo)
            notes.append("bootstrap: installed AGENTS.md + .agents/rules/")
        elif step.startswith("skills:"):
            names = [n.strip() for n in step.split(":", 1)[1].split(",") if n.strip()]
            _install_skills(repo, names, skills_source)
            notes.append("skills: " + ", ".join(names))
        elif step == "map":
            script = repo / ".agents" / "scripts" / "devagent" / "main.py"
            if not script.is_file():
                raise SystemExit(
                    "error: setup step 'map' needs a 'bootstrap' step first "
                    "(it installs the runtime at .agents/scripts/devagent/)"
                )
            proc = subprocess.run(
                [sys.executable, str(script), "map"],
                cwd=str(repo),
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if proc.returncode != 0:
                raise SystemExit(
                    "error: map generation failed\n" + proc.stdout + proc.stderr
                )
            notes.append("map: " + (proc.stdout or "").strip().splitlines()[-1])
        else:
            raise SystemExit(f"error: unknown setup step {step!r}")
    return notes


def run_dir(case: Case, run_id: str, workspace_root: Path) -> Path:
    return Path(workspace_root) / case.name / run_id


def canonical_config(config: str) -> str:
    return LEGACY_CONFIGS.get(config, config)


def config_path(run: Path, config: str) -> Path:
    """new_skill lives at the run root; other configs get a subdirectory."""
    return (
        run
        if canonical_config(config) == ROOT_CONFIG
        else run / canonical_config(config)
    )


def config_setup(case: Case, config: str) -> list[str]:
    """without_skill is the same repo with no framework installed."""
    return [] if canonical_config(config) == "without_skill" else list(case.setup)


def step_dir(base: Path, index: int, step: Step) -> Path:
    """Where one step's transcript/outputs/repo snapshot live (index is 1-based)."""
    return base / STEPS_DIR / f"{index}-{step.id}"


def snapshot_base_repo(base: Path) -> None:
    """Capture the seeded repo once, so each step can be reset to it."""
    snapshot = base / BASE_SNAPSHOT_DIR
    if not snapshot.exists():
        shutil.copytree(base / "repo", snapshot)


def reset_working_repo(base: Path) -> None:
    """Independent prompts: restore the seeded repo before a step runs.

    Steps in a scenario do not carry state - the shared repo is wiped back to
    the pristine snapshot so prompt k+1 never sees prompt k's edits.
    """
    snapshot = base / BASE_SNAPSHOT_DIR
    if not snapshot.is_dir():
        return
    repo = base / "repo"
    if repo.exists():
        shutil.rmtree(repo)
    shutil.copytree(snapshot, repo)


def select_configs(value: str) -> tuple[str, ...]:
    if value == "all":
        return CONFIGS
    if value == "both":
        return ("new_skill", "without_skill")
    if value == "compare":
        return ("new_skill", "old_skill")
    return (canonical_config(value),)


def existing_configs(run: Path) -> tuple[str, ...]:
    found = [c for c in CONFIGS if (config_path(run, c) / "repo").is_dir()]
    return tuple(found)


def init_run(
    case: Case,
    run_id: str,
    workspace_root: Path,
    force: bool = False,
    configs: tuple[str, ...] = (ROOT_CONFIG,),
    old_skills_dir: Path | None = None,
) -> tuple[Path, list[str]]:
    target = run_dir(case, run_id, workspace_root)
    if target.exists():
        if not force:
            raise SystemExit(f"error: run exists: {target} (use --force)")
        shutil.rmtree(target)
    target.mkdir(parents=True)
    notes: list[str] = []
    setups: dict[str, list[str]] = {}
    for raw_config in configs:
        config = canonical_config(raw_config)
        base = config_path(target, config)
        base.mkdir(parents=True, exist_ok=True)
        seed_repo(case, base / "repo")
        setup = config_setup(case, config)
        source = SKILLS_SOURCE
        staged: Path | None = None
        if config == "old_skill":
            staged = base / "_old_skills"
            materialize_old_skills(case, staged, old_skills_dir)
            source = staged
        config_notes = apply_setup(base / "repo", setup, source)
        if staged is not None and staged.exists():
            shutil.rmtree(staged)
        setups[config] = setup
        notes.extend(f"[{config}] {note}" for note in config_notes)
    (target / "run.json").write_text(
        json.dumps(
            {
                "case": case.name,
                "run_id": run_id,
                "profile": case.profile,
                "configs": [canonical_config(c) for c in configs],
                "setup": setups,
                "prompt": case.prompt,
                "steps": [step.id for step in case.steps],
                "multi_step": not case.legacy,
                "created_at": iso_now(),
                "setup_notes": notes,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return target, notes


def parse_artifact(artifact: str) -> tuple[str, str, str, str]:
    """Split an artifact spec into (kind, scope, path, text)."""
    kind, sep, rest = artifact.partition(":")
    if not sep or kind not in ARTIFACT_KINDS:
        raise ValueError(f"bad artifact (kind): {artifact!r}")
    scope = "repo"
    if rest.startswith(("repo:", "run:")):
        scope, rest = rest.split(":", 1)
    if scope not in SCOPES:
        raise ValueError(f"bad artifact (scope): {artifact!r}")
    if kind in ("contains", "not-contains", "matches", "not-matches"):
        path, sep, text = rest.partition(":")
        if not sep or not path or not text:
            raise ValueError(f"bad artifact (text): {artifact!r}")
        return kind, scope, path, text
    if not rest:
        raise ValueError(f"bad artifact (path): {artifact!r}")
    return kind, scope, rest, ""


def _scoped_root(run: Path, scope: str) -> Path:
    return run if scope == "run" else run / "repo"


def check_artifact(run: Path, artifact: str) -> tuple[bool, str]:
    """Evaluate one artifact spec against a run directory."""
    try:
        kind, scope, rel, text = parse_artifact(artifact)
    except ValueError as exc:
        return False, str(exc)
    root = _scoped_root(run, scope)
    matches = [p for p in sorted(root.glob(rel)) if p.exists()]

    if kind == "exists":
        return bool(matches), f"{len(matches)} match(es) for {scope}:{rel}"
    if kind == "missing":
        return not matches, f"{len(matches)} match(es) for {scope}:{rel}"
    if not matches:
        return False, f"file not found: {scope}:{rel}"
    found = False
    for path in matches:
        if not path.is_file():
            continue
        try:
            body = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if kind in ("matches", "not-matches"):
            try:
                if re.search(text, body):
                    found = True
                    break
            except re.error as exc:
                return False, f"bad regex {text!r}: {exc}"
        elif text in body:
            found = True
            break
    if kind == "contains":
        return found, f"{'found' if found else 'missing'} {text!r} in {scope}:{rel}"
    if kind == "matches":
        return (
            found,
            f"{'matched' if found else 'no match for'} /{text}/ in {scope}:{rel}",
        )
    if kind == "not-matches":
        return (
            not found
        ), f"{'matched' if found else 'no match for'} /{text}/ in {scope}:{rel}"
    if found is False and not any(p.is_file() for p in matches):
        return False, f"file not found: {scope}:{rel}"
    return (not found), f"{'found' if found else 'absent'} {text!r} in {scope}:{rel}"


def describe_artifact(artifact: str) -> str:
    """A human sentence for an artifact check; falls back to the raw string."""
    try:
        kind, scope, rel, text = parse_artifact(artifact)
    except ValueError:
        return artifact
    where = "the agent's answer" if scope == "run" else "the repo"
    location = "" if (scope == "run" and rel == "transcript.md") else f" in `{rel}`"
    if kind == "exists":
        return f"{where} has a path matching `{rel}`"
    if kind == "missing":
        return f"{where} has no path matching `{rel}`"
    if kind == "contains":
        return f"{where} contains {text!r}{location}"
    if kind == "matches":
        return f"{where} matches /{text}/{location}"
    if kind == "not-matches":
        return f"{where} does not match /{text}/{location}"
    return f"{where} does not contain {text!r}{location}"


def _grading(checks: list[dict]) -> dict:
    """The skill-creator grading.json shape for a list of artifact checks."""
    total = len(checks)
    passed_count = sum(1 for item in checks if item["passed"])
    return {
        "expectations": [
            {
                "text": item["description"],
                "passed": item["passed"],
                "evidence": f"{item['detail']} (check: {item['artifact']})",
            }
            for item in checks
        ],
        "summary": {
            "pass_rate": round(passed_count / total, 3) if total else 0.0,
            "passed": passed_count,
            "failed": total - passed_count,
            "total": total,
        },
    }


def _step_checks(case: Case, out: Path, step: Step) -> list[dict]:
    checks = []
    for artifact in step.expected_artifacts:
        ok, detail = check_artifact(out, artifact)
        checks.append(
            {
                "artifact": artifact,
                "description": case.assertion_labels.get(artifact)
                or describe_artifact(artifact),
                "passed": ok,
                "detail": detail,
            }
        )
    return checks


def check_config_steps(case: Case, run: Path, config: str) -> dict:
    """Grade every step of a multi-step scenario; aggregate at the config root.

    Each step dir is shaped like a run dir (`repo/` + `transcript.md`), so the
    existing artifact DSL applies unchanged. Per-step `result.json` /
    `grading.json` are written, plus a config-level aggregate the review uses.
    """
    base = config_path(run, config)
    step_results: list[dict] = []
    aggregate: list[dict] = []
    for index, step in enumerate(case.steps, start=1):
        out = step_dir(base, index, step)
        out.mkdir(parents=True, exist_ok=True)
        checks = _step_checks(case, out, step)
        step_passed = bool(checks) and all(item["passed"] for item in checks)
        step_results.append(
            {
                "case": case.name,
                "step": step.id,
                "config": config,
                "passed": step_passed,
                "checks": checks,
                "checked_at": iso_now(),
            }
        )
        (out / "result.json").write_text(
            json.dumps(step_results[-1], indent=2) + "\n", encoding="utf-8"
        )
        (out / "grading.json").write_text(
            json.dumps(_grading(checks), indent=2) + "\n", encoding="utf-8"
        )
        aggregate.extend(checks)
    result = {
        "case": case.name,
        "config": config,
        "passed": bool(aggregate) and all(item["passed"] for item in aggregate),
        "steps": step_results,
        "checks": aggregate,
        "checked_at": iso_now(),
    }
    (base / "result.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    (base / "grading.json").write_text(
        json.dumps(_grading(aggregate), indent=2) + "\n", encoding="utf-8"
    )
    return result


def check_config(case: Case, run: Path, config: str = ROOT_CONFIG) -> dict:
    """Grade one config; write result.json + skill-creator grading.json."""
    if not case.legacy:
        return check_config_steps(case, run, config)
    base = config_path(run, config)
    checks = _step_checks(case, base, case_steps(case)[0])
    result = {
        "case": case.name,
        "config": config,
        "passed": bool(checks) and all(item["passed"] for item in checks),
        "checks": checks,
        "checked_at": iso_now(),
    }
    (base / "result.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    (base / "grading.json").write_text(
        json.dumps(_grading(checks), indent=2) + "\n", encoding="utf-8"
    )
    return result


def check_run(case: Case, run: Path) -> dict:
    """Backwards-compatible: grade the with_skill config at the run root."""
    return check_config(case, run, ROOT_CONFIG)


def case_steps(case: Case) -> list[Step]:
    """The case's steps. A flat Case built directly (tests) has none, so one
    implicit step is synthesized from its flat fields."""
    if case.steps:
        return case.steps
    return [
        Step(
            id=case.name,
            prompt=case.prompt,
            expectations=case.expectations,
            expected_artifacts=case.expected_artifacts,
        )
    ]


def skills_under_test(case: Case) -> list[str]:
    names: list[str] = []
    for step in case.setup:
        if step.startswith("skills:"):
            names.extend(
                n.strip() for n in step.split(":", 1)[1].split(",") if n.strip()
            )
    return names


def _tree_sha(path: Path) -> str:
    """Deterministic content hash of a directory tree (caches ignored).

    Newlines are normalized to LF so a baseline accepted on one OS still
    matches the same checkout on another.
    """
    digest = hashlib.sha256()
    for entry in sorted(path.rglob("*")):
        if entry.is_dir() or entry.suffix == ".pyc":
            continue
        if any(part in IGNORE_DIRS for part in entry.parts):
            continue
        rel = entry.relative_to(path).as_posix()
        data = entry.read_bytes().replace(b"\r\n", b"\n")
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(data)
        digest.update(b"\0")
    return digest.hexdigest()


def baseline_path(case: Case) -> Path | None:
    """Where the accepted baseline for a case lives, if the case has a path."""
    if case.path is None:
        return None
    return case.path.parent.parent / BASELINES_DIR / f"{case.name}.json"


def skills_hash(case: Case) -> str:
    """Hash the shipped skills a case exercises, plus the shared runtime.

    Every case bootstraps `skills/dev-agent` (runtime + seed rulebook +
    installer), so a change there can affect any case even when it is not
    listed in `setup`.
    """
    names = sorted(set(skills_under_test(case)) | {"dev-agent"})
    digest = hashlib.sha256()
    for name in names:
        src = SKILLS_SOURCE / name
        digest.update(f"{name}\0".encode())
        if src.is_dir():
            digest.update(_tree_sha(src).encode("utf-8"))
        else:
            digest.update(b"missing")
        digest.update(b"\0")
    return digest.hexdigest()


def fixture_hash(case: Case) -> str:
    """Hash the case fixture itself (case.json + any per-case overlay)."""
    if case.path is None:
        return ""
    return _tree_sha(case.path)


def load_baseline(case: Case) -> dict | None:
    path = baseline_path(case)
    if path is None or not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def baseline_checks(case: Case) -> list[dict]:
    """Drift checks against an accepted baseline; empty when none is recorded."""
    baseline = load_baseline(case)
    if baseline is None:
        return []
    return [
        {
            "name": "baseline: skills under test unchanged",
            "ok": baseline.get("skills_sha256") == skills_hash(case),
            "detail": "the skills changed since accept; re-run the eval and accept",
        },
        {
            "name": "baseline: case fixture unchanged",
            "ok": baseline.get("fixture_sha256") == fixture_hash(case),
            "detail": "the case changed since accept; re-run the eval and accept",
        },
    ]


def accept_run(
    case: Case,
    run: Path,
    configs: tuple[str, ...] | None = None,
    model: str | None = None,
    force: bool = False,
) -> Path:
    """Record a checked run as the case's accepted baseline.

    Mirrors `skill_eval accept`: the run must have graded (`check`) and its
    `new_skill` verdict must have passed unless `force` is set. The baseline
    pins the skills + fixture hashes so later drift is detectable offline.
    """
    present = existing_configs(run)
    if not present:
        raise SystemExit(f"error: run not initialized: {run}")
    chosen = tuple(c for c in (configs or present) if c in present) or present
    steps_snapshot: list[dict] = []
    passed = 0
    total = 0
    verdict_ok = True
    for config in chosen:
        result_path = config_path(run, config) / "result.json"
        if not result_path.is_file():
            raise SystemExit(
                f"error: config {config!r} has no result.json (run check first)"
            )
        result = json.loads(result_path.read_text(encoding="utf-8"))
        checks = result.get("checks", [])
        passed += sum(1 for c in checks if c.get("passed"))
        total += len(checks)
        if config == ROOT_CONFIG:
            verdict_ok = verdict_ok and bool(result.get("passed"))
        step_results = result.get("steps") or [
            {"step": case.steps[0].id, "checks": checks}
        ]
        for step_result in step_results:
            steps_snapshot.append(
                {
                    "step": step_result.get("step"),
                    "config": config,
                    "checks": [
                        {"artifact": c.get("artifact"), "passed": c.get("passed")}
                        for c in step_result.get("checks", [])
                    ],
                }
            )
    if not verdict_ok and not force:
        raise SystemExit("error: the run did not pass (use --force to accept anyway)")
    path = baseline_path(case)
    if path is None:
        raise SystemExit("error: case has no fixture path to store a baseline")
    baseline = {
        "case": case.name,
        "accepted_at": iso_now(),
        "model": model,
        "profile": case.profile,
        "configs": list(chosen),
        "skills_under_test": skills_under_test(case),
        "skills_sha256": skills_hash(case),
        "fixture_sha256": fixture_hash(case),
        "summary": {
            "passed": passed,
            "total": total,
            "pass_rate": round(passed / total, 3) if total else 0.0,
        },
        "steps": steps_snapshot,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
    return path


def print_baseline_status(case: Case) -> None:
    """Print an advisory when an accepted baseline has drifted (§Phase 2)."""
    for check in baseline_checks(case):
        if not check["ok"]:
            print(f"baseline drift: {check['name']} - {check['detail']}")


def _copy_outputs(base: Path, dest: Path) -> None:
    dest_out = dest / "outputs"
    dest_out.mkdir(parents=True, exist_ok=True)
    outputs = base / "outputs"
    if outputs.is_dir():
        for item in sorted(outputs.iterdir()):
            if item.is_file():
                shutil.copy2(item, dest_out / item.name)
    if not any(dest_out.iterdir()):
        (dest_out / "answer.md").write_text("(no output captured)\n", encoding="utf-8")


def run_benchmark(iteration: Path, skill_name: str) -> Path | None:
    """Aggregate grading.json files into the viewer's Benchmark/summary tab."""
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.aggregate_benchmark",
            str(iteration),
            "--skill-name",
            skill_name,
        ],
        cwd=SKILL_CREATOR,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    benchmark = iteration / "benchmark.json"
    if proc.returncode != 0 or not benchmark.is_file():
        print(
            "warning: benchmark aggregation failed: "
            + (proc.stdout + proc.stderr).strip()[-300:],
            file=sys.stderr,
        )
        return None
    return benchmark


def build_review_workspace(
    entries: list[tuple[Case, str, Path]],
    review_dir: Path,
    skill_name: str,
) -> list[str]:
    """Materialize every (case, config, graded dir) into the viewer layout."""
    if review_dir.exists():
        shutil.rmtree(review_dir)
    iteration = review_dir / "iteration-1"
    run_ids: list[str] = []
    grouped: dict[str, list[tuple[Case, str, Path]]] = {}
    for entry in entries:
        grouped.setdefault(entry[0].name, []).append(entry)
    for index, (name, items) in enumerate(grouped.items()):
        eval_dir = iteration / f"eval-{index}-{name}"
        for case, config, base in items:
            dest = eval_dir / config / "run-1"
            _copy_outputs(base, dest)
            grading = base / "grading.json"
            if grading.is_file():
                shutil.copy2(grading, dest / "grading.json")
            metadata = {
                "eval_id": index,
                "eval_name": case.name,
                "prompt": case.prompt,
                "config": config,
                "assertions": list(case.expected_artifacts),
                "assertion_labels": [
                    case.assertion_labels.get(artifact) or describe_artifact(artifact)
                    for artifact in case.expected_artifacts
                ],
                "expectations": list(case.expectations),
            }
            body = json.dumps(metadata, indent=2) + "\n"
            (dest / "eval_metadata.json").write_text(body, encoding="utf-8")
            (eval_dir / "eval_metadata.json").write_text(body, encoding="utf-8")
            run_ids.append(f"iteration-1-eval-{index}-{name}-{config}-run-1")
    return run_ids


def render_review(
    entries: list[tuple[Case, str, Path]],
    out_root: Path,
    label: str,
    skill_name: str,
) -> Path | None:
    """Build review.html (with the Benchmark summary tab) for N cases/configs."""
    if not entries:
        return None
    review_dir = out_root / "review"
    run_ids = build_review_workspace(entries, review_dir, skill_name)
    html = out_root / "review.html"
    benchmark = run_benchmark(review_dir / "iteration-1", skill_name)
    cmd = [
        sys.executable,
        str(REVIEWER),
        str(review_dir),
        "--static",
        str(html),
        "--skill-name",
        skill_name,
    ]
    if benchmark is not None:
        cmd += ["--benchmark", str(benchmark)]
    # The vendored viewer reads output files with Python's locale encoding;
    # on Windows that is cp1252 and UTF-8 answers arrive as mojibake. Force
    # UTF-8 mode for the child without editing the vendored skill.
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run(
        cmd,
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    if proc.returncode != 0 or not html.is_file():
        print(
            "warning: review generation failed: "
            + (proc.stdout + proc.stderr).strip()[-400:],
            file=sys.stderr,
        )
        return None
    template = {
        "status": "pending",
        "reviews": [{"run_id": run_id, "feedback": ""} for run_id in run_ids],
    }
    (out_root / "feedback-template.json").write_text(
        json.dumps(template, indent=2) + "\n", encoding="utf-8"
    )
    return html


def review_units(case: Case, config: str, base: Path) -> list[tuple[Case, str, Path]]:
    """Expand a config into review pages: one per step for a scenario.

    A multi-step case becomes one pseudo-case per step (`<case>#<step>`) whose
    graded dir is the step dir, so `render_review` shows one page per prompt
    with the configs side by side and keeps the Benchmark aggregation.
    """
    if case.legacy:
        return [(case, config, base)]
    units: list[tuple[Case, str, Path]] = []
    for index, step in enumerate(case.steps, start=1):
        unit = Case(
            name=f"{case.name}#{step.id}",
            profile=case.profile,
            prompt=step.prompt,
            expectations=step.expectations,
            expected_artifacts=step.expected_artifacts,
            assertion_labels=case.assertion_labels,
            layer=case.layer,
            steps=[step],
            legacy=True,
        )
        units.append((unit, config, step_dir(base, index, step)))
    return units


def build_review(case: Case, run: Path) -> Path | None:
    """Review for one case: every config present in its run directory."""
    entries: list[tuple[Case, str, Path]] = []
    for config in existing_configs(run):
        entries.extend(review_units(case, config, config_path(run, config)))
    return render_review(
        entries,
        run,
        label=f"{case.name}-{run.name}",
        skill_name=", ".join(skills_under_test(case)) or case.name,
    )


def trusted_preview(label: str, html: Path) -> Path:
    """Copy the self-contained review into the repo so the editor can open it.

    The workspace lives outside the repo (so bootstrap can run), but VSCode's
    built-in browser refuses `file://` pages outside a trusted folder. The copy
    lives under the gitignored `.behavior-review/` and needs no server.
    """
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    preview = PREVIEW_DIR / f"{label}.html"
    shutil.copy2(html, preview)
    return preview


def repair_mojibake(text: str) -> str:
    """Undo UTF-8-read-as-cp1252 damage from OpenCode's Windows console output.

    Every UTF-8 multibyte sequence starts with a byte >= 0x80, which cp1252
    renders as 'â', 'Ã' or 'Â' - so those three characters are the markers.
    """
    if not any(marker in text for marker in ("\u00e2", "\u00c3", "\u00c2")):
        return text
    try:
        return text.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Mixed text (emoji or CJK broke cp1252): repair word-sized chunks that
        # round-trip, leave the rest untouched.
        out: list[str] = []
        for chunk in text.split(" "):
            try:
                out.append(chunk.encode("cp1252").decode("utf-8"))
            except (UnicodeEncodeError, UnicodeDecodeError):
                out.append(chunk)
        return " ".join(out)


def extract_assistant_text(jsonl: str) -> str:
    """Pull the assistant's text parts out of OpenCode's JSONL stream."""
    parts: list[str] = []
    for line in jsonl.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "text":
            continue
        part = event.get("part") or {}
        text = part.get("text") or event.get("text")
        if isinstance(text, str) and text.strip():
            parts.append(text.strip())
    return repair_mojibake("\n\n".join(parts))


def write_answer(base: Path, stdout: str) -> None:
    """Materialize `outputs/answer.md` - what the viewer shows as 'what the AI generated'."""
    outputs = base / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    answer = (
        extract_assistant_text(stdout)
        or stdout.strip()
        or "(no assistant text captured)"
    )
    (outputs / "answer.md").write_text(answer + "\n", encoding="utf-8")


def drive_opencode(
    run: Path,
    prompt: str,
    timeout: int,
    model: str | None,
    agent: str = "build",
    config: str = ROOT_CONFIG,
    capture_dir: Path | None = None,
) -> int:
    exe = shutil.which("opencode")
    if not exe:
        print("error: 'opencode' not found on PATH", file=sys.stderr)
        return 2
    cmd = [exe, "run", prompt, "--format", "json", "--auto", "--standalone"]
    if model:
        cmd += ["--model", model]
    if agent:
        # OpenCode's default agent is 'plan', which ignores the installed
        # AGENTS.md workflow. Behavior cases must run the build agent.
        cmd += ["--agent", agent]
    base = config_path(run, config)
    out = Path(capture_dir) if capture_dir is not None else base
    out.mkdir(parents=True, exist_ok=True)
    started = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(base / "repo"),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        print(f"error: opencode timed out after {timeout}s", file=sys.stderr)
        return 1
    transcript = "# transcript\n\n" + (proc.stdout or "") + "\n" + (proc.stderr or "")
    (out / "transcript.md").write_text(transcript, encoding="utf-8")
    (out / "opencode.stderr.txt").write_text(proc.stderr or "", encoding="utf-8")
    write_answer(out, proc.stdout or "")
    print(f"opencode exit: {proc.returncode} ({round(time.time() - started, 1)}s)")
    return 0 if proc.returncode == 0 else 1


def run_config(
    run: Path,
    case: Case,
    config: str,
    timeout: int,
    model: str | None,
    agent: str = "build",
) -> int:
    """Drive every step of `case` for one config; return 0 when all succeed.

    Legacy cases are a single implicit step captured at the config root. A
    multi-step scenario runs each prompt against a freshly reset copy of the
    shared repo, captures the step's transcript/outputs, and snapshots the repo
    it left, so each step grades independently.
    """
    if case.legacy:
        return drive_opencode(
            run, case_steps(case)[0].prompt, timeout, model, agent, config
        )
    base = config_path(run, config)
    snapshot_base_repo(base)
    total = len(case.steps)
    rc = 0
    for index, step in enumerate(case.steps, start=1):
        reset_working_repo(base)
        out = step_dir(base, index, step)
        out.mkdir(parents=True, exist_ok=True)
        print(f"  step {index}/{total}: {step.id}")
        if (
            drive_opencode(
                run, step.prompt, timeout, model, agent, config, capture_dir=out
            )
            != 0
        ):
            rc = 1
        snapshot = out / "repo"
        if snapshot.exists():
            shutil.rmtree(snapshot)
        shutil.copytree(base / "repo", snapshot)
    return rc


def cmd_list(fixtures_root: Path, skill: str | None = None) -> int:
    for name in list_cases(fixtures_root):
        case = Case.load(fixtures_root, name)
        skills = skills_under_test(case)
        if skill and skill not in skills:
            continue
        print(f"{name}  skills={', '.join(skills) or '-'}")
    return 0


def cmd_init(args: argparse.Namespace, fixtures_root: Path) -> int:
    case = Case.load(fixtures_root, args.case)
    run_id = args.run_id or new_run_id()
    target, notes = init_run(
        case,
        run_id,
        args.workspace_root,
        force=args.force,
        configs=select_configs(args.config),
        old_skills_dir=args.old_skills_dir,
    )
    for note in notes:
        print(note)
    print(f"initialized: {target}")
    print(
        f"next: python tools/behavior_eval.py run --case {case.name} "
        f"--run-id {run_id} --config {args.config}"
    )
    return 0


def cmd_run(args: argparse.Namespace, fixtures_root: Path) -> int:
    case = Case.load(fixtures_root, args.case)
    target = run_dir(case, args.run_id, args.workspace_root)
    present = existing_configs(target)
    if not present:
        print(f"error: run not initialized: {target} (run init first)", file=sys.stderr)
        return 2
    configs = tuple(c for c in select_configs(args.config) if c in present)
    if not configs:
        print(
            f"error: requested config not initialized in {target} "
            f"(present: {', '.join(present)})",
            file=sys.stderr,
        )
        return 2
    rc = 0
    for config in configs:
        print(f"running config: {config}")
        if run_config(target, case, config, args.timeout, args.model, args.agent) != 0:
            rc = 1
    print(
        f"next: python tools/behavior_eval.py check --case {case.name} "
        f"--run-id {args.run_id}"
    )
    return rc


def cmd_check(args: argparse.Namespace, fixtures_root: Path) -> int:
    case = Case.load(fixtures_root, args.case)
    target = run_dir(case, args.run_id, args.workspace_root)
    if not target.is_dir():
        print(f"error: run not found: {target}", file=sys.stderr)
        return 2
    present = existing_configs(target)
    if not present:
        print(f"error: run not initialized: {target}", file=sys.stderr)
        return 2
    configs = tuple(c for c in select_configs(args.config) if c in present) or present
    ok = True
    results: dict[str, dict] = {}
    for config in configs:
        result = check_config(case, target, config)
        results[config] = result
        prefix = f"[{config}] " if len(configs) > 1 else ""
        for item in result["checks"]:
            mark = "PASS" if item["passed"] else "FAIL"
            print(f"{mark} {prefix}{item['artifact']} - {item['detail']}")
        # The case's verdict is the with_skill run: the baseline is a
        # comparison, so it is expected to fail the framework assertions.
        if config == ROOT_CONFIG:
            ok = result["passed"]
        elif ROOT_CONFIG not in configs:
            ok = ok and result["passed"]
    print(f"{'PASS' if ok else 'FAIL'} case {case.name}")
    print_baseline_status(case)
    if not args.no_review:
        html = build_review(case, target)
        if html is not None:
            preview = trusted_preview(f"{case.name}-{target.name}", html)
            print(f"review: {html}")
            print(f"open:   {preview}  (trusted copy - no server needed)")
            print(
                "next: open the review, click 'Submit All Reviews', then save the "
                f"download as {target / 'feedback.json'}"
            )
    return 0 if ok else 1


def cmd_batch(args: argparse.Namespace, fixtures_root: Path) -> int:
    """Run N predefined prompts in one review (new vs old skill by default)."""
    names = [n.strip() for n in (args.cases or "").split(",") if n.strip()]
    if args.skill:
        names = [
            name
            for name in list_cases(fixtures_root)
            if args.skill in skills_under_test(Case.load(fixtures_root, name))
        ]
    if not names:
        print("error: pass --cases a,b,c or --skill <name>", file=sys.stderr)
        return 2

    batch_root = Path(args.workspace_root) / f"batch-{args.run_id}"
    if batch_root.exists():
        if not args.force:
            print(f"error: batch exists: {batch_root} (use --force)", file=sys.stderr)
            return 2
        shutil.rmtree(batch_root)
    batch_root.mkdir(parents=True)

    configs = select_configs(args.configs)
    cases = [Case.load(fixtures_root, name) for name in names]
    entries: list[tuple[Case, str, Path]] = []
    rc = 0
    for case in cases:
        run, _notes = init_run(
            case,
            "run-1",
            batch_root / "cases",
            force=True,
            configs=configs,
            old_skills_dir=args.old_skills_dir,
        )
        for config in configs:
            print(f"running: {case.name} [{config}]")
            if run_config(run, case, config, args.timeout, args.model, args.agent) != 0:
                rc = 1
        for config in configs:
            result = check_config(case, run, config)
            entries.extend(review_units(case, config, config_path(run, config)))
            mark = "PASS" if result["passed"] else "FAIL"
            print(f"{mark} {case.name} [{config}]")
        print_baseline_status(case)

    skills = sorted({s for case in cases for s in skills_under_test(case)})
    skill_name = ", ".join(skills) or "behavior suite"
    html = render_review(
        entries, batch_root, label=f"batch-{args.run_id}", skill_name=skill_name
    )
    (batch_root / "batch.json").write_text(
        json.dumps(
            {
                "run_id": args.run_id,
                "cases": [case.name for case in cases],
                "configs": list(configs),
                "skills": skills,
                "created_at": iso_now(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    if html is None:
        print("error: review generation failed", file=sys.stderr)
        return 1
    preview = trusted_preview(f"batch-{args.run_id}", html)
    print(f"review: {html}")
    print(f"open:   {preview}  (trusted copy - no server needed)")
    print(
        "next: submit reviews, then save the download as "
        f"{batch_root / 'feedback.json'} and run feedback --run-dir {batch_root}"
    )
    return rc


def cmd_feedback(args: argparse.Namespace, fixtures_root: Path) -> int:
    if getattr(args, "run_dir", None):
        target = _resolve(args.run_dir, REPO)
        label = target.name
        skills: list[str] = []
        batch_meta = target / "batch.json"
        if batch_meta.is_file():
            try:
                skills = json.loads(batch_meta.read_text(encoding="utf-8")).get(
                    "skills", []
                )
            except (OSError, json.JSONDecodeError):
                skills = []
    else:
        case = Case.load(fixtures_root, args.case)
        target = run_dir(case, args.run_id, args.workspace_root)
        label = case.name
        skills = skills_under_test(case)
    path = (
        _resolve(args.feedback, target) if args.feedback else target / "feedback.json"
    )
    if not path.is_file():
        print(f"error: feedback not found: {path}", file=sys.stderr)
        print(
            "  open review.html, click 'Submit All Reviews', and save "
            "feedback.json at that path",
            file=sys.stderr,
        )
        return 2
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: unreadable feedback {path}: {exc}", file=sys.stderr)
        return 2
    if isinstance(data, dict):
        reviews = data.get("reviews", [])
        status = data.get("status", "")
    elif isinstance(data, list):
        reviews, status = data, ""
    else:
        print(f"error: unexpected feedback shape in {path}", file=sys.stderr)
        return 2

    lines = [f"# Feedback digest - {label}", "", f"source: {path}"]
    lines.append(f"skills under test: {', '.join(skills) or '-'}")
    lines.append("revise with: author-skill (skills/<name>/), then re-run the eval")
    if status:
        lines.append(f"status: {status}")
    lines.append("")
    used = 0
    for review in reviews:
        if not isinstance(review, dict):
            continue
        text = (review.get("feedback") or "").strip()
        if not text:
            continue
        used += 1
        lines += [f"## {review.get('run_id', '?')}", "", text, ""]
    digest = target / "feedback-digest.md"
    digest.write_text("\n".join(lines), encoding="utf-8")
    print(f"reviews with feedback: {used}")
    print(f"digest: {digest}")
    if used == 0:
        print("no written feedback yet - submit reviews in review.html first")
    return 0


def cmd_accept(args: argparse.Namespace, fixtures_root: Path) -> int:
    case = Case.load(fixtures_root, args.case)
    target = run_dir(case, args.run_id, args.workspace_root)
    if not target.is_dir():
        print(f"error: run not found: {target}", file=sys.stderr)
        return 2
    path = accept_run(
        case,
        target,
        configs=select_configs(args.config),
        model=args.model,
        force=args.force,
    )
    print(f"accepted: {case.name}")
    print(f"baseline: {path}")
    print(
        "next: commit the baseline; `baseline` then flags drift when the "
        "skills or case change"
    )
    return 0


def cmd_baseline(args: argparse.Namespace, fixtures_root: Path) -> int:
    """Offline drift report: compare each case against its accepted baseline.

    Deterministic and agent-free, so it is safe to run in CI: a skill edit
    after `accept` shows up as drift until the case is re-run and re-accepted.
    """
    names = list_cases(fixtures_root)
    if args.skill:
        names = [
            name
            for name in names
            if args.skill in skills_under_test(Case.load(fixtures_root, name))
        ]
    ok = drift = missing = 0
    for name in names:
        case = Case.load(fixtures_root, name)
        if load_baseline(case) is None:
            status = "no-baseline"
            missing += 1
        elif any(not c["ok"] for c in baseline_checks(case)):
            status = "DRIFT"
            drift += 1
        else:
            status = "ok"
            ok += 1
        print(f"{status:<12} {name}")
    print(f"\ncases: {len(names)}  ok: {ok}  drift: {drift}  no-baseline: {missing}")
    if drift:
        print(
            "error: some baselines drifted; re-run and accept those cases",
            file=sys.stderr,
        )
        return 1
    if args.strict and missing:
        print(
            f"error: --strict requires a baseline for all {len(names)} cases "
            f"({missing} missing)",
            file=sys.stderr,
        )
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Behavior/E2E harness for prompt-level framework cases."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    list_p = sub.add_parser("list", help="list behavior cases")
    list_p.add_argument(
        "--skill", default=None, help="only cases exercising this skill"
    )
    list_p.set_defaults(handler=cmd_list)

    for name, handler, helptext in (
        ("init", cmd_init, "seed a run from the case fixture + setup"),
        ("run", cmd_run, "drive OpenCode headlessly inside the seeded repo"),
        ("check", cmd_check, "grade artifacts, write grading.json + review.html"),
    ):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("--case", required=True)
        p.add_argument("--run-id", default=None)
        p.add_argument(
            "--workspace-root",
            type=Path,
            default=_resolve(DEFAULT_WORKSPACE, REPO),
        )
        if name == "init":
            p.add_argument("--force", action="store_true")
            p.add_argument(
                "--config",
                choices=[*CONFIGS, "with_skill", "both", "compare", "all"],
                default=ROOT_CONFIG,
                help="new_skill (default), old_skill, without_skill, compare, both",
            )
            p.add_argument(
                "--old-skills-dir",
                type=Path,
                default=None,
                help="snapshot dir for old_skill (default: export from git HEAD)",
            )
        if name == "run":
            p.add_argument("--timeout", type=int, default=900)
            p.add_argument("--model", default=None)
            p.add_argument(
                "--agent",
                default="build",
                help="OpenCode agent (default: build; 'plan' ignores the rules)",
            )
            p.add_argument(
                "--config",
                choices=[*CONFIGS, "with_skill", "both", "compare"],
                default=ROOT_CONFIG,
                help="which initialized config(s) to run",
            )
        if name == "check":
            p.add_argument(
                "--config",
                choices=[*CONFIGS, "with_skill", "both", "compare", "all"],
                default="all",
                help="grade every present config by default",
            )
            p.add_argument(
                "--no-review",
                action="store_true",
                help="skip review.html generation",
            )
        p.set_defaults(handler=handler)

    feedback_p = sub.add_parser(
        "feedback", help="turn a downloaded feedback.json into a revision digest"
    )
    feedback_p.add_argument("--case", default=None)
    feedback_p.add_argument("--run-id", default=None)
    feedback_p.add_argument(
        "--run-dir",
        default=None,
        help="batch (or case) run directory; alternative to --case/--run-id",
    )
    feedback_p.add_argument(
        "--workspace-root",
        type=Path,
        default=_resolve(DEFAULT_WORKSPACE, REPO),
    )
    feedback_p.add_argument(
        "--feedback",
        default=None,
        help="path to feedback.json (default <run>/feedback.json)",
    )
    feedback_p.set_defaults(handler=cmd_feedback)

    batch_p = sub.add_parser(
        "batch",
        help="run N predefined prompts into one review (new vs old skill by default)",
    )
    batch_p.add_argument("--cases", default=None, help="comma-separated case names")
    batch_p.add_argument(
        "--skill", default=None, help="select every case for this skill"
    )
    batch_p.add_argument("--run-id", default=None)
    batch_p.add_argument(
        "--workspace-root",
        type=Path,
        default=_resolve(DEFAULT_WORKSPACE, REPO),
    )
    batch_p.add_argument(
        "--configs",
        choices=[*CONFIGS, "both", "compare", "all"],
        default="compare",
        help="compare = new_skill + old_skill (default)",
    )
    batch_p.add_argument("--old-skills-dir", type=Path, default=None)
    batch_p.add_argument("--force", action="store_true")
    batch_p.add_argument("--timeout", type=int, default=900)
    batch_p.add_argument("--model", default=None)
    batch_p.add_argument("--agent", default="build")
    batch_p.set_defaults(handler=cmd_batch)

    accept_p = sub.add_parser(
        "accept", help="record a checked run as the case's accepted baseline"
    )
    accept_p.add_argument("--case", required=True)
    accept_p.add_argument("--run-id", required=True)
    accept_p.add_argument(
        "--workspace-root",
        type=Path,
        default=_resolve(DEFAULT_WORKSPACE, REPO),
    )
    accept_p.add_argument(
        "--config",
        choices=[*CONFIGS, "with_skill", "both", "compare", "all"],
        default="all",
        help="configs to record (default: every present config)",
    )
    accept_p.add_argument("--model", default=None)
    accept_p.add_argument("--force", action="store_true")
    accept_p.set_defaults(handler=cmd_accept)

    baseline_p = sub.add_parser(
        "baseline", help="offline drift report for accepted case baselines"
    )
    baseline_p.add_argument(
        "--skill", default=None, help="only cases exercising this skill"
    )
    baseline_p.add_argument(
        "--strict",
        action="store_true",
        help="fail when any case lacks a baseline (CI)",
    )
    baseline_p.set_defaults(handler=cmd_baseline)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    fixtures_root = REPO / FIXTURES_REL
    if args.command == "list":
        return args.handler(fixtures_root, args.skill)
    if args.command in ("baseline", "accept"):
        return args.handler(args, fixtures_root)
    if args.command == "feedback" and args.run_dir:
        return args.handler(args, fixtures_root)
    if args.command == "feedback" and not args.case:
        print("error: pass --case or --run-dir", file=sys.stderr)
        return 2
    if args.command != "init" and not args.run_id:
        print("error: --run-id is required for this subcommand", file=sys.stderr)
        return 2
    return args.handler(args, fixtures_root)


if __name__ == "__main__":
    sys.exit(main())
