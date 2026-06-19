import subprocess
import os
import re
import datetime

def run_cmd(args):
    try:
        res = subprocess.run(args, capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error executing command: {e.stderr.strip()}"
    except Exception as e:
        return f"Error: {str(e)}"

def get_git_root():
    try:
        res = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.abspath(os.path.join(script_dir, "..", "..", "..", ".."))

def update_handoff():
    git_root = get_git_root()
    handoff_path = os.path.join(git_root, "docs", "handoffs", "active_handoff.md")
    history_path = os.path.join(git_root, "docs", "handoffs", "handoff_history.log")
    audit_path = os.path.join(git_root, "docs", "audits", "session_audit.log")
    template_path = os.path.join(git_root, ".agents", "skills", "collaborative-memory", "templates", "handoff_template.md")
    
    # Ensure directories exist
    os.makedirs(os.path.dirname(handoff_path), exist_ok=True)
    os.makedirs(os.path.dirname(audit_path), exist_ok=True)
    
    # 1. Fetch git status
    branch = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    status = run_cmd(["git", "status", "--porcelain"])
    diff_stat = run_cmd(["git", "diff", "--stat"])
    
    # Detect if we are in a Git worktree
    git_dir = run_cmd(["git", "rev-parse", "--git-dir"])
    is_worktree = "worktrees" in git_dir
    worktree_status = ""
    if is_worktree:
        worktree_status = f"\n- **Worktree Path**: `{os.getcwd()}`"
    
    if not status:
        status_text = "Clean (No uncommitted changes)"
    else:
        status_text = "\n".join(f"- `{line.strip()}`" for line in status.split("\n") if line.strip())
        
    if diff_stat:
        status_text += f"\n\n**Diff Summary**:\n```text\n{diff_stat}\n```"
        
    # 2. Read or create active_handoff.md from template
    if os.path.exists(handoff_path):
        with open(handoff_path, "r", encoding="utf-8") as f:
            content = f.read()
    elif os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()
        print(f"Initializing active handoff from template: {template_path}")
    else:
        content = """# Active Handoff Ticket

- **Type**: ai_to_human
- **Last Updated**: YYYY-MM-DD
- **Active Persona**: @engineer
- **Source**: AI Agent
- **Target**: Human Developer

---

## 🎯 Current Objective
Define active target task here.

---

## 📝 Tasks & Status
- [ ] Task 1

---

## 💻 Workspace State
<!-- state-start -->
- **Active Branch**: main
- **Dirty Files**: None
<!-- state-end -->

---

## ❓ Pending Questions / Prompts
- None
"""

    # Update updated date
    today = datetime.date.today().strftime("%Y-%m-%d")
    content = re.sub(r"- \*\*Last Updated\*\*:\s*[\w\d\-\/]+", f"- **Last Updated**: {today}", content)
    
    # Replace Workspace State section
    state_block = f"""<!-- state-start -->
- **Active Branch**: `{branch}`{worktree_status}
- **Dirty Files / Modifications**:
{status_text}
<!-- state-end -->"""
    
    if "<!-- state-start -->" in content and "<!-- state-end -->" in content:
        content = re.sub(
            r"<!-- state-start -->.*?<!-- state-end -->",
            state_block,
            content,
            flags=re.DOTALL
        )
    else:
        section_pattern = r"(## 💻 Workspace State\s*\n)(.*?)(?=\n\n##|\Z)"
        content = re.sub(
            section_pattern,
            rf"\1{state_block}",
            content,
            flags=re.DOTALL
        )
        
    with open(handoff_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    # 3. Extract meta fields for logging and display
    h_type = re.search(r"- \*\*Type\*\*:\s*([^\n]+)", content)
    h_persona = re.search(r"- \*\*Active Persona\*\*:\s*([^\n]+)", content)
    h_objective = re.search(r"## 🎯 Current Objective\s*\n([^\n]+)", content)
    
    type_str = h_type.group(1).strip() if h_type else "Unknown"
    persona_str = h_persona.group(1).strip() if h_persona else "Unknown"
    objective_str = h_objective.group(1).strip() if h_objective else "Not set"

    # 4. Log to session_audit.log
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [ACTOR: CMS System] COMPILED HANDOFF: Updated {handoff_path} (Branch: {branch})\n"
    with open(audit_path, "a", encoding="utf-8") as f:
        f.write(log_entry)
        
    # 5. Append to handoff_history.log
    history_entry = f"[{timestamp}] Type={type_str} Persona={persona_str} Branch={branch}\n"
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(history_entry)
        
    # 6. Display Terminal Dashboard for human developer (Plain text to avoid Windows encoding issues)
    print("\n" + "=" * 60)
    print("CMS HANDOFF STATUS BOARD".center(60))
    print("=" * 60)
    
    print(f"  Last Updated:   {today}")
    print(f"  Handoff Type:   {type_str}")
    print(f"  Active Role:    {persona_str}")
    print(f"  Git Branch:     {branch}")
    print("-" * 60)
    print(f"  Target Objective:\n    {objective_str}")
    print("-" * 60)
    
    # Extract tasks
    tasks = re.findall(r"- \[[xX/\s]\] [^\n]+", content)
    if tasks:
        print("  Checklist Progress:")
        for t in tasks[:8]:  # show up to 8
            print(f"    {t}")
        if len(tasks) > 8:
            print(f"    ... and {len(tasks)-8} more tasks.")
    print("=" * 60)
    print(f"Successfully compiled handoff card: {handoff_path}\n")

if __name__ == "__main__":
    update_handoff()
