import os
import sys
import shutil
import hashlib
import subprocess
from pathlib import Path

def get_file_hash(content):
    # Normalize line endings to avoid platform-specific diffs
    normalized = content.replace("\r\n", "\n").encode('utf-8')
    return hashlib.sha256(normalized).hexdigest()

def run_command(command, cwd=None):
    try:
        # Run shell command
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def main():
    print("=" * 60)
    print("      AGENTIC WORKSPACE INITIALIZATION / BOOTSTRAP      ")
    print("=" * 60)

    # 1. Setup paths relative to script location
    # Script is in: <workspace_root>/.agents/skills/agentic-code-start/scripts/bootstrap.py
    script_path = Path(__file__).resolve()
    skill_dir = script_path.parent.parent
    template_dir = skill_dir / "templates"
    
    # Workspace root is 4 levels up from the script
    workspace_root = Path(skill_dir.parent.parent.parent).resolve()
    target_agents_dir = workspace_root / ".agents"

    print(f"[INFO] Workspace root detected: {workspace_root}")
    print(f"[INFO] Template directory: {template_dir}")
    print(f"[INFO] Target agent directory: {target_agents_dir}")
    print("-" * 60)

    if not template_dir.exists():
        print(f"[ERROR] Template directory not found: {template_dir}")
        sys.exit(1)

    # 2. Sync Agent Directory Templates (personas, workflows, rules, scripts)
    folders = ["personas", "workflows", "rules", "scripts"]
    for folder in folders:
        src_folder = template_dir / folder
        dest_folder = target_agents_dir / folder

        if not src_folder.exists():
            continue

        print(f"\n[INFO] Checking folder: .agents/{folder}/")
        os.makedirs(dest_folder, exist_ok=True)

        for item in src_folder.iterdir():
            if item.is_file():
                dest_file = dest_folder / item.name
                
                # Read template content
                with open(item, "r", encoding="utf-8") as f:
                    template_content = f.read()

                if dest_file.exists():
                    # Compare content
                    with open(dest_file, "r", encoding="utf-8") as f:
                        dest_content = f.read()

                    if get_file_hash(template_content) == get_file_hash(dest_content):
                        print(f"  [OK] Up to date: .agents/{folder}/{item.name}")
                    else:
                        print(f"  [WARNING] File exists and has custom changes! SKIPPED overwrite:")
                        print(f"    -> Destination: .agents/{folder}/{item.name}")
                        print(f"    -> Template: .agents/skills/agentic-code-start/templates/{folder}/{item.name}")
                else:
                    # Copy file
                    shutil.copy2(item, dest_file)
                    print(f"  [CREATED] Installed template: .agents/{folder}/{item.name}")

    # 3. Handle Root Configuration files (.cursorrules, .windsurfrules)
    print("\n[INFO] Checking IDE Routing Configurations...")
    routing_rules = {
        ".cursorrules": "# Cursor Rules\n# Please read and adhere to the gateway instructions defined in `.agents/rules/system.md`.\n",
        ".windsurfrules": "# Windsurf Rules\n# Please read and adhere to the gateway instructions defined in `.agents/rules/system.md`.\n"
    }

    for filename, rule_content in routing_rules.items():
        rule_file = workspace_root / filename
        if rule_file.exists():
            with open(rule_file, "r", encoding="utf-8") as f:
                content = f.read()
            if ".agents/" not in content:
                # Append instruction
                with open(rule_file, "a", encoding="utf-8") as f:
                    f.write("\n" + rule_content)
                print(f"  [UPDATED] Appended routing instruction to {filename}")
            else:
                print(f"  [OK] Routing instruction already present in {filename}")
        else:
            with open(rule_file, "w", encoding="utf-8", newline="\n") as f:
                f.write(rule_content)
            print(f"  [CREATED] Created routing file: {filename}")

    # 4. Handle Root Templates (Taskfile.yml, .gitignore, skills-lock.json)
    root_templates = ["Taskfile.yml", ".gitignore", "skills-lock.json"]
    for filename in root_templates:
        src_file = template_dir / filename
        dest_file = workspace_root / filename

        if src_file.exists():
            with open(src_file, "r", encoding="utf-8") as f:
                template_content = f.read()

            if dest_file.exists():
                with open(dest_file, "r", encoding="utf-8") as f:
                    dest_content = f.read()
                
                if get_file_hash(template_content) == get_file_hash(dest_content):
                    print(f"  [OK] Up to date: {filename}")
                else:
                    print(f"  [WARNING] File exists and has custom changes! SKIPPED overwrite:")
                    print(f"    -> Destination: {filename}")
                    print(f"    -> Template: .agents/skills/agentic-code-start/templates/{filename}")
            else:
                shutil.copy2(src_file, dest_file)
                print(f"  [CREATED] Installed root file: {filename}")

    # 5. Run Skills Update
    print("\n[INFO] Updating installed skills...")
    success, stdout, stderr = run_command("npx skills update", cwd=str(workspace_root))
    if success:
        print("  [OK] npx skills update executed successfully.")
        if stdout:
            print(stdout.strip())
    else:
        # Check if skills lock exists; if so, npx skills might not be in PATH
        print("  [WARNING] Could not execute 'npx skills update'. Make sure Node.js/NPM are installed.")
        if stderr:
            print(f"  Details: {stderr.strip()}")

    print("\n" + "=" * 60)
    print("          INITIALIZATION COMPLETE SUCCESSFULLY          ")
    print("=" * 60)

if __name__ == "__main__":
    main()
