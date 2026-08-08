# Style Guide: gitea_mcp

The goal of this document is to ensure the codebase looks as if it were written by a single person. We distinguish between universal readability categories and project-specific values.

---

## 1. General Tier (Readability Standards)
Regardless of the language used, the following categories must be consistently applied across the project.

### 1.1 Structural Consistency
- **Indentation:** A single indentation method (tabs vs. spaces) and a fixed width must be used consistently to ensure cross-editor readability.
- **Naming Conventions:** A consistent pattern must be used for variables, functions, and classes to reduce cognitive load.
- **Capitalization:** Constants and specific types must follow a distinct, project-wide capitalization rule.
- *Source:* [Programming Style | Wikipedia](https://en.wikipedia.org/wiki/Programming_style)

### 1.2 Documentation Style
- **Commenting Philosophy:** Comments should explain the "Why" (intent) rather than the "What" (mechanics). The "What" should be evident from the code itself.
- *Source:* [Programming Style | Wikipedia](https://en.wikipedia.org/wiki/Programming_style)

### 1.3 Cross-Language Alignment
In projects using multiple languages, where possible, naming and organizational conventions should be aligned to assist developers switching contexts.
- *Source:* [Software Engineering at Google | Abseil](https://abseil.io/resources/swe-book/html/ch08.html)

---

## 2. Project Tier (Specific Values)

### 2.1 Visuals
- **Language:** Python 3, following [PEP 8](https://peps.python.org/pep-0008/) as the baseline.
- **Indentation:** 4 spaces, no tabs.
- **Line Length:** No hard wrap is currently enforced by tooling. Keep lines readable; wrapping around 100 characters is a reasonable target if a formatter is later adopted.

### 2.2 Naming Conventions
- **Variables/Functions:** `snake_case` (e.g. `gitea_list_repos`, `_handle_api_error`). Internal/module-private helpers are prefixed with a single underscore (`_request`, `_paginated`).
- **Classes/Types:** `PascalCase` (e.g. `RepoRef`, `ListReposInput`). Pydantic input models are named `<Verb><Noun>Input` for tool parameters, or a bare noun (`RepoRef`) for shared shapes other models inherit from.
- **Constants:** `SCREAMING_SNAKE_CASE` (e.g. `GITEA_BASE_URL`, `API_BASE`, `HEADERS`).
- **MCP tool names:** the registered `name=` on `@mcp.tool` matches the Python function name exactly, prefixed `gitea_` (e.g. `gitea_create_issue`).

### 2.3 Documentation
- Every `@mcp.tool` function has a docstring with a one-line summary, an `Args:` section describing the input model's fields, and a `Returns:` section describing the JSON shape returned — this is the primary contract surface for the MCP client and must stay accurate.

### 2.4 Linting & Automation
- **Tooling:** None is currently configured — no linter or formatter is pinned in `pyproject.toml`. Until one is adopted, contributions should follow this document manually. If a formatter is added later, prefer `black`/`ruff` defaults over inventing project-specific rules that diverge from PEP 8.
