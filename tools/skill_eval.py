#!/usr/bin/env python3
"""Golden agent evals for the vendored skill-creator.

The skill-creator workflow is agent-driven: an agent creates/improves a skill,
writes eval cases, runs with-skill and baseline outputs, grades them, and
generates an HTML review for a human. This tool pins that workflow to one
canonical workspace so artifacts never scatter across repos or runs:

    skill-workspaces/skill-creator/<case>/<run-id>/

It owns the mechanics only:
    init    seed a sandbox from a committed case fixture
    run     drive OpenCode headlessly inside that sandbox
    check   normalize the layout, validate artifacts, build benchmark + review
    accept  record the accepted run as the case's golden baseline
    list    show cases and runs

The vendored skill-creator is never edited. Tests for this tool live in
tests/test_skill_eval_harness.py; the real OpenCode run is gated by SKILL_EVAL=1.

Usage:
    python tools/skill_eval.py init --case create-headings-skill
    python tools/skill_eval.py run --case create-headings-skill
    python tools/skill_eval.py check --case create-headings-skill --run-id <id>
    python tools/skill_eval.py iterate --case create-headings-skill --run-id <id>
    python tools/skill_eval.py accept --case create-headings-skill --run-id <id>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE_PARENT = "skill-workspaces"
WORKSPACE_SKILL = "skill-creator"
CASES_REL = Path("tests") / "fixtures" / "skill-creator" / "cases"
SKILL_CREATOR_REL = Path(".agents") / "skills" / "skill-creator"
IGNORE_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    ".venv-win",
    ".venv-linux",
    ".venv-macos",
    "node_modules",
}
BASELINE_CONFIGS = {"without_skill", "old_skill", "new_skill"}


def find_root() -> Path:
    """Walk up from this script until AGENTS.md (the repo-root marker) is found."""
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


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def tree_hash(path: Path) -> str:
    """Deterministic content hash of a directory tree (caches ignored)."""
    digest = hashlib.sha256()
    for entry in sorted(path.rglob("*")):
        if entry.is_dir():
            continue
        if entry.suffix == ".pyc":
            continue
        if any(part in IGNORE_DIRS for part in entry.parts):
            continue
        rel = entry.relative_to(path).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(entry.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


@dataclass
class Case:
    name: str
    mode: str
    skill_name: str
    prompt: str
    expectations: list[str] = field(default_factory=list)
    expected_artifacts: list[str] = field(default_factory=list)
    model: str | None = None
    baseline: str | None = None
    skip_description_optimization: bool = True

    @classmethod
    def load(cls, cases_root: Path, name: str) -> Case:
        path = cases_root / name / "case.json"
        if not path.is_file():
            raise SystemExit(f"error: case not found: {path}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"error: cannot read {path}: {exc}")
        for key in ("name", "mode", "skill_name", "prompt"):
            if not data.get(key):
                raise SystemExit(f"error: {path}: missing '{key}'")
        if data["mode"] not in ("create", "improve"):
            raise SystemExit(f"error: {path}: mode must be create or improve")
        return cls(
            name=data["name"],
            mode=data["mode"],
            skill_name=data["skill_name"],
            prompt=data["prompt"],
            expectations=list(data.get("expectations", [])),
            expected_artifacts=list(data.get("expected_artifacts", [])),
            model=data.get("model"),
            baseline=data.get("baseline"),
            skip_description_optimization=bool(
                data.get("skip_description_optimization", True)
            ),
        )


def resolve_run(workspace_root: Path, case: Case, run_id: str) -> Path:
    return workspace_root / WORKSPACE_SKILL / case.name / run_id


def resolve_case_dir(fixtures_root: Path, case: Case) -> Path:
    return fixtures_root / case.name


def copy_skill_creator(root: Path, dest: Path) -> None:
    source = root / SKILL_CREATOR_REL
    if not (source / "SKILL.md").is_file():
        raise SystemExit(f"error: vendored skill-creator not found at {source}")
    shutil.copytree(
        source,
        dest,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )


def override_block(case: Case, run_dir: Path) -> str:
    skill_dir = run_dir / "skill"
    evals = run_dir / "evals" / "evals.json"
    iteration = run_dir / "iteration-1"
    lines = [
        "",
        "## Skill-creator eval override (injected by tools/skill_eval.py)",
        "",
        f"- You are inside an eval sandbox. Workspace root: `{run_dir}`",
        f"- Write the target skill to: `{skill_dir}`",
        f"- Write eval cases to: `{evals}`",
        f"- Write iteration outputs to: `{iteration}`",
        "- Use OpenCode subagents. Do NOT call Claude Code.",
    ]
    if case.skip_description_optimization:
        lines.append(
            "- Skip the Description Optimization section: run_eval.py, "
            "run_loop.py, and improve_description.py require Claude Code."
        )
    lines += [
        "- Use this layout for every eval:",
        "  `iteration-1/eval-<id>-<name>/eval_metadata.json`",
        "  `iteration-1/eval-<id>-<name>/with_skill/run-1/outputs/`",
        "  `iteration-1/eval-<id>-<name>/with_skill/run-1/grading.json`",
        "  `iteration-1/eval-<id>-<name>/without_skill/run-1/outputs/`",
        "  `iteration-1/eval-<id>-<name>/without_skill/run-1/grading.json`",
        "- Copy `eval_metadata.json` into each `run-1/` directory too.",
        "- Do not package the skill. Stop after generating the static review HTML;",
        "  `tools/skill_eval.py check` regenerates `review.html` for you.",
        "",
    ]
    return "\n".join(lines)


def write_override(sandbox: Path, case: Case, run_dir: Path) -> None:
    agents = sandbox / "AGENTS.md"
    prefix = ""
    if agents.is_file():
        prefix = agents.read_text(encoding="utf-8").rstrip() + "\n"
    agents.write_text(prefix + override_block(case, run_dir), encoding="utf-8")


def init_run(
    root: Path,
    case: Case,
    run_id: str,
    workspace_root: Path,
    fixtures_root: Path,
    force: bool = False,
) -> Path:
    run_dir = resolve_run(workspace_root, case, run_id)
    if run_dir.exists():
        if not force:
            raise SystemExit(f"error: run already exists: {run_dir} (use --force)")
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True)

    case_dir = resolve_case_dir(fixtures_root, case)
    repo = case_dir / "repo"
    if not repo.is_dir():
        raise SystemExit(f"error: case fixture has no repo/: {repo}")
    sandbox = run_dir / "sandbox"
    shutil.copytree(repo, sandbox)

    copy_skill_creator(root, sandbox / ".agents" / "skills" / "skill-creator")

    skill_dir = run_dir / "skill"
    if case.mode == "improve":
        if not case.baseline:
            raise SystemExit(f"error: improve case {case.name} has no 'baseline'")
        baseline = sandbox / case.baseline
        if not baseline.is_dir():
            raise SystemExit(f"error: baseline not found in fixture: {baseline}")
        shutil.copytree(baseline, run_dir / "skill-snapshot")
        shutil.copytree(baseline, skill_dir)
    else:
        skill_dir.mkdir()

    (run_dir / "evals").mkdir()
    write_override(sandbox, case, run_dir)

    metadata = {
        "case": case.name,
        "mode": case.mode,
        "run_id": run_id,
        "created_at": iso_now(),
        "prompt": case.prompt,
        "prompt_sha256": sha256_text(case.prompt),
        "skill_name": case.skill_name,
        "model": case.model or os.environ.get("SKILL_EVAL_MODEL"),
        "skill_creator": str(SKILL_CREATOR_REL),
        "input_tree_hash": tree_hash(sandbox),
    }
    (run_dir / "run.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    return run_dir


def update_run_json(run_dir: Path, **updates) -> None:
    path = run_dir / "run.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    data.update(updates)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def normalize_layout(run_dir: Path) -> list[str]:
    """Make the agent's output match what the vendored scripts expect.

    Accepts both `<config>/outputs/` and `<config>/run-N/outputs/`, and copies
    eval_metadata.json into every run dir (the viewer looks there first).
    Returns a list of human-readable changes.
    """
    changes: list[str] = []
    for iteration in sorted(run_dir.glob("iteration-*")):
        if not iteration.is_dir():
            continue
        for eval_dir in sorted(iteration.glob("eval-*")):
            metadata = eval_dir / "eval_metadata.json"
            for config in sorted(p for p in eval_dir.iterdir() if p.is_dir()):
                if config.name in ("inputs", "outputs"):
                    continue
                legacy_outputs = config / "outputs"
                if legacy_outputs.is_dir() and not (config / "run-1").exists():
                    run1 = config / "run-1"
                    run1.mkdir()
                    shutil.move(str(legacy_outputs), str(run1 / "outputs"))
                    for name in ("grading.json", "timing.json"):
                        if (config / name).is_file():
                            shutil.move(str(config / name), str(run1 / name))
                    changes.append(
                        f"normalized {config.relative_to(run_dir)} -> run-1/"
                    )
                for run1 in sorted(config.glob("run-*")):
                    if (
                        metadata.is_file()
                        and not (run1 / "eval_metadata.json").exists()
                    ):
                        shutil.copy2(metadata, run1 / "eval_metadata.json")
    return changes


def parse_frontmatter(text: str) -> dict:
    """Minimal stdlib frontmatter reader for name/description (no PyYAML)."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    body = text[3:end].strip("\n")
    data: dict = {}
    key = None
    for raw in body.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line[:1].isspace() and key:
            data[key] = (str(data.get(key, "")) + " " + line.strip()).strip()
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            data[key] = value
    return data


def structural_checks(run_dir: Path, case: Case) -> list[dict]:
    checks: list[dict] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    skill = run_dir / "skill" / "SKILL.md"
    add("skill/SKILL.md exists", skill.is_file())
    if skill.is_file():
        front = parse_frontmatter(skill.read_text(encoding="utf-8"))
        add(
            "skill frontmatter has name",
            bool(front.get("name")),
            str(front.get("name", "")),
        )
        add(
            "skill frontmatter has description",
            bool(front.get("description")),
            str(front.get("description", ""))[:120],
        )

    evals_path = run_dir / "evals" / "evals.json"
    add("evals/evals.json exists", evals_path.is_file())
    if evals_path.is_file():
        try:
            evals = json.loads(evals_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            add("evals/evals.json parses", False, str(exc))
        else:
            items = evals.get("evals") if isinstance(evals, dict) else None
            add("evals list present", isinstance(items, list) and bool(items))
            if isinstance(items, list):
                bad = [
                    i
                    for i, item in enumerate(items)
                    if not isinstance(item, dict)
                    or not item.get("prompt")
                    or not item.get("expected_output")
                ]
                add(
                    "every eval has prompt + expected_output",
                    not bad,
                    f"bad indexes: {bad}",
                )

    iterations = sorted(run_dir.glob("iteration-*"))
    add("at least one iteration", bool(iterations))
    for iteration in iterations:
        eval_dirs = sorted(iteration.glob("eval-*"))
        add(f"{iteration.name}: has eval-* dirs", bool(eval_dirs))
        for eval_dir in eval_dirs:
            metadata = eval_dir / "eval_metadata.json"
            add(f"{eval_dir.name}: eval_metadata.json", metadata.is_file())
            configs = [p.name for p in eval_dir.iterdir() if p.is_dir()]
            has_with = "with_skill" in configs
            has_baseline = any(c in BASELINE_CONFIGS for c in configs)
            add(
                f"{eval_dir.name}: with_skill + baseline",
                has_with and has_baseline,
                ", ".join(configs),
            )
            for config in configs:
                if config in ("inputs", "outputs"):
                    continue
                config_dir = eval_dir / config
                runs = sorted(config_dir.glob("run-*"))
                add(f"{eval_dir.name}/{config}: run-* exists", bool(runs))
                for run in runs:
                    add(
                        f"{eval_dir.name}/{config}/{run.name}: outputs exists",
                        (run / "outputs").is_dir(),
                    )
                    add(
                        f"{eval_dir.name}/{config}/{run.name}: eval_metadata.json",
                        (run / "eval_metadata.json").is_file(),
                    )
                    grading = run / "grading.json"
                    add(
                        f"{eval_dir.name}/{config}/{run.name}: grading.json",
                        grading.is_file(),
                    )
                    if grading.is_file():
                        try:
                            data = json.loads(grading.read_text(encoding="utf-8"))
                        except (OSError, json.JSONDecodeError) as exc:
                            add("grading parses", False, str(exc))
                            continue
                        expectations = data.get("expectations")
                        add(
                            "grading.expectations is a list",
                            isinstance(expectations, list) and bool(expectations),
                        )
                        if isinstance(expectations, list):
                            bad = [
                                e
                                for e in expectations
                                if not isinstance(e, dict)
                                or "text" not in e
                                or "passed" not in e
                                or "evidence" not in e
                            ]
                            add(
                                "grading uses text/passed/evidence",
                                not bad,
                                f"{len(bad)} bad item(s)",
                            )
                        summary = data.get("summary")
                        add(
                            "grading.summary has pass_rate + total",
                            isinstance(summary, dict)
                            and "pass_rate" in summary
                            and "total" in summary,
                        )
    return checks


def golden_checks(run_dir: Path, case: Case, fixtures_root: Path) -> list[dict]:
    """Compare a run against the accepted golden baseline, when one exists."""
    expected = resolve_case_dir(fixtures_root, case) / "expected"
    golden_path = expected / "golden.json"
    if not golden_path.is_file():
        return []
    try:
        golden = json.loads(golden_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [{"name": "golden.json parses", "ok": False, "detail": str(exc)}]
    run_path = run_dir / "run.json"
    run_meta = (
        json.loads(run_path.read_text(encoding="utf-8")) if run_path.is_file() else {}
    )
    return [
        {
            "name": "golden: input tree matches",
            "ok": golden.get("input_tree_hash") == run_meta.get("input_tree_hash"),
            "detail": "re-accept after changing the fixture or skill-creator",
        },
        {
            "name": "golden: prompt matches",
            "ok": golden.get("prompt_sha256") == run_meta.get("prompt_sha256"),
            "detail": "re-accept after changing the case prompt",
        },
        {
            "name": "golden: skill snapshot exists",
            "ok": (expected / "skill" / "SKILL.md").is_file(),
            "detail": str(expected / "skill" / "SKILL.md"),
        },
        {
            "name": "golden: evals snapshot exists",
            "ok": (expected / "evals.json").is_file(),
            "detail": str(expected / "evals.json"),
        },
    ]


def run_script(
    cmd: list[str], cwd: Path, timeout: int = 120
) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )


def script_checks(root: Path, run_dir: Path, case: Case) -> list[dict]:
    checks: list[dict] = []
    skill_creator = root / SKILL_CREATOR_REL
    iterations = sorted(run_dir.glob("iteration-*"))
    if not iterations:
        return [{"name": "scripts: no iteration", "ok": False, "detail": ""}]
    for iteration in iterations:
        proc = run_script(
            [
                sys.executable,
                "-m",
                "scripts.aggregate_benchmark",
                str(iteration),
                "--skill-name",
                case.skill_name,
            ],
            cwd=skill_creator,
        )
        ok = proc.returncode == 0 and (iteration / "benchmark.json").is_file()
        checks.append(
            {
                "name": f"{iteration.name}: aggregate_benchmark",
                "ok": ok,
                "detail": (proc.stdout + proc.stderr).strip()[-400:],
            }
        )
    last = iterations[-1]
    benchmark = last / "benchmark.json"
    review = run_dir / "review.html"
    cmd = [
        sys.executable,
        str(skill_creator / "eval-viewer" / "generate_review.py"),
        str(last),
        "--skill-name",
        case.skill_name,
        "--static",
        str(review),
    ]
    if benchmark.is_file():
        cmd += ["--benchmark", str(benchmark)]
    if len(iterations) > 1:
        cmd += ["--previous-workspace", str(iterations[-2])]
    proc = run_script(cmd, cwd=root)
    checks.append(
        {
            "name": f"{last.name}: static review",
            "ok": proc.returncode == 0 and review.is_file(),
            "detail": (proc.stdout + proc.stderr).strip()[-400:],
        }
    )
    return checks


def write_check(run_dir: Path, checks: list[dict]) -> bool:
    ok = all(c["ok"] for c in checks)
    payload = {"ok": ok, "checked_at": iso_now(), "checks": checks}
    (run_dir / "check.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    for check in checks:
        mark = "ok " if check["ok"] else "FAIL"
        detail = f" - {check['detail']}" if check["detail"] and not check["ok"] else ""
        print(f"{mark}: {check['name']}{detail}")
    print(f"\n{'PASS' if ok else 'FAIL'}: {len(checks)} check(s)")
    return ok


def next_iteration(run_dir: Path) -> int:
    numbers = []
    for path in run_dir.glob("iteration-*"):
        suffix = path.name.split("-", 1)[-1]
        if suffix.isdigit():
            numbers.append(int(suffix))
    return max(numbers, default=0) + 1


def iteration_prompt(case: Case, run_dir: Path, iteration: int, feedback: Path) -> str:
    previous = run_dir / f"iteration-{iteration - 1}"
    return (
        f"{case.prompt}\n\n"
        f"This is iteration {iteration}. Read the feedback at {feedback} and the "
        f"previous iteration at {previous}. Revise {run_dir / 'skill'} in place, "
        f"then write {run_dir / f'iteration-{iteration}'} using the same layout. "
        "Stop after the outputs and grading; tools/skill_eval.py check will "
        "generate review.html."
    )


def drive_opencode(
    run_dir: Path,
    prompt: str,
    model: str | None,
    timeout: int,
    label: str,
) -> int:
    exe = shutil.which("opencode")
    if not exe:
        print("error: 'opencode' not found on PATH", file=sys.stderr)
        return 2

    cmd = [exe, "run", prompt, "--format", "json", "--auto", "--standalone"]
    if model:
        cmd += ["--model", model]

    started = time.time()
    update_run_json(
        run_dir,
        started_at=iso_now(),
        command=cmd,
        model=model,
        status="running",
        last_label=label,
    )
    print(f"running {label}: {run_dir}")
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(run_dir / "sandbox"),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        update_run_json(
            run_dir,
            status="timeout",
            finished_at=iso_now(),
            duration_seconds=round(time.time() - started, 1),
        )
        print(f"error: opencode timed out after {timeout}s", file=sys.stderr)
        return 1

    stem = "opencode" if label == "run" else f"opencode.{label}"
    (run_dir / f"{stem}.stdout.jsonl").write_text(proc.stdout or "", encoding="utf-8")
    (run_dir / f"{stem}.stderr.txt").write_text(proc.stderr or "", encoding="utf-8")
    update_run_json(
        run_dir,
        status="passed" if proc.returncode == 0 else "failed",
        exit_code=proc.returncode,
        finished_at=iso_now(),
        duration_seconds=round(time.time() - started, 1),
    )
    print(f"opencode exit: {proc.returncode}")
    return 0 if proc.returncode == 0 else 1


def cmd_init(args: argparse.Namespace, root: Path) -> int:
    case = Case.load(args.fixtures_root, args.case)
    run_id = args.run_id or new_run_id()
    run_dir = init_run(
        root,
        case,
        run_id,
        args.workspace_root,
        args.fixtures_root,
        force=args.force,
    )
    print(f"initialized: {run_dir}")
    print(f"next: python tools/skill_eval.py run --case {case.name} --run-id {run_id}")
    return 0


def cmd_run(args: argparse.Namespace, root: Path) -> int:
    case = Case.load(args.fixtures_root, args.case)
    run_id = args.run_id or new_run_id()
    run_dir = resolve_run(args.workspace_root, case, run_id)
    if not run_dir.is_dir():
        run_dir = init_run(root, case, run_id, args.workspace_root, args.fixtures_root)
        print(f"initialized: {run_dir}")
    if not (run_dir / "sandbox").is_dir():
        print(f"error: run has no sandbox: {run_dir}", file=sys.stderr)
        return 2

    model = args.model or case.model or os.environ.get("SKILL_EVAL_MODEL")
    rc = drive_opencode(run_dir, case.prompt, model, args.timeout, "run")
    print(
        f"next: python tools/skill_eval.py check --case {case.name} --run-id {run_id}"
    )
    return rc


def cmd_iterate(args: argparse.Namespace, root: Path) -> int:
    case = Case.load(args.fixtures_root, args.case)
    run_dir = resolve_run(args.workspace_root, case, args.run_id)
    if not run_dir.is_dir():
        print(f"error: run not found: {run_dir}", file=sys.stderr)
        return 2
    if not (run_dir / "sandbox").is_dir():
        print(f"error: run has no sandbox: {run_dir}", file=sys.stderr)
        return 2
    feedback = Path(args.feedback) if args.feedback else run_dir / "feedback.json"
    if not feedback.is_file():
        print(
            f"error: feedback not found: {feedback} (download it from review.html)",
            file=sys.stderr,
        )
        return 2
    iteration = args.iteration or next_iteration(run_dir)
    if iteration <= 1:
        print("error: iteration must be 2 or later", file=sys.stderr)
        return 2
    target = run_dir / f"iteration-{iteration}"
    if target.exists():
        if not args.force:
            print(f"error: {target.name} already exists (use --force)", file=sys.stderr)
            return 2
        shutil.rmtree(target)

    model = args.model or case.model or os.environ.get("SKILL_EVAL_MODEL")
    prompt = iteration_prompt(case, run_dir, iteration, feedback)
    rc = drive_opencode(run_dir, prompt, model, args.timeout, f"iteration-{iteration}")
    print(
        f"next: python tools/skill_eval.py check --case {case.name} --run-id {args.run_id}"
    )
    return rc


def cmd_check(args: argparse.Namespace, root: Path) -> int:
    case = Case.load(args.fixtures_root, args.case)
    run_dir = resolve_run(args.workspace_root, case, args.run_id)
    if not run_dir.is_dir():
        print(f"error: run not found: {run_dir}", file=sys.stderr)
        return 2

    changes = normalize_layout(run_dir)
    for change in changes:
        print(f"layout: {change}")

    checks = structural_checks(run_dir, case)
    checks += golden_checks(run_dir, case, args.fixtures_root)
    if not args.no_scripts and all(c["ok"] for c in checks):
        checks += script_checks(root, run_dir, case)
    ok = write_check(run_dir, checks)
    print(f"artifacts: {run_dir}")
    if (run_dir / "review.html").is_file():
        print(f"review: {run_dir / 'review.html'}")
    return 0 if ok else 1


def cmd_accept(args: argparse.Namespace, root: Path) -> int:
    case = Case.load(args.fixtures_root, args.case)
    run_dir = resolve_run(args.workspace_root, case, args.run_id)
    check_path = run_dir / "check.json"
    if not check_path.is_file():
        print(f"error: run has no check.json: {run_dir}", file=sys.stderr)
        return 2
    check = json.loads(check_path.read_text(encoding="utf-8"))
    if not check.get("ok") and not args.force:
        print(
            "error: check did not pass (use --force to accept anyway)", file=sys.stderr
        )
        return 1

    case_dir = resolve_case_dir(args.fixtures_root, case)
    expected = case_dir / "expected"
    if expected.exists():
        shutil.rmtree(expected)
    (expected / "skill").parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(run_dir / "skill", expected / "skill")
    evals_src = run_dir / "evals" / "evals.json"
    if evals_src.is_file():
        shutil.copy2(evals_src, expected / "evals.json")

    run_meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    golden = {
        "case": case.name,
        "run_id": args.run_id,
        "approved_at": iso_now(),
        "input_tree_hash": run_meta.get("input_tree_hash"),
        "prompt_sha256": run_meta.get("prompt_sha256"),
        "model": run_meta.get("model"),
        "skill_name": case.skill_name,
        "artifacts": [
            "skill/SKILL.md",
            "evals/evals.json",
        ]
        + [p.name for p in sorted(run_dir.glob("iteration-*"))],
    }
    (expected / "golden.json").write_text(
        json.dumps(golden, indent=2) + "\n", encoding="utf-8"
    )
    (expected / "manifest.json").write_text(
        json.dumps({"artifacts": golden["artifacts"]}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"accepted: {run_dir}")
    print(f"golden:   {expected / 'golden.json'}")
    return 0


def cmd_list(args: argparse.Namespace, root: Path) -> int:
    if not args.fixtures_root.is_dir():
        print(f"error: cases not found: {args.fixtures_root}", file=sys.stderr)
        return 2
    for case_path in sorted(p for p in args.fixtures_root.iterdir() if p.is_dir()):
        case_file = case_path / "case.json"
        if not case_file.is_file():
            continue
        print(case_path.name)
        runs = args.workspace_root / WORKSPACE_SKILL / case_path.name
        if runs.is_dir():
            for run in sorted(p for p in runs.iterdir() if p.is_dir()):
                print(f"  {run.name}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=None,
        help="workspace root (default: <repo>/skill-workspaces)",
    )
    parser.add_argument(
        "--fixtures-root",
        type=Path,
        default=None,
        help="case fixtures root (default: <repo>/tests/fixtures/skill-creator/cases)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_case(p: argparse.ArgumentParser) -> None:
        p.add_argument("--case", required=True)

    init_p = sub.add_parser("init", help="seed a run sandbox from a case fixture")
    add_case(init_p)
    init_p.add_argument("--run-id", default=None)
    init_p.add_argument("--force", action="store_true")
    init_p.set_defaults(func=cmd_init)

    run_p = sub.add_parser("run", help="drive OpenCode inside the sandbox")
    add_case(run_p)
    run_p.add_argument("--run-id", default=None)
    run_p.add_argument("--model", default=None)
    run_p.add_argument("--timeout", type=int, default=900)
    run_p.set_defaults(func=cmd_run)

    iterate_p = sub.add_parser(
        "iterate", help="revise from feedback.json into the next iteration"
    )
    add_case(iterate_p)
    iterate_p.add_argument("--run-id", required=True)
    iterate_p.add_argument("--iteration", type=int, default=None)
    iterate_p.add_argument("--feedback", default=None)
    iterate_p.add_argument("--model", default=None)
    iterate_p.add_argument("--timeout", type=int, default=900)
    iterate_p.add_argument("--force", action="store_true")
    iterate_p.set_defaults(func=cmd_iterate)

    check_p = sub.add_parser(
        "check", help="validate artifacts + build benchmark/review"
    )
    add_case(check_p)
    check_p.add_argument("--run-id", required=True)
    check_p.add_argument("--no-scripts", action="store_true")
    check_p.set_defaults(func=cmd_check)

    accept_p = sub.add_parser(
        "accept", help="record a checked run as the golden baseline"
    )
    add_case(accept_p)
    accept_p.add_argument("--run-id", required=True)
    accept_p.add_argument("--force", action="store_true")
    accept_p.set_defaults(func=cmd_accept)

    list_p = sub.add_parser("list", help="list cases and runs")
    list_p.set_defaults(func=cmd_list)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    root = find_root()
    args.workspace_root = args.workspace_root or root / WORKSPACE_PARENT
    args.fixtures_root = args.fixtures_root or root / CASES_REL
    if not args.workspace_root.is_absolute():
        args.workspace_root = (root / args.workspace_root).resolve()
    if not args.fixtures_root.is_absolute():
        args.fixtures_root = (root / args.fixtures_root).resolve()
    return args.func(args, root)


if __name__ == "__main__":
    sys.exit(main())
