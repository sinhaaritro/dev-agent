---
name: map-generator
description: Automatically aggregates persona and skill metadata into the central agent-map.md database.
when_to_use: "Triggers automatically whenever files in personas/ or skills/ are created, updated, or deleted."
---

# Map Generator Skill (`map-generator`)

**Purpose**: Automate the collection of workspace metadata to keep [agent-map.md](../../agent-map.md) fully sync'd with zero manual configuration.

---

## ⚙️ Trigger Strategy

1. **Automation**: Run `task update-map` after making changes to the `.agents/` configuration files.
2. **Verification**: After execution, inspect the newly generated `agent-map.md` to ensure it is not blank and lists all active skills and personas.

---

## 📜 Metadata Rules

To be correctly cataloged, all files must define these YAML fields in their frontmatter:
*   **Personas** (`personas/*.md`): Must include `name`, `description`, and `skills`.
*   **Skills** (`skills/**/SKILL.md`): Must include `name`, `description`, and `when_to_use`.
