import os
import sys
import re
import argparse
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
        return Path(__file__).resolve().parents[4]


PROJECT_ROOT = _get_project_root()
DOCS_DIR = PROJECT_ROOT / "docs"
PERSONAS_DIR = PROJECT_ROOT / ".agents" / "personas"
TEMPLATES_DIR = PROJECT_ROOT / ".agents" / "skills" / "collaborative-memory" / "templates"

def copy_template(template_name, dest_path):
    template_file = TEMPLATES_DIR / template_name
    if not template_file.exists():
        print(f"  Error: Template file missing: {template_file}")
        sys.exit(1)
    
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy(template_file, dest_path)
        print(f"  Initialized {dest_path.relative_to(PROJECT_ROOT)}")
    except Exception as e:
        print(f"  Error writing to {dest_path}: {e}")
        sys.exit(1)

def auto_detect_project_profile():
    profile_dest = DOCS_DIR / "project_profile.md"
    if profile_dest.exists():
        return

    template_file = TEMPLATES_DIR / "project_profile_template.md"
    if not template_file.exists():
        print("  Error: Template project_profile_template.md missing")
        return

    try:
        profile_content = template_file.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  Error reading template: {e}")
        return

    # Default values/fallbacks
    project_name = "AI Setup"
    domain = "Developer Tooling / AI Agent Template"
    tech_stack = "Python, Taskfile"
    repo_pattern = "Single Package"
    purpose = "Multi-agent base template for workspace collaboration."
    formatting_rule = "[e.g., PEP 8 for Python, Prettier for TypeScript]"
    testing_rule = "[e.g., write unit tests for all new utilities, keep 80%+ coverage]"
    git_rule = "[e.g., feature branches, squash commit on merge]"

    readme_path = PROJECT_ROOT / "README.md"
    
    if readme_path.exists():
        print("  Reading root README.md to auto-configure project profile...")
        try:
            readme_text = readme_path.read_text(encoding="utf-8")
            
            # Extract first heading as project name
            name_match = re.search(r"^#\s+(.+)$", readme_text, re.MULTILINE)
            if name_match:
                project_name = name_match.group(1).strip()
            
            # Scan for common project configuration files to identify the tech stack
            detected_stack = []
            file_markers = {
                "package.json": "Node.js",
                "tsconfig.json": "TypeScript",
                "requirements.txt": "Python",
                "pyproject.toml": "Python",
                "go.mod": "Go",
                "Cargo.toml": "Rust",
                "Taskfile.yml": "Taskfile",
                "Dockerfile": "Docker",
                "docker-compose.yml": "Docker",
                "Makefile": "Make"
            }
            for filename, display in file_markers.items():
                if (PROJECT_ROOT / filename).exists():
                    detected_stack.append(display)

            # Check if README explicitly mentions tech stack/stack
            stack_match = re.search(r"(?:Tech\s+)?Stack:\s*(.+)$", readme_text, re.MULTILINE | re.IGNORECASE)
            if stack_match:
                for item in stack_match.group(1).split(","):
                    cleaned_item = item.strip().strip(".*•")
                    if cleaned_item:
                        detected_stack.append(cleaned_item)

            if detected_stack:
                tech_stack = ", ".join(sorted(list(set(detected_stack))))
            
            # Detect repo type
            if re.search(r"\bmonorepo\b", readme_text, re.IGNORECASE):
                repo_pattern = "Monorepo"
            
            # Extract purpose (first substantial paragraph)
            lines = [l.strip() for l in readme_text.splitlines() if l.strip()]
            for j, line in enumerate(lines):
                if line.startswith("#"):
                    for k in range(j + 1, min(j + 5, len(lines))):
                        if not lines[k].startswith("#") and len(lines[k].split()) > 3:
                            purpose = lines[k]
                            if len(purpose) > 150:
                                purpose = purpose[:147] + "..."
                            break
                    break

            # Try to extract alignment philosophy, formatting, testing, git rules
            for line in readme_text.splitlines():
                stripped = line.strip().lower()
                # Formatting rule detection
                if any(x in stripped for x in ["formatting", "eslint", "prettier", "pep 8", "pep8"]):
                    if len(line.strip()) > 10 and len(line.strip()) < 100:
                        formatting_rule = line.strip().lstrip("-*• ").strip()
                # Testing standard detection
                if any(x in stripped for x in ["test", "testing", "pytest", "jest", "coverage"]):
                    if len(line.strip()) > 10 and len(line.strip()) < 100:
                        testing_rule = line.strip().lstrip("-*• ").strip()
                # Git strategy detection
                if any(x in stripped for x in ["git", "branch", "commit", "squash"]):
                    if len(line.strip()) > 10 and len(line.strip()) < 100:
                        git_rule = line.strip().lstrip("-*• ").strip()

        except Exception as e:
            print(f"  Warning: Failed to extract info from README.md: {e}")
    else:
        # README.md does not exist, check if interactive
        if sys.stdin.isatty():
            print("\n  [!] README.md not found! Starting interactive project setup:")
            try:
                project_name = input("  Enter Project Name (default: 'AI Setup'): ").strip() or project_name
                domain = input("  Enter Project Domain/Type (default: 'Developer Tooling'): ").strip() or domain
                tech_stack = input("  Enter Tech Stack (default: 'Python, Taskfile'): ").strip() or tech_stack
                repo_pattern = input("  Enter Repository Pattern (default: 'Single Package'): ").strip() or repo_pattern
                purpose = input("  Enter Project Purpose/Description: ").strip() or purpose
                
                generate_readme = input("  Would you like the AI to generate a root README.md? (y/N): ").strip().lower()
                if generate_readme.startswith('y'):
                    readme_template_path = PROJECT_ROOT / ".agents" / "scripts" / "README.template.md"
                    if readme_template_path.exists():
                        try:
                            readme_template = readme_template_path.read_text(encoding="utf-8")
                            readme_content = readme_template.format(
                                project_name=project_name,
                                purpose=purpose,
                                domain=domain,
                                tech_stack=tech_stack
                            )
                            readme_path.write_text(readme_content, encoding="utf-8")
                            print(f"  Successfully generated root README.md at {readme_path}")
                        except Exception as e:
                            print(f"  Warning: Failed to generate README.md from template: {e}")
                    else:
                        print("  Warning: README.template.md not found, skipping generation.")
            except (KeyboardInterrupt, EOFError):
                print("\n  Setup interrupted. Using default fallbacks.")
        else:
            print("  README.md not found. Non-interactive session, using default fallbacks.")

    # Inject variables into the template
    profile_content = profile_content.replace("[Project Name]", project_name)
    profile_content = profile_content.replace("[e.g., Web Application, Developer Tooling, Backend Service, Infrastructure]", domain)
    profile_content = profile_content.replace("[e.g., Python, TypeScript, React, Next.js, FastAPI, PostgreSQL]", tech_stack)
    profile_content = profile_content.replace("[e.g., Monorepo, Single Package, Microservice]", repo_pattern)
    profile_content = profile_content.replace("[Brief explanation of what the project does and its core business value]", purpose)
    profile_content = profile_content.replace("[e.g., PEP 8 for Python, Prettier for TypeScript]", formatting_rule)
    profile_content = profile_content.replace("[e.g., write unit tests for all new utilities, keep 80%+ coverage]", testing_rule)
    profile_content = profile_content.replace("[e.g., feature branches, squash commit on merge]", git_rule)

    profile_dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        profile_dest.write_text(profile_content, encoding="utf-8")
        print(f"  Initialized {profile_dest.relative_to(PROJECT_ROOT)}")
    except Exception as e:
        print(f"  Error writing to {profile_dest}: {e}")

def init_core():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "handoffs").mkdir(parents=True, exist_ok=True)
    
    memory_file = DOCS_DIR / "MEMORY.md"
    if not memory_file.exists():
        copy_template("memory_template.md", memory_file)

    handoff_file = DOCS_DIR / "handoffs" / "active_handoff.md"
    if not handoff_file.exists():
        copy_template("handoff_template.md", handoff_file)

    # Initialize AI-readable project profile
    auto_detect_project_profile()

def init_specs():
    path = DOCS_DIR / "specs"
    path.mkdir(parents=True, exist_ok=True)
    index_file = path / "index.md"
    if not index_file.exists():
        copy_template("specs_index_template.md", index_file)

def init_adr():
    path = DOCS_DIR / "adr"
    path.mkdir(parents=True, exist_ok=True)
    index_file = path / "index.md"
    if not index_file.exists():
        copy_template("adr_index_template.md", index_file)

def init_tests():
    (DOCS_DIR / "tests").mkdir(parents=True, exist_ok=True)
    print("  Created docs/tests/")

def init_audits():
    (DOCS_DIR / "audits").mkdir(parents=True, exist_ok=True)
    print("  Created docs/audits/")

def init_changes():
    (DOCS_DIR / "changes").mkdir(parents=True, exist_ok=True)
    print("  Created docs/changes/")

def init_plans():
    (DOCS_DIR / "plans").mkdir(parents=True, exist_ok=True)
    print("  Created docs/plans/")

def detect_from_personas():
    folders = set(["specs", "plans"])  # Default base folders
    if not PERSONAS_DIR.exists():
        return folders
    for file in PERSONAS_DIR.glob("*.md"):
        persona_name = file.stem.lower()
        if persona_name == "architect":
            folders.add("adr")
        elif persona_name == "qa":
            folders.add("tests")
            folders.add("audits")
        elif persona_name == "engineer":
            folders.add("changes")
    return folders

def main():
    parser = argparse.ArgumentParser(description="Initialize Workspace Collaborative Memory System (CMS) docs layout.")
    parser.add_argument("folders", nargs="*", help="Specific folders to initialize (e.g. specs, adr, tests, audits, changes, plans, all). If empty, auto-detects from active personas.")
    args = parser.parse_args()

    print("Initializing CMS docs layout...")
    
    # 1. Always initialize core handoffs and MEMORY.md
    init_core()

    # 2. Determine which subfolders to initialize
    target_folders = set()
    if args.folders:
        if "all" in [f.lower() for f in args.folders]:
            target_folders = {"specs", "adr", "tests", "audits", "changes", "plans"}
        else:
            for f in args.folders:
                target_folders.add(f.lower())
    else:
        # Auto-detect from active personas folder
        target_folders = detect_from_personas()
        print(f"  Auto-detected active personas. Selected folders: {', '.join(sorted(target_folders))}")

    # 3. Call corresponding functions
    mappers = {
        "specs": init_specs,
        "adr": init_adr,
        "tests": init_tests,
        "audits": init_audits,
        "changes": init_changes,
        "plans": init_plans
    }

    for folder in sorted(target_folders):
        if folder in mappers:
            mappers[folder]()
        else:
            print(f"  Warning: Unknown folder target '{folder}' ignored.")

    print("CMS docs initialization completed successfully!\n")

if __name__ == "__main__":
    main()
