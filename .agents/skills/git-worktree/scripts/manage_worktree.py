"""
Git Worktree Manager
Manages isolated Git worktrees for parallel agent execution.

Subcommands:
    create <slug> <branch>  - Create a worktree under .worktrees/<slug> on <branch>
    clean  <slug> <branch>  - Remove worktree and delete local branch
    list                    - List all active Git worktrees
"""

import os
import sys
import subprocess


def get_project_root():
    """Resolve project root via git rev-parse."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        print("Error: Not inside a Git repository.", file=sys.stderr)
        sys.exit(1)


def ensure_gitignore_entry(project_root):
    """Ensure .worktrees/ is listed in .gitignore."""
    gitignore_path = os.path.join(project_root, ".gitignore")
    entry = ".worktrees/"

    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r", encoding="utf-8") as f:
            content = f.read()
        if entry not in content:
            with open(gitignore_path, "a", encoding="utf-8") as f:
                f.write("\n# Git worktrees for parallel agents\n" + entry + "\n")
    else:
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write("# Git worktrees for parallel agents\n" + entry + "\n")


def branch_exists(branch_name):
    """Check if a local branch exists."""
    result = subprocess.run(
        ["git", "show-ref", "--verify", f"refs/heads/{branch_name}"],
        capture_output=True, text=True
    )
    return result.returncode == 0


def cmd_create(slug, branch):
    """Create a worktree at .worktrees/<slug> on the given branch."""
    project_root = get_project_root()
    worktree_parent = os.path.join(project_root, ".worktrees")
    worktree_path = os.path.join(worktree_parent, slug)

    if os.path.exists(worktree_path):
        print(f"Error: Worktree path already exists: {worktree_path}", file=sys.stderr)
        sys.exit(1)

    ensure_gitignore_entry(project_root)
    os.makedirs(worktree_parent, exist_ok=True)

    if branch_exists(branch):
        print(f"Branch '{branch}' exists. Adding worktree at '{worktree_path}'...")
        subprocess.run(
            ["git", "worktree", "add", worktree_path, branch],
            check=True
        )
    else:
        print(f"Creating branch '{branch}' and worktree at '{worktree_path}'...")
        subprocess.run(
            ["git", "worktree", "add", worktree_path, "-b", branch],
            check=True
        )

    print(f"Worktree ready: {os.path.abspath(worktree_path)}")


def cmd_clean(slug, branch):
    """Remove a worktree and delete its local branch."""
    project_root = get_project_root()
    worktree_path = os.path.join(project_root, ".worktrees", slug)

    if os.path.exists(worktree_path):
        print(f"Removing worktree at '{worktree_path}'...")
        subprocess.run(["git", "worktree", "remove", worktree_path, "--force"], check=True)
    else:
        print(f"Worktree path not found: {worktree_path}. Pruning stale entries...")
        subprocess.run(["git", "worktree", "prune"], check=True)

    if branch_exists(branch):
        print(f"Deleting branch '{branch}'...")
        subprocess.run(["git", "branch", "-D", branch], check=True)
    else:
        print(f"Branch '{branch}' not found, skipping deletion.")

    print("Cleanup complete.")


def cmd_list():
    """List all active Git worktrees."""
    subprocess.run(["git", "worktree", "list"], check=True)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "create":
        if len(sys.argv) != 4:
            print("Usage: manage_worktree.py create <slug> <branch>", file=sys.stderr)
            sys.exit(1)
        cmd_create(sys.argv[2], sys.argv[3])

    elif command == "clean":
        if len(sys.argv) != 4:
            print("Usage: manage_worktree.py clean <slug> <branch>", file=sys.stderr)
            sys.exit(1)
        cmd_clean(sys.argv[2], sys.argv[3])

    elif command == "list":
        cmd_list()

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
