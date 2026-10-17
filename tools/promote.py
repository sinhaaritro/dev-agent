#!/usr/bin/env python3
"""promote engine - mirror the shipped product (skills/) into the dogfood
workspace (.agents/skills/).

`skills/` is the product and the single source of truth: the top-level folders
users receive via `npx skills`. `.agents/skills/` is the repo's own workspace
copy (used while building the framework) plus repo-only tooling; it must never
ship. The skills CLI discovers BOTH `skills/` and `.agents/skills/`, so every
skill under `.agents/skills/` must carry `metadata.internal: true` or it leaks
to users. promote enforces that by injecting the flag into the derived copy.

What promote owns:
    - every top-level `skills/<name>/` folder that contains a `SKILL.md`,
    - recorded in `.agents/.promoted.json`.

What promote never touches:
    - any `.agents/skills/<name>` not in the manifest (repo-only skills such as
      `promote`/`author-skill`, and third-party `skill-creator`).

Usage:
    python tools/promote.py               # apply (default)
    python tools/promote.py apply
    python tools/promote.py --dry-run     # print planned changes, write nothing
    python tools/promote.py --check       # exit 1 on any drift (CI)

Per-skill report (dry-run/check): new: <name>  ok: <name>  overwrite: <name>
                                  remove: <name>
Per-skill report (apply): installed/unchanged/updated/removed: <name>
Summary (apply):
    promote complete: <N> installed, <M> updated, <K> unchanged, <R> removed

Exit codes: 0 = success / clean; 1 = drift (--check only); 2 = error.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

SKILLS_DIR = "skills"
WORK_DIR = ".agents/skills"
MANIFEST = ".agents/.promoted.json"


def find_root() -> Path:
    """Walk up from this script until AGENTS.md is found (repo root marker)."""
    current = Path(__file__).resolve().parent
    while True:
        if (current / "AGENTS.md").is_file():
            return current
        parent = current.parent
        if parent == current:
            sys.exit("error: AGENTS.md not found above " + str(Path(__file__).resolve()))
        current = parent


def normalize_bytes(data: bytes) -> bytes:
    """Normalise line endings to LF for UTF-8 text; pass binary through.

    Keeps --check stable across machines/checkouts regardless of CRLF policy.
    """
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def inject_internal(text: str) -> str:
    """Ensure the frontmatter `metadata:` block contains `internal: true`.

    This is the ONLY transform applied to a derived skill: the source `skills/`
    copy stays clean (no internal), so shipped skills are never hidden. Raises
    ValueError when the file has no usable frontmatter.
    """
    if not text.startswith("---"):
        raise ValueError("SKILL.md does not start with frontmatter ('---')")
    lines = text.split("\n")
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        raise ValueError("unterminated frontmatter")
    fm = lines[1:end]

    meta_idx = None
    for i, ln in enumerate(fm):
        if ln.rstrip() == "metadata:":
            meta_idx = i
            break

    if meta_idx is None:
        fm = fm + ["metadata:", "  internal: true"]
    else:
        has_internal = False
        j = meta_idx + 1
        while j < len(fm) and fm[j].startswith((" ", "\t")):
            if fm[j].strip().startswith("internal:"):
                has_internal = True
                break
            j += 1
        if not has_internal:
            fm = fm[: meta_idx + 1] + ["  internal: true"] + fm[meta_idx + 1 :]

    return "\n".join(["---"] + fm + ["---"] + lines[end + 1 :])


def iter_files(src_dir: Path):
    """Yield (posix-relpath, path) for every sourceable file (skips caches)."""
    for path in sorted(src_dir.rglob("*")):
        if path.is_dir():
            continue
        parts = path.relative_to(src_dir).parts
        if "__pycache__" in parts or path.suffix == ".pyc":
            continue
        yield path.relative_to(src_dir).as_posix(), path


def discover_sources(skills_dir: Path) -> dict:
    """Top-level `skills/<name>/` folders that contain a SKILL.md."""
    out = {}
    if not skills_dir.is_dir():
        return out
    for entry in sorted(skills_dir.iterdir()):
        if entry.is_dir() and (entry / "SKILL.md").is_file():
            out[entry.name] = entry
    return out


def expected_files(src_dir: Path) -> dict:
    """The exact bytes promote should place in the derived folder."""
    out = {}
    for rel, path in iter_files(src_dir):
        data = path.read_bytes()
        if rel == "SKILL.md":
            text = normalize_bytes(data).decode("utf-8")
            out[rel] = inject_internal(text).encode("utf-8")
        else:
            out[rel] = normalize_bytes(data)
    return out


def actual_files(dest_dir: Path):
    """Normalised bytes currently in a derived folder, or None if absent."""
    if not dest_dir.is_dir():
        return None
    out = {}
    for path in sorted(dest_dir.rglob("*")):
        if path.is_dir():
            continue
        parts = path.relative_to(dest_dir).parts
        if "__pycache__" in parts:
            continue
        out[path.relative_to(dest_dir).as_posix()] = normalize_bytes(path.read_bytes())
    return out


def load_manifest(root: Path) -> list:
    manifest = root / MANIFEST
    if not manifest.is_file():
        return []
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return list(data.get("skills", []))


def write_manifest(root: Path, names) -> None:
    manifest = root / MANIFEST
    manifest.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps({"version": 1, "skills": sorted(names)}, indent=2) + "\n"
    manifest.write_text(content, encoding="utf-8", newline="\n")


def remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="mirror skills/ (product) into .agents/skills/ (dogfood workspace)"
    )
    parser.add_argument("mode", nargs="?", default="apply", choices=["apply"])
    parser.add_argument("--dry-run", action="store_true", help="print planned changes, write nothing")
    parser.add_argument("--check", action="store_true", help="exit non-zero on any drift")
    args = parser.parse_args()

    if args.dry_run and args.check:
        sys.stderr.write("error: --dry-run and --check are mutually exclusive\n")
        return 2

    root = find_root()
    skills_dir = root / SKILLS_DIR
    work_dir = root / WORK_DIR

    if not skills_dir.is_dir():
        sys.stderr.write("error: no skills/ folder at " + str(skills_dir) + "\n")
        return 2

    sources = discover_sources(skills_dir)
    managed = set(load_manifest(root))
    existing = {d.name for d in work_dir.iterdir() if d.is_dir()} if work_dir.is_dir() else set()

    collisions = sorted((set(sources) & existing) - managed)
    if collisions:
        sys.stderr.write(
            "error: name collision with unmanaged skill(s) in "
            + WORK_DIR
            + ": "
            + ", ".join(collisions)
            + " (refusing to overwrite; resolve by hand)\n"
        )
        return 2

    plan = []
    for name in sorted(sources):
        try:
            expected = expected_files(sources[name])
        except (OSError, ValueError) as exc:
            sys.stderr.write("error: " + name + ": " + str(exc) + "\n")
            return 2
        actual = actual_files(work_dir / name)
        if actual is None:
            status = "new"
        elif actual == expected:
            status = "ok"
        else:
            status = "overwrite"
        plan.append((status, name, expected))
    removals = sorted(managed - set(sources))

    if args.check:
        drift = 0
        for status, name, _ in plan:
            print(status + ": " + name)
            if status != "ok":
                drift += 1
        for name in removals:
            print("remove: " + name)
            drift += 1
        if drift:
            print("promote: " + str(drift) + " change(s) needed")
            return 1
        print("promote: clean")
        return 0

    if args.dry_run:
        for status, name, _ in plan:
            print(status + ": " + name)
        for name in removals:
            print("remove: " + name)
        return 0

    installed = updated = unchanged = removed = 0
    for status, name, expected in plan:
        dest = work_dir / name
        if status == "ok":
            print("unchanged: " + name)
            unchanged += 1
            continue
        if dest.exists():
            remove_path(dest)
        for rel, data in expected.items():
            out = dest.joinpath(*rel.split("/"))
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)
        if status == "new":
            print("installed: " + name)
            installed += 1
        else:
            print("updated: " + name)
            updated += 1

    for name in removals:
        remove_path(work_dir / name)
        print("removed: " + name)
        removed += 1

    write_manifest(root, list(sources))
    print(
        "promote complete: "
        + str(installed)
        + " installed, "
        + str(updated)
        + " updated, "
        + str(unchanged)
        + " unchanged, "
        + str(removed)
        + " removed"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
