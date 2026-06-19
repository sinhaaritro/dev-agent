import sys
import shutil
import subprocess
from pathlib import Path


def _get_project_root():
    """Resolve project root via git."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True
        )
        return Path(result.stdout.strip())
    except subprocess.CalledProcessError:
        return Path(__file__).resolve().parent.parents[1]


# Paths
PROJECT_ROOT = _get_project_root()
SCRIPT_DIR = Path(__file__).resolve().parent
TASKFILE_PATH = PROJECT_ROOT / "Taskfile.yml"
TEMPLATE_PATH = SCRIPT_DIR / "Taskfile.template.yml"
GITIGNORE_PATH = PROJECT_ROOT / ".gitignore"
GITIGNORE_TEMPLATE = SCRIPT_DIR / "gitignore.template"

def normalize_rule(line):
    return line.strip().rstrip("/")

def ensure_gitignore():
    print("Checking if .gitignore is configured...")
    if not GITIGNORE_TEMPLATE.exists():
        print(f"Error: Gitignore template file not found at {GITIGNORE_TEMPLATE}", file=sys.stderr)
        sys.exit(1)

    if not GITIGNORE_PATH.exists():
        print(".gitignore not found. Auto-generating from template...")
        try:
            shutil.copy(GITIGNORE_TEMPLATE, GITIGNORE_PATH)
            print(f"Successfully created .gitignore at {GITIGNORE_PATH}")
        except Exception as e:
            print(f"Error copying template to {GITIGNORE_PATH}: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # Check for missing rules if .gitignore exists
    try:
        existing_content = GITIGNORE_PATH.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading {GITIGNORE_PATH}: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        template_content = GITIGNORE_TEMPLATE.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading {GITIGNORE_TEMPLATE}: {e}", file=sys.stderr)
        sys.exit(1)

    # Parse template rules
    template_rules = []
    for line in template_content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            template_rules.append(stripped)

    # Parse existing rules
    existing_normalized = set()
    for line in existing_content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            existing_normalized.add(normalize_rule(stripped))

    # Identify missing rules
    missing_rules = []
    for rule in template_rules:
        if normalize_rule(rule) not in existing_normalized:
            missing_rules.append(rule)

    if missing_rules:
        print("Missing rules detected in .gitignore. Appending missing rules...")
        try:
            with open(GITIGNORE_PATH, "a", encoding="utf-8") as f:
                f.write("\n# Added by agent workspace setup\n")
                for rule in missing_rules:
                    f.write(f"{rule}\n")
            print("Successfully updated .gitignore with missing rules.")
        except Exception as e:
            print(f"Error appending rules to {GITIGNORE_PATH}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(".gitignore is already up to date.")

def main():
    print("Checking if Taskfile.yml exists...")
    taskfile_created = False
    if TASKFILE_PATH.exists():
        print("Taskfile.yml already exists at root directory. No action required.")
    else:
        print("Taskfile.yml not found. Auto-generating from template...")
        if not TEMPLATE_PATH.exists():
            print(f"Error: Template file not found at {TEMPLATE_PATH}", file=sys.stderr)
            sys.exit(1)

        try:
            shutil.copy(TEMPLATE_PATH, TASKFILE_PATH)
            print(f"Successfully created Taskfile.yml at {TASKFILE_PATH}")
            taskfile_created = True
        except Exception as e:
            print(f"Error copying template to {TASKFILE_PATH}: {e}", file=sys.stderr)
            sys.exit(1)

    # Ensure gitignore is configured
    ensure_gitignore()

if __name__ == "__main__":
    main()

