# Contributing to gitea_mcp

Thank you for your interest in contributing! To maintain a high-velocity and sustainable project, we follow a tiered contribution framework.

---

## 1. General Tier (Universal Workflow)
These guidelines ensure a clean project history and a professional onboarding experience.

### 1.1 Communication & Spirit
- **Welcoming Environment:** We value constructive feedback and respectful communication. New contributors are encouraged to ask questions early.
- *Source:* [Best practices to manage an open source project | Codacy](https://blog.codacy.com/best-practices-to-manage-an-open-source-project)

### 1.2 Version Control Workflow
To maintain a readable and traceable git history:
- **Commit Messages:** Use the **imperative mood** (e.g., "Add user authentication" instead of "Added user authentication" or "Adds user authentication").
- **Traceability:** Every commit or Pull Request must reference a corresponding Issue number (e.g., `Fixes #123`).
- *Source:* [How to Build a CONTRIBUTING.md | contributing.md](https://contributing.md/how-to-build-contributing-md/)

### 1.3 Repository Hygiene
- **Template Usage:** Use the provided Issue and Pull Request templates located in the `.github/` directory to ensure all necessary information is captured.
- *Source:* [Writing Practical Contribution Guidelines | Hypertext Dispatches](https://tenthirtyam.org/dispatches/2026/03/21/writing-practical-contribution-guidelines-for-github-repositories/)

---

## 2. Project Tier (Local Setup)

### 2.1 Local Environment Setup
- **Prerequisites:** Python 3.9 or later, a Gitea instance you have API access to, and a scoped Gitea personal access token.
- **Installation:**
  ```bash
  git clone https://github.com/datamathcode/gitea-mcp.git
  cd gitea-mcp
  python3 -m venv venv
  source venv/bin/activate
  pip install -e ".[dev]"
  ```
  `pip install -e .` registers the same `gitea-mcp` console-script entry point the packaged install (`pipx`/`uv`) does — the `[dev]` extra additionally pulls in `pytest` for running the test suite.
- **Configuration:** `export GITEA_BASE_URL="https://your-gitea-instance"` and `export GITEA_TOKEN="<your token>"` — see the README for the full setup and MCP client configuration.

### 2.2 Branching Strategy
- **Naming Convention:** `feature/<short-description>` for new tools/capabilities, `fix/<short-description>` for bug fixes, `docs/<short-description>` for documentation-only changes.
- **Target Branch:** All PRs target `main` — there is no separate `develop` branch for this project.

### 2.3 Submission Checklist
- [ ] Code follows `STYLE.md`
- [ ] New/changed tools follow the architectural constraints in `CODING_STANDARDS.md` (single `_request()` boundary, centralized error translation, env-var-only secrets, schema-validated input)
- [ ] Tests added/updated and passing against a live (disposable) Gitea instance
- [ ] README and/or `docs/agents/*.md` updated if the change affects setup, tool surface, or project conventions
