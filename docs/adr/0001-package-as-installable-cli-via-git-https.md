# Package as an installable CLI, distributed via git+https, with hatchling and static versioning

`gitea_mcp` is now a proper installable Python project (`pyproject.toml`, a `gitea-mcp` console-script entry point) rather than a loose script requiring a manual venv and a hand-edited absolute path in Claude Desktop's config. We decided `pipx`/`uv` should both work as install methods, which ruled out a lighter-weight alternative — a [PEP 723](https://peps.python.org/pep-0723/) inline-script metadata block run via `uv run`/`uvx` — since that path is uv-only and pipx has no equivalent for running a bare script. A real package was the only option that kept both tools on the table.

## Considered options

- **Build backend**: `hatchling` over `setuptools` (more config surface for no benefit here) or uv's own `uv_build` (fastest, but ties the build step to one tool's ecosystem — the opposite of what "supports pipx and uv" is trying to achieve). Chosen for being tool-agnostic.
- **Install source**: `git+https://github.com/datamathcode/gitea-mcp.git` over PyPI publishing. PyPI would mean zero-URL installs (`pipx install gitea-mcp`) but requires registering a PyPI project and setting up a trusted-publishing CI workflow — real one-time infrastructure work that isn't blocked by anything here and can be layered on later. Deferred as a non-goal for now, consistent with the project's existing "expand once the core set proves out" scope philosophy.
- **Versioning**: a static string in `pyproject.toml` (`0.1.0`, matching the already-cut `v0.1.0` tag) over git-tag-derived versioning via `hatch-vcs`. At this release cadence (one tag so far), the extra build dependency and slightly unusual between-tag version strings (`0.1.1.dev3+g<sha>`) weren't worth it. Revisit if release frequency picks up.
- **Layout**: kept `gitea_mcp.py` as a flat module rather than moving to a `src/` package directory — a single-file server doesn't need the import-shadowing protection `src/` layouts exist for.

## Consequences

Claude Desktop's config must reference the installed command's **absolute path**, not a bare `gitea-mcp` — Claude Desktop launched via Finder/Dock on macOS doesn't inherit shell `PATH` additions like `~/.local/bin`. This is documented in the README, not solved by the packaging itself.
