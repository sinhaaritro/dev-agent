# 🚀 {project_name}

> {purpose}

---

## 📖 Overview
This repository uses the agent-workspace setup. It establishes **system rules**, **personas**, **workflows**, and **reusable skills** that modern LLM-based coding assistants read and execute. 

* **Domain**: {domain}
* **Tech Stack**: {tech_stack}

---

## ⚡ Quick Start

### 1. Bootstrap the Template
Ensure you have Python 3.8+ and the [Taskfile](https://taskfile.dev) runner installed. Then run:
```bash
# Setup the Python virtual environment (.venv) and local binary folders (.bin)
task env:init

# Scaffold the Collaborative Memory System (CMS) docs/ layout
task docs:init all
```

### 2. Configure for Your Project
Edit `docs/project_profile.md` to define your project's technology stack, domain rules, and build/verify commands.
