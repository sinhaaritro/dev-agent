#!/usr/bin/env python3
"""dev-agent installer - set up the Dev Agent framework in a target repo.

Two independent jobs:

1. ``setup`` (stdlib-only, offline, the default). Copies this skill's
   ``reference/`` seeds (AGENTS.md, .gitignore merge, rules, coder, IDE
   dotfiles) and the bundled ``runtime/`` into the target, then writes
   ``.agents/.devagent.json``. Atomic: the runtime is staged in
   ``.agents/scripts/.devagent.tmp/`` and renamed into place, and the manifest
   is written last so an interrupted install is detectable.

2. ``setup --skills <spec>`` (needs ``npx``). Opt-in; delegates the wrapper
   skills to ``npx skills add`` and never copies skill folders itself.

Commands:
    python <skill>/scripts/bootstrap.py setup [--target DIR] [--dry-run]
                    [--scope project|global] [--agent NAME]
                    [--skills mandatory|all|<comma-list>]
    python <skill>/scripts/bootstrap.py --check [--target DIR]
    python <skill>/scripts/bootstrap.py --update [--target DIR] [--dry-run]

``setup`` is the default command: passing only ``--target DIR`` behaves as
``setup``. Run with ``--dry-run`` to preview without writing.

Per-file report:
    seeds, dry-run:  new: <rel>  ok: <rel>  overwrite: <rel>  append: <rel>
    seeds, install:  installed: <rel>  unchanged: <rel>  updated: <rel>  appended: <rel>
    runtime:         installed/unchanged/updated: .agents/scripts/devagent/<rel>
    manifest:        wrote/unchanged: .agents/.devagent.json
Summary (setup):     dev-agent setup complete: <N> installed, <M> updated, <K> unchanged

``--check`` prints ``ok`` / ``stale`` / ``modified`` / ``missing`` / ``orphan``
lines and exits 1 on any drift (a CI guard you can wire into hooks or CI).

Exit codes: 0 = success / clean; 1 = error, drift, or bad target; 2 = refused
(the packaged runtime is older than the one already installed).
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# (path inside reference/, path inside the target repo)
SEED_FILES = (
    ("AGENTS.md", "AGENTS.md"),
    (".gitignore", ".gitignore"),
    ("rules/dev-agent-framework.md", ".agents/rules/dev-agent-framework.md"),
    ("agents/coder.md", ".agents/agents/coder.md"),
    (".cursorrules", ".cursorrules"),
    (".windsurfrules", ".windsurfrules"),
)

RUNTIME_SRC_REL = ("runtime", "devagent")
RUNTIME_DEST_REL = (".agents", "scripts", "devagent")
SCRIPTS_REL = (".agents", "scripts")
STAGING_DEST_REL = (".agents", "scripts", ".devagent.tmp")
MANIFEST_REL = (".agents", ".devagent.json")
DESCRIPTOR_NAME = "skills.json"

SCHEMA = 1
FRAMEWORK = "dev-agent"
PYTHON_REQUIRES = ">=3.10"
SOURCE_CATALOG = "skills.sh.json"
LOCK_FILE = "skills-lock.json"
BLOCK_SEEDS = ("AGENTS.md",)
BLOCK_BEGIN = "<!-- dev-agent:begin -->"
BLOCK_END = "<!-- dev-agent:end -->"
FRAMEWORK_HEADING = "# DEV AGENT"


# --------------------------------------------------------------------------- #
# discovery helpers
# --------------------------------------------------------------------------- #


def find_skill_root() -> Path:
    """Walk up from this script until the skill root (the dir holding reference/)."""
    current = Path(__file__).resolve().parent
    while True:
        if (current / "reference").is_dir():
            return current
        parent = current.parent
        if parent == current:
            sys.exit(
                "error: reference/ folder not found above "
                + str(Path(__file__).resolve())
            )
        current = parent


def _load_json(path: Path) -> dict | None:
    """Parse a JSON object, returning None for a missing or malformed file."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def is_framework_checkout(root: Path) -> bool:
    """True when ``root`` is the framework's own source checkout.

    The marker is structural, not a grouping name: the repo carries the skills
    catalog *and* ships this skill's source at ``skills/dev-agent``. A consumer
    install keeps the skill under ``.agents/skills/dev-agent``, and a consumer
    catalog (grouping its own skills) lacks that source path, so neither matches.
    """
    if not (root / SOURCE_CATALOG).is_file():
        return False
    return (root / "skills" / FRAMEWORK / "SKILL.md").is_file()


def lock_installs_framework(lock: Path) -> bool:
    """True when a ``skills-lock.json`` records this framework as installed."""
    data = _load_json(lock)
    installed = data.get("skills") if data else None
    return isinstance(installed, dict) and FRAMEWORK in installed


def find_source_repo_root(target: Path) -> Path | None:
    """Walk up from ``target`` to the nearest framework source checkout.

    A repo is the source tree when it has the catalog and ``skills/dev-agent``.
    A consumer repo is recognised by ``skills-lock.json`` recording a dev-agent
    install, and is never the source tree. ``AGENTS.md`` is deliberately not a
    marker: consumer repos carry their own, and setup writes one into every
    installed repo. Walking stops at a repo boundary (``.git``) or the filesystem
    root, so a nested clone is never mistaken for its parent.
    """
    current = target.resolve()
    while True:
        if is_framework_checkout(current):
            return current
        if lock_installs_framework(current / LOCK_FILE):
            return None
        if (current / ".git").exists():
            return None
        parent = current.parent
        if parent == current:
            return None
        current = parent


def read_runtime_version(skill_root: Path) -> str:
    """The bundled runtime's version, read from its __init__.py (no import)."""
    init = skill_root.joinpath(*RUNTIME_SRC_REL) / "__init__.py"
    if not init.is_file():
        sys.exit("error: bundled runtime not found at " + str(init))
    match = re.search(
        r'^__version__\s*=\s*["\']([^"\']+)["\']',
        init.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    if not match:
        sys.exit("error: cannot read __version__ from " + str(init))
    return match.group(1)


def verify_seeds(skill_root: Path) -> None:
    missing = [
        rel for rel, _ in SEED_FILES if not (skill_root / "reference" / rel).is_file()
    ]
    if missing:
        sys.exit(
            "error: missing seed file(s) in reference/: "
            + ", ".join("reference/" + rel for rel in missing)
        )


def iter_runtime_source(skill_root: Path) -> dict:
    """Bundled runtime bytes keyed by ``devagent/<relpath>`` (skips caches)."""
    src = skill_root.joinpath(*RUNTIME_SRC_REL)
    if not src.is_dir():
        sys.exit("error: bundled runtime not found at " + str(src))
    out = {}
    for path in sorted(src.rglob("*")):
        if path.is_dir():
            continue
        parts = path.relative_to(src).parts
        if "__pycache__" in parts or path.suffix == ".pyc":
            continue
        rel = "devagent/" + path.relative_to(src).as_posix()
        out[rel] = path.read_bytes()
    return out


def iter_runtime_actual(target: Path) -> dict:
    """Runtime bytes currently installed, keyed the same way as the source."""
    dest = target.joinpath(*RUNTIME_DEST_REL)
    if not dest.is_dir():
        return {}
    out = {}
    for path in sorted(dest.rglob("*")):
        if path.is_dir():
            continue
        parts = path.relative_to(dest).parts
        if "__pycache__" in parts or path.suffix in (".pyc", ".bak"):
            continue
        rel = "devagent/" + path.relative_to(dest).as_posix()
        out[rel] = path.read_bytes()
    return out


def remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


# --------------------------------------------------------------------------- #
# hashing / manifest
# --------------------------------------------------------------------------- #


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def read_manifest(target: Path) -> dict | None:
    manifest = target.joinpath(*MANIFEST_REL)
    if not manifest.is_file():
        return None
    try:
        return json.loads(manifest.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def build_manifest(runtime_files: dict, version: str, scope: str, agent: str) -> dict:
    return {
        "schema": SCHEMA,
        "framework": FRAMEWORK,
        "runtime_version": version,
        "python": PYTHON_REQUIRES,
        "scope": scope,
        "agent": agent,
        "installed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": {
            "channel": "skills",
            "installed_by": "skills/dev-agent",
            "skills_version": version,
        },
        "files": {
            rel: sha256_bytes(data) for rel, data in sorted(runtime_files.items())
        },
    }


def write_manifest(target: Path, manifest: dict) -> None:
    path = target.joinpath(*MANIFEST_REL)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def version_tuple(value: str) -> tuple:
    parts = re.findall(r"\d+", value or "")
    return tuple(int(p) for p in parts) if parts else (0,)


# --------------------------------------------------------------------------- #
# seed planning (unchanged mechanics, kept for parity)
# --------------------------------------------------------------------------- #


def parse_gitignore(content: str):
    """Split gitignore content into (header_comment, [pattern_lines])."""
    header = ""
    patterns = []
    for line in content.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            if not header:
                header = s
        else:
            patterns.append(s)
    return header, patterns


def _managed_block_span(text: str) -> tuple[int, int] | None:
    """Start/end offsets of the managed block (markers included), if present."""
    start = text.find(BLOCK_BEGIN)
    if start == -1:
        return None
    end = text.find(BLOCK_END, start + len(BLOCK_BEGIN))
    if end == -1:
        return None
    return start, end + len(BLOCK_END)


def _split_template(template: str) -> tuple[str, str]:
    """Split the seed into its project scaffold and the framework contract.

    The scaffold (title, description, stack, repo map, commands) is written only
    for a new file; the contract (from ``FRAMEWORK_HEADING`` on) is what gets
    appended to an existing file so a project never ends up with two copies.
    """
    idx = template.find(FRAMEWORK_HEADING)
    if idx == -1:
        return "", template
    return template[:idx], template[idx:]


def _managed_block(framework: str) -> str:
    """Wrap the framework contract in markers so later runs can replace it."""
    return BLOCK_BEGIN + "\n" + framework.strip("\n") + "\n" + BLOCK_END


def plan_seeds(skill_root: Path, target: Path) -> list:
    results = []  # (seed_rel, dest_rel, status)
    for seed_rel, dest_rel in SEED_FILES:
        src = skill_root / "reference" / seed_rel
        dst = target / dest_rel
        if seed_rel == ".gitignore" and dst.exists():
            _h, seed_patterns = parse_gitignore(src.read_text(encoding="utf-8"))
            _eh, existing_patterns = parse_gitignore(dst.read_text(encoding="utf-8"))
            missing = [p for p in seed_patterns if p not in set(existing_patterns)]
            status = "append" if missing else "ok"
        elif seed_rel in BLOCK_SEEDS and dst.exists():
            status = _block_status(src, dst)
        elif not dst.exists():
            status = "new"
        elif dst.is_file() and dst.read_bytes() == src.read_bytes():
            status = "ok"
        else:
            status = "overwrite"
        results.append((seed_rel, dest_rel, status))
    return results


def _block_status(src: Path, dst: Path) -> str:
    """Decide how the framework contract relates to the file already on disk."""
    existing = dst.read_text(encoding="utf-8")
    _scaffold, framework = _split_template(src.read_text(encoding="utf-8"))
    block = _managed_block(framework)
    span = _managed_block_span(existing)
    if span is not None:
        start, end = span
        return "ok" if existing[start:end] == block else "update"
    if framework.strip("\n") and framework.strip("\n") in existing:
        # A repo seeded before markers existed: adopt the same text in place.
        return "update"
    return "append"


def _write_managed_block(dst: Path, template: str) -> None:
    """Write only the framework contract, appending or replacing in place.

    A new file gets the full template (project scaffold + contract). An existing
    file keeps its content untouched: a legacy unmarked contract is wrapped where
    it already sits, and anything else gets the contract appended once.
    """
    scaffold, framework = _split_template(template)
    block = _managed_block(framework)
    marker = framework.strip("\n")
    existing = dst.read_text(encoding="utf-8") if dst.exists() else ""
    span = _managed_block_span(existing)
    if span is not None:
        start, end = span
        text = existing[:start] + block + existing[end:]
    elif not dst.exists():
        body = scaffold.rstrip("\n")
        text = (body + "\n\n" if body else "") + block + "\n"
    elif marker and marker in existing:
        at = existing.index(marker)
        text = existing[:at] + block + existing[at + len(marker) :]
    else:
        body = existing.rstrip("\n")
        text = (body + "\n\n" if body else "") + block + "\n"
    dst.write_text(text, encoding="utf-8")


def write_seed(
    skill_root: Path, target: Path, seed_rel: str, dest_rel: str, status: str
) -> None:
    src = skill_root / "reference" / seed_rel
    dst = target / dest_rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    if seed_rel in BLOCK_SEEDS:
        _write_managed_block(dst, src.read_text(encoding="utf-8"))
    elif status == "append":
        seed_header, seed_patterns = parse_gitignore(src.read_text(encoding="utf-8"))
        existing = dst.read_text(encoding="utf-8")
        _eh, existing_patterns = parse_gitignore(existing)
        missing = [p for p in seed_patterns if p not in set(existing_patterns)]
        block_lines = []
        if seed_header and seed_header not in existing:
            block_lines.append(seed_header)
        block_lines.extend(missing)
        block = "\n".join(block_lines) + "\n"
        if existing and not existing.endswith("\n"):
            existing += "\n"
        dst.write_text(existing + block, encoding="utf-8")
    else:
        shutil.copyfile(src, dst)


# --------------------------------------------------------------------------- #
# runtime install
# --------------------------------------------------------------------------- #


def stage_runtime(target: Path, runtime_files: dict) -> None:
    """Write the runtime to .devagent.tmp/, then atomically rename into place."""
    scripts = target / ".agents" / "scripts"
    stage = target.joinpath(*STAGING_DEST_REL)
    if stage.exists():
        remove_path(stage)
    for rel, data in runtime_files.items():
        inner = rel.split("/", 1)[1] if rel.startswith("devagent/") else rel
        out = stage.joinpath(*inner.split("/"))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
    dest = target.joinpath(*RUNTIME_DEST_REL)
    if dest.exists():
        remove_path(dest)
    scripts.mkdir(parents=True, exist_ok=True)
    stage.rename(dest)


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #


def _resolve_target(raw: str) -> Path:
    target = Path(raw).expanduser().resolve()
    if not target.is_dir():
        sys.exit("error: target is not a directory: " + str(target))
    return target


def _guard_self_bootstrap(target: Path) -> None:
    source_root = find_source_repo_root(target)
    if source_root is None:
        return
    sys.exit(
        "error: refusing to bootstrap the framework's own source tree ("
        + str(source_root)
        + ") - this repo is the source of truth, not a target"
    )


def _apply_seeds(skill_root: Path, target: Path, dry_run: bool) -> tuple[int, int, int]:
    plan = plan_seeds(skill_root, target)
    if dry_run:
        for _seed_rel, rel, status in plan:
            print(status + ": " + rel)
        return 0, 0, 0
    installed = updated = unchanged = 0
    for seed_rel, rel, status in plan:
        if status == "ok":
            print("unchanged: " + rel)
            unchanged += 1
            continue
        write_seed(skill_root, target, seed_rel, rel, status)
        if status == "new":
            print("installed: " + rel)
            installed += 1
        elif status == "append":
            print("appended: " + rel)
            updated += 1
        else:
            print("updated: " + rel)
            updated += 1
    return installed, updated, unchanged


def _reconcile_runtime(
    target: Path, runtime_files: dict, manifest: dict | None, dry_run: bool
) -> tuple[int, int, int]:
    """Report and (unless dry-run) install the bundled runtime.

    Comparisons are against the manifest hashes when present, else the on-disk
    bytes (first install). Returns (installed, updated, unchanged).
    """
    actual = iter_runtime_actual(target)
    rows = []  # (rel, status)
    for rel, data in runtime_files.items():
        if rel not in actual:
            status = "installed"
        elif actual[rel] == data:
            status = "unchanged"
        else:
            status = "updated"
        rows.append((rel, status))

    prefix = "/".join(SCRIPTS_REL)
    counts = {"installed": 0, "updated": 0, "unchanged": 0}
    for rel, status in rows:
        print(status + ": " + prefix + "/" + rel)
        counts[status] += 1

    if not dry_run and (counts["installed"] or counts["updated"]):
        stage_runtime(target, runtime_files)
    return counts["installed"], counts["updated"], counts["unchanged"]


def cmd_setup(args, skill_root: Path) -> int:
    _guard_self_bootstrap(_resolve_target(args.target))
    verify_seeds(skill_root)
    target = _resolve_target(args.target)
    version = read_runtime_version(skill_root)
    runtime_files = iter_runtime_source(skill_root)
    manifest = read_manifest(target)

    if manifest is not None:
        installed_version = str(manifest.get("runtime_version", "0"))
        if version_tuple(installed_version) > version_tuple(version):
            sys.stderr.write(
                "error: the installed runtime ("
                + installed_version
                + ") is newer than this package ("
                + version
                + "); refusing to downgrade. Use a newer dev-agent skill.\n"
            )
            return 2

    s_inst, s_upd, s_same = _apply_seeds(skill_root, target, args.dry_run)
    r_inst, r_upd, r_same = _reconcile_runtime(
        target, runtime_files, manifest, args.dry_run
    )

    m_inst = m_same = 0
    if not args.dry_run:
        new_manifest = build_manifest(
            runtime_files, version, args.scope, args.agent or ""
        )
        if manifest is None or manifest.get("files") != new_manifest["files"]:
            write_manifest(target, new_manifest)
            print("wrote: .agents/.devagent.json")
            m_inst = 1
        else:
            print("unchanged: .agents/.devagent.json")
            m_same = 1

    skill_names = _resolve_skill_names(args.skills, _read_descriptor(skill_root))

    print(
        "dev-agent setup complete: "
        + str(s_inst + r_inst + m_inst)
        + " installed, "
        + str(s_upd + r_upd)
        + " updated, "
        + str(s_same + r_same + m_same)
        + " unchanged"
    )

    if skill_names and not args.dry_run:
        return _install_skills(skill_root, args, target, skill_names)
    return 0


def cmd_check(args, skill_root: Path) -> int:
    target = _resolve_target(args.target)
    version = read_runtime_version(skill_root)
    runtime_files = iter_runtime_source(skill_root)
    manifest = read_manifest(target)

    drift = 0
    if manifest is None:
        print("missing: .agents/.devagent.json")
        print("dev-agent check: 1 change(s) needed")
        return 1

    installed_version = str(manifest.get("runtime_version", "0"))
    if version_tuple(installed_version) < version_tuple(version):
        print(
            "stale: runtime " + installed_version + " -> " + version + " (run --update)"
        )
        drift += 1
    elif version_tuple(installed_version) > version_tuple(version):
        print("stale: runtime " + installed_version + " is newer than this package")
        drift += 1

    known = manifest.get("files") or {}
    actual = iter_runtime_actual(target)
    for rel, data in sorted(runtime_files.items()):
        dig = sha256_bytes(data)
        if rel not in actual:
            print("missing: " + rel)
            drift += 1
        elif rel not in known:
            print("orphan: " + rel + " (not in manifest)")
            drift += 1
        elif actual[rel] != data:
            print("modified: " + rel)
            drift += 1
        elif known.get(rel) != dig and actual[rel] == data:
            print("modified: " + rel + " (manifest hash out of date)")
            drift += 1
    for rel in sorted(set(actual) - set(runtime_files)):
        print("orphan: " + rel + " (not in package)")
        drift += 1

    if drift:
        print("dev-agent check: " + str(drift) + " change(s) needed")
        return 1
    print("dev-agent check: clean")
    return 0


def cmd_update(args, skill_root: Path) -> int:
    target = _resolve_target(args.target)
    _guard_self_bootstrap(target)
    version = read_runtime_version(skill_root)
    runtime_files = iter_runtime_source(skill_root)
    manifest = read_manifest(target)

    # Capture files the user modified (relative to the manifest) so we can back
    # them up AFTER staging replaces the runtime directory.
    modified = {}
    if manifest is not None:
        known = manifest.get("files") or {}
        for rel, data in iter_runtime_actual(target).items():
            if rel in known and sha256_bytes(data) != known[rel]:
                modified[rel] = data

    if args.dry_run:
        _reconcile_runtime(target, runtime_files, manifest, True)
        print("dev-agent update: dry-run (no writes)")
        return 0

    r_inst, r_upd, _r_same = _reconcile_runtime(target, runtime_files, manifest, False)

    for rel, data in sorted(modified.items()):
        full = target.joinpath(*SCRIPTS_REL, *rel.split("/"))
        backup = full.with_name(full.name + ".bak")
        backup.write_bytes(data)
        print("backup: " + "/".join(SCRIPTS_REL) + "/" + rel + " -> " + backup.name)

    new_manifest = build_manifest(runtime_files, version, args.scope, args.agent or "")
    write_manifest(target, new_manifest)
    print("wrote: .agents/.devagent.json")
    print(
        "dev-agent update complete: "
        + str(r_inst)
        + " installed, "
        + str(r_upd)
        + " updated"
    )
    return 0


def _read_descriptor(skill_root: Path) -> dict:
    path = skill_root / DESCRIPTOR_NAME
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}


def _resolve_skill_names(spec: str, descriptor: dict) -> list:
    """Resolve a `--skills` spec to names, always including the mandatory set.

    Absent/`mandatory` -> mandatory only; a comma list -> mandatory plus the
    listed extras (the flag selects optional skills); `all` -> mandatory plus
    every optional skill; `none`/`off` -> nothing.
    """
    mandatory = list(descriptor.get("mandatory", []))
    optional = list(descriptor.get("optional", []))
    spec = (spec or "mandatory").strip()
    if spec in ("none", "off"):
        return []
    if spec in ("mandatory", "required", "all"):
        return mandatory + optional if spec == "all" else mandatory
    extra = [s.strip() for s in spec.split(",") if s.strip()]
    return mandatory + [s for s in extra if s not in mandatory]


def _emit(stream, text: str) -> None:
    """Write subprocess output without failing on a narrow console codec."""
    encoding = getattr(stream, "encoding", None) or "utf-8"
    try:
        stream.write(text)
    except UnicodeEncodeError:
        stream.write(text.encode(encoding, "replace").decode(encoding, "replace"))


def _install_skills(
    skill_root: Path, args, target: Path, names: list | None = None
) -> int:
    descriptor = _read_descriptor(skill_root)
    source = descriptor.get("source")
    if names is None:
        names = _resolve_skill_names(args.skills, descriptor)
    if not source or not names:
        sys.stderr.write("error: no --skills descriptor or skill list available\n")
        return 1

    argv = ["npx", "--yes", "skills@latest", "add", source]
    for name in names:
        argv += ["--skill", name]
    argv += ["-y"]
    if args.scope == "global":
        argv += ["-g"]
    if args.agent:
        argv += ["-a", args.agent]

    npx = shutil.which("npx")
    if npx is None:
        print("note: npx not found; runtime installed, install skills manually:")
        print("      " + " ".join(argv))
        return 0

    # On Windows `npx` is a .cmd shim, which CreateProcess cannot run directly.
    run_cmd = [npx, *argv[1:]]
    if os.name == "nt" and npx.lower().endswith((".cmd", ".bat")):
        run_cmd = [os.environ.get("COMSPEC", "cmd.exe"), "/c", *run_cmd]
    proc = subprocess.run(
        run_cmd,
        cwd=str(target),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.stdout:
        _emit(sys.stdout, proc.stdout)
    if proc.stderr:
        _emit(sys.stderr, proc.stderr)
    if proc.returncode != 0:
        sys.stderr.write(
            "error: `npx skills add` failed (exit " + str(proc.returncode) + ")\n"
        )
        return proc.returncode
    print("skills installed: " + ", ".join(names))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="bootstrap.py",
        description="dev-agent: install the Dev Agent framework into a target repository",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="setup",
        choices=["setup", "check", "update"],
        help="what to do (default: setup)",
    )
    parser.add_argument("--target", default=".", help="repository to install into")
    parser.add_argument("--dry-run", action="store_true", help="preview, write nothing")
    parser.add_argument(
        "--check",
        action="store_true",
        dest="check_flag",
        help="alias for the check command",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        dest="update_flag",
        help="alias for the update command",
    )
    parser.add_argument(
        "--scope",
        default="project",
        choices=["project", "global"],
        help="install scope",
    )
    parser.add_argument("--agent", default=None, help="harness/agent name to record")
    parser.add_argument(
        "--skills",
        default="mandatory",
        help=(
            "skills to install: mandatory (default) | none | all | <comma-list of "
            "optional skills>; always includes the mandatory set"
        ),
    )
    args = parser.parse_args()

    command = (
        "check" if args.check_flag else "update" if args.update_flag else args.command
    )
    skill_root = find_skill_root()

    if command == "setup":
        return cmd_setup(args, skill_root)
    if command == "check":
        return cmd_check(args, skill_root)
    return cmd_update(args, skill_root)


if __name__ == "__main__":
    sys.exit(main())
