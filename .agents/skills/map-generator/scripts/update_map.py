import os
import re
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
        # Fallback to relative navigation
        return Path(__file__).resolve().parents[4]


# Config
PROJECT_ROOT = _get_project_root()
AGENT_DIR = PROJECT_ROOT / ".agents"
PERSONAS_DIR = AGENT_DIR / "personas"
SKILLS_DIR = AGENT_DIR / "skills"
OUTPUT_FILE = AGENT_DIR / "agent-map.md"

def parse_frontmatter(file_path):
    """Parses key-value pairs from YAML frontmatter between triple dashes (---)"""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return {}

    frontmatter_text = match.group(1)
    metadata = {}
    lines = frontmatter_text.splitlines()
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()
            
            # Handle YAML multiline block scalars (> or |)
            if val in (">", "|"):
                block_type = val
                block_lines = []
                i += 1
                
                # Determine indentation from the first indented non-empty line
                indent_level = None
                while i < len(lines):
                    next_line = lines[i]
                    next_stripped = next_line.strip()
                    
                    if not next_stripped:
                        block_lines.append("")
                        i += 1
                        continue
                    
                    current_indent = len(next_line) - len(next_line.lstrip())
                    if indent_level is None:
                        if current_indent == 0:
                            break
                        indent_level = current_indent
                    
                    if current_indent < indent_level:
                        break
                    
                    block_lines.append(next_line[indent_level:])
                    i += 1
                
                if block_type == ">":
                    # Folded style: join paragraphs with spaces
                    paragraphs = []
                    curr_para = []
                    for bl in block_lines:
                        if not bl.strip():
                            if curr_para:
                                paragraphs.append(" ".join(curr_para))
                                curr_para = []
                        else:
                            curr_para.append(bl.strip())
                    if curr_para:
                        paragraphs.append(" ".join(curr_para))
                    val_str = " ".join(paragraphs)
                else:
                    # Literal style
                    val_str = "\n".join(block_lines).rstrip()
                
                metadata[key] = val_str
                continue
            else:
                # Clean up outer quotes
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                metadata[key] = val
        i += 1
    return metadata


def build_map():
    print(f"Scanning .agents directory...")
    
    # 1. Gather Personas
    personas = []
    if PERSONAS_DIR.exists():
        for file in PERSONAS_DIR.glob("*.md"):
            meta = parse_frontmatter(file)
            if meta:
                # Resolve relative path from agent-map.md (relative to AGENT_DIR)
                rel_path = file.relative_to(AGENT_DIR).as_posix()
                personas.append({
                    "name": meta.get("name", file.stem),
                    "description": meta.get("description", "No description provided."),
                    "skills": meta.get("skills", "None"),
                    "trigger": meta.get("trigger", "manual"),
                    "link": f"[{file.name}]({rel_path})"
                })

    # 2. Gather Skills
    skills = []
    if SKILLS_DIR.exists():
        for file in SKILLS_DIR.glob("**/SKILL.md"):
            meta = parse_frontmatter(file)
            if meta:
                rel_path = file.relative_to(AGENT_DIR).as_posix()
                skills.append({
                    "name": meta.get("name", file.parent.name),
                    "description": meta.get("description", "No description provided."),
                    "when_to_use": meta.get("when_to_use", "Always active"),
                    "link": f"[{file.parent.name}/SKILL.md]({rel_path})"
                })

    # 3. Generate Markdown Contents
    markdown_content = f"""# Workspace Agent Map (`agent-map.md`)

> [!NOTE]
> This file is auto-generated by the `map-generator` skill script. 
> Do not modify this file manually. Update individual file frontmatters instead.

---

## 👥 Personas & Roles

This table maps specialized developer personas, their responsibilities, and triggers:

| Persona | Description | Required Skills | Activation Trigger | Source File |
| :--- | :--- | :--- | :--- | :--- |
"""

    for p in sorted(personas, key=lambda x: x["name"]):
        markdown_content += f"| **@{p['name']}** | {p['description']} | `{p['skills']}` | `{p['trigger']}` | {p['link']} |\n"

    markdown_content += """
---

## 🔧 Skills & Instructions

This table maps reusable engineering guidelines and their dynamic trigger conditions:

| Skill | Description | Active Condition | Source File |
| :--- | :--- | :--- | :--- |
"""

    for s in sorted(skills, key=lambda x: x["name"]):
        markdown_content += f"| **{s['name']}** | {s['description']} | *{s['when_to_use']}* | {s['link']} |\n"

    # Write output
    OUTPUT_FILE.write_text(markdown_content, encoding="utf-8")
    print(f"Map successfully generated at: {OUTPUT_FILE}")

if __name__ == "__main__":
    build_map()
