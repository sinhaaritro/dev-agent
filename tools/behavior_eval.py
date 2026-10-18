#!/usr/bin/env python3
"""Behavior/E2E harness: run prompt-level framework cases against a real install.

A behavior case is the same `case.json` + `repo/` contract as a skill-creator
case, so the two tools share one mental model:

    tests/fixtures/behavior/cases/<case>/case.json
    tests/fixtures/behavior/cases/<case>/repo/          # optional override
    tests/fixtures/behavior/profiles/<profile>/repo/    # shared starting state

`setup` performs the real install path (bootstrap + local skill copy) so the
prompt runs against a framework-installed tree, never a hand-made one.
Workspaces are throwaway:

    behavior-workspaces/<case>/<run-id>/repo/           # the consumer tree
    behavior-workspaces/<case>/<run-id>/transcript.md   # the agent transcript
    behavior-workspaces/<case>/<run-id>/result.json     # check results

Artifacts are a tiny machine-checkable DSL (scope defaults to `repo`):

    exists:repo:src/app.js          a path or glob has a match
    missing:repo:specs/             a path or glob has no match
    contains:repo:docs/README.md:X  a file contains the text
    not-contains:run:transcript.md:specs/
    contains:run:transcript.md:[STATUS:   (run: = the workspace dir)

Usage:
    python tools/behavior_eval.py list
    python tools/behavior_eval.py init --case b2-1-four-lanes
    python tools/behavior_eval.py run  --case b2-1-four-lanes --run-id <id>
    python tools/behavior_eval.py check --case b2-1-four-lanes --run-id <id>

`run` drives OpenCode headlessly; `init` and `check` are offline and
deterministic (tests/test_behavior_harness.py covers them).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FIXTURES_REL = Path("tests") / "fixtures" / "behavior"
DEFAULT_WORKSPACE = "behavior-workspaces"
DEFAULT_SETUP = ["bootstrap", "skills:auto-router,phase-protocol"]
SKILLS_SOURCE = REPO / "skills"
BOOTSTRAP_SCRIPT = SKILLS_SOURCE / "bootstrap" / "scripts" / "bootstrap.py"

ARTIFACT_KINDS = ("exists", "missing", "contains", "not-contains")
SCOPES = ("repo", "run")


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
class Case:
    name: str
    profile: str
    prompt: str
    setup: list[str] = field(default_factory=lambda: list(DEFAULT_SETUP))
    expectations: list[str] = field(default_factory=list)
    expected_artifacts: list[str] = field(default_factory=list)
    layer: str = "behavior"
    path: Path | None = None

    @classmethod
    def load(cls, fixtures_root: Path, name: str) -> Case:
        case_path = Path(fixtures_root) / "cases" / name / "case.json"
        if not case_path.is_file():
            raise SystemExit(f"error: case not found: {case_path}")
        try:
            data = json.loads(case_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"error: unreadable case {case_path}: {exc}") from exc
        for key in ("name", "profile", "prompt"):
            if not isinstance(data.get(key), str) or not data[key].strip():
                raise SystemExit(f"error: case {case_path} needs a non-empty {key!r}")
        if data.get("layer", "behavior") != "behavior":
            raise SystemExit(f"error: case {case_path} layer must be 'behavior'")
        return cls(
            name=data["name"],
            profile=data["profile"],
            prompt=data["prompt"],
            setup=list(data.get("setup", DEFAULT_SETUP)),
            expectations=list(data.get("expectations", [])),
            expected_artifacts=list(data.get("expected_artifacts", [])),
            layer=data.get("layer", "behavior"),
            path=case_path.parent,
        )

    @property
    def overlay(self) -> Path | None:
        """Case-local `repo/` overlay applied on top of the profile repo."""
        assert self.path is not None
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
        [sys.executable, str(BOOTSTRAP_SCRIPT), "--target", str(target)],
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


def _install_skills(target: Path, names: list[str]) -> None:
    for name in names:
        src = SKILLS_SOURCE / name
        if not src.is_dir():
            raise SystemExit(f"error: skill not found in skills/: {name}")
        dest = target / ".agents" / "skills" / name
        if dest.exists():
            shutil.rmtree(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dest)


def apply_setup(repo: Path, setup: list[str]) -> list[str]:
    """Run the case `setup` steps against `repo`; return human-readable notes."""
    notes: list[str] = []
    for step in setup:
        if step == "bootstrap":
            _run_bootstrap(repo)
            notes.append("bootstrap: installed AGENTS.md + .agents/rules/")
        elif step.startswith("skills:"):
            names = [n.strip() for n in step.split(":", 1)[1].split(",") if n.strip()]
            _install_skills(repo, names)
            notes.append("skills: " + ", ".join(names))
        elif step == "map":
            script = repo / ".agents" / "skills" / "map-generator" / "scripts" / "generate_map.py"
            if not script.is_file():
                raise SystemExit("error: setup step 'map' needs 'skills:map-generator' first")
            proc = subprocess.run(
                [sys.executable, str(script)],
                cwd=str(repo),
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if proc.returncode != 0:
                raise SystemExit("error: map generation failed\n" + proc.stdout + proc.stderr)
            notes.append("map: " + (proc.stdout or "").strip().splitlines()[-1])
        else:
            raise SystemExit(f"error: unknown setup step {step!r}")
    return notes


def run_dir(case: Case, run_id: str, workspace_root: Path) -> Path:
    return Path(workspace_root) / case.name / run_id


def init_run(
    case: Case,
    run_id: str,
    workspace_root: Path,
    force: bool = False,
) -> tuple[Path, list[str]]:
    target = run_dir(case, run_id, workspace_root)
    if target.exists():
        if not force:
            raise SystemExit(f"error: run exists: {target} (use --force)")
        shutil.rmtree(target)
    target.mkdir(parents=True)
    seed_repo(case, target / "repo")
    notes = apply_setup(target / "repo", case.setup)
    (target / "run.json").write_text(
        json.dumps(
            {
                "case": case.name,
                "run_id": run_id,
                "profile": case.profile,
                "setup": case.setup,
                "prompt": case.prompt,
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
    if kind in ("contains", "not-contains"):
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
        if text in body:
            found = True
            break
    if kind == "contains":
        return found, f"{'found' if found else 'missing'} {text!r} in {scope}:{rel}"
    if found is False and not any(p.is_file() for p in matches):
        return False, f"file not found: {scope}:{rel}"
    return (not found), f"{'found' if found else 'absent'} {text!r} in {scope}:{rel}"


def check_run(case: Case, run: Path) -> dict:
    checks = []
    for artifact in case.expected_artifacts:
        ok, detail = check_artifact(run, artifact)
        checks.append({"artifact": artifact, "passed": ok, "detail": detail})
    passed = all(item["passed"] for item in checks) and bool(checks)
    result = {
        "case": case.name,
        "passed": passed,
        "checks": checks,
        "checked_at": iso_now(),
    }
    (run / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def drive_opencode(run: Path, prompt: str, timeout: int, model: str | None) -> int:
    exe = shutil.which("opencode")
    if not exe:
        print("error: 'opencode' not found on PATH", file=sys.stderr)
        return 2
    cmd = [exe, "run", prompt, "--format", "json", "--auto", "--standalone"]
    if model:
        cmd += ["--model", model]
    started = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(run / "repo"),
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
    (run / "transcript.md").write_text(transcript, encoding="utf-8")
    (run / "opencode.stderr.txt").write_text(proc.stderr or "", encoding="utf-8")
    print(f"opencode exit: {proc.returncode} ({round(time.time() - started, 1)}s)")
    return 0 if proc.returncode == 0 else 1


def cmd_list(fixtures_root: Path) -> int:
    for name in list_cases(fixtures_root):
        print(name)
    return 0


def cmd_init(args: argparse.Namespace, fixtures_root: Path) -> int:
    case = Case.load(fixtures_root, args.case)
    run_id = args.run_id or new_run_id()
    target, notes = init_run(case, run_id, args.workspace_root, force=args.force)
    for note in notes:
        print(note)
    print(f"initialized: {target}")
    print(f"next: python tools/behavior_eval.py run --case {case.name} --run-id {run_id}")
    return 0


def cmd_run(args: argparse.Namespace, fixtures_root: Path) -> int:
    case = Case.load(fixtures_root, args.case)
    target = run_dir(case, args.run_id, args.workspace_root)
    if not (target / "repo").is_dir():
        print(f"error: run not initialized: {target} (run init first)", file=sys.stderr)
        return 2
    return drive_opencode(target, case.prompt, args.timeout, args.model)


def cmd_check(args: argparse.Namespace, fixtures_root: Path) -> int:
    case = Case.load(fixtures_root, args.case)
    target = run_dir(case, args.run_id, args.workspace_root)
    if not target.is_dir():
        print(f"error: run not found: {target}", file=sys.stderr)
        return 2
    result = check_run(case, target)
    for item in result["checks"]:
        print(f"{'PASS' if item['passed'] else 'FAIL'} {item['artifact']} - {item['detail']}")
    print(f"{'PASS' if result['passed'] else 'FAIL'} case {case.name}")
    return 0 if result["passed"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Behavior/E2E harness for prompt-level framework cases."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    list_p = sub.add_parser("list", help="list behavior cases")
    list_p.set_defaults(handler=cmd_list)

    for name, handler, helptext in (
        ("init", cmd_init, "seed a run from the case fixture + setup"),
        ("run", cmd_run, "drive OpenCode headlessly inside the seeded repo"),
        ("check", cmd_check, "evaluate expected_artifacts and write result.json"),
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
        if name == "run":
            p.add_argument("--timeout", type=int, default=900)
            p.add_argument("--model", default=None)
        p.set_defaults(handler=handler)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    fixtures_root = REPO / FIXTURES_REL
    if args.command == "list":
        return args.handler(fixtures_root)
    if args.command != "init" and not args.run_id:
        print("error: --run-id is required for this subcommand", file=sys.stderr)
        return 2
    return args.handler(args, fixtures_root)


if __name__ == "__main__":
    sys.exit(main())
