<div align="center">

<img src="assets/banner.png" alt="Gitea MCP" width="100%" />

# Gitea MCP

**A local MCP server that gives Claude Desktop — and any MCP client — the ability to work with a self-hosted Gitea instance.**

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/protocol-MCP-6f42c1)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

</div>

---

MCP clients — Claude Desktop included — have no built-in way to reach a self-hosted Gitea instance. `gitea_mcp` closes that gap: it's a local MCP server that gives any MCP-compatible client the ability to list and search repos, manage issues and pull requests, and read/write files directly against your own Gitea instance.

As a bonus, it does this without routing through a third-party gateway — most MCP setups for Git hosting (Composio and similar) put a gateway between your agent and your infrastructure, holding your token and brokering every API call. `gitea_mcp` skips that entirely: it runs as a subprocess on your own machine, talks over stdio, and speaks directly to your Gitea instance — your token and repo data never pass through anyone else's server.

> [!NOTE]
> This project is intentionally local-only. There's no hosted endpoint, no third-party account, and no server to deploy — just a command your MCP client launches on demand.

## Features

- **Direct connection** — talks straight to `GITEA_BASE_URL`, nothing in between
- **Repositories** — list and search
- **Issues** — list (filtered by state) and create
- **Pull requests** — list (filtered by state) and create
- **Files** — read content and write (create or update) as a single commit, with SHA-based conflict protection
- **Commits** — list history, optionally scoped to one file
- **Actionable errors** — auth, not-found, permission, conflict, and validation failures all come back as specific, readable messages instead of raw exceptions

## Prerequisites

- Python 3.9 or later
- [pipx](https://pipx.pypa.io/) or [uv](https://docs.astral.sh/uv/) (for the recommended install path below)
- A running Gitea instance you have API access to
- A Gitea personal access token

## Install

**Recommended** — installs a `gitea-mcp` command directly from this repo, no manual venv management:

```bash
pipx install git+https://github.com/datamathcode/gitea-mcp.git
# or
uv tool install git+https://github.com/datamathcode/gitea-mcp.git
```

**Manual / development install** — for contributing, or an editable local install:

```bash
git clone https://github.com/datamathcode/gitea-mcp.git
cd gitea-mcp
python3 -m venv venv
source venv/bin/activate   # venv\Scripts\activate on Windows
pip install -e .
```

Both paths register the same `gitea-mcp` command.

> [!IMPORTANT]
> Dependencies are pinned to `mcp==1.9.4` deliberately. Newer `mcp` releases (2.0.0+) restructured the package and no longer expose `FastMCP` at the path this server imports it from.

## Configure

Generate a token in Gitea under **Settings → Applications → Generate New Token**, scoped narrowly to what this server needs (repo read/write, issue read/write) rather than every permission available.

```bash
export GITEA_BASE_URL="https://gitea.example.com"
export GITEA_TOKEN="<your token>"
```

The server refuses to start if either variable is missing — no silent fallback to a hardcoded value.

## Usage

`gitea_mcp` is a standard MCP server communicating over stdio — it works with any MCP-compatible client, not just Claude Desktop. Any client that can launch a local subprocess and speak the MCP protocol can use it; point it at the installed command's path and set `GITEA_BASE_URL`/`GITEA_TOKEN` in the environment it launches with.

### Run standalone

```bash
gitea-mcp
```

(Running from a source checkout without installing still works too: `python3 gitea_mcp.py`.)

### Add to an MCP client

`gitea_mcp` works the same way with every client below: point it at the installed command's absolute path, and set `GITEA_BASE_URL`/`GITEA_TOKEN` in the environment it launches with. Each client just has its own config file and format for expressing that.

First, find the installed command's absolute path:

```bash
which gitea-mcp
```

#### Claude Desktop

In Claude Desktop's MCP config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "gitea": {
      "command": "/absolute/path/from/which/gitea-mcp",
      "env": {
        "GITEA_BASE_URL": "https://gitea.example.com",
        "GITEA_TOKEN": "<your token>"
      }
    }
  }
}
```

> [!IMPORTANT]
> Use the full path from `which gitea-mcp`, not just `"gitea-mcp"`. Claude Desktop, launched via Finder/Dock on macOS, doesn't inherit your shell's `PATH` additions — a bare command name resolves fine from a terminal but fails to launch from Claude Desktop's config. Check whether your client has the same limitation before assuming a bare command name will work.

---

#### Claude Code

```bash
claude mcp add --transport stdio gitea --env GITEA_BASE_URL=https://gitea.example.com --env GITEA_TOKEN=YOUR_TOKEN_HERE -- /absolute/path/from/which/gitea-mcp
```

Docs: [code.claude.com/docs/en/mcp-quickstart](https://code.claude.com/docs/en/mcp-quickstart)

---

#### Codex

```bash
codex mcp add gitea --env GITEA_BASE_URL=https://gitea.example.com --env GITEA_TOKEN=YOUR_TOKEN_HERE -- /absolute/path/from/which/gitea-mcp
```

Docs: [learn.chatgpt.com/docs/extend/mcp](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)

---

#### Hermes Agent

In `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  gitea:
    command: "/absolute/path/from/which/gitea-mcp"
    env:
      GITEA_BASE_URL: "https://gitea.example.com"
      GITEA_TOKEN: "<your token>"
```

Docs: [hermes-agent.nousresearch.com/docs/user-guide/features/mcp](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp)

---

#### OpenCode

In `.opencode.json` — note `env` here is an array of `"KEY=value"` strings, not an object like the other clients above:

```json
{
  "mcpServers": {
    "gitea": {
      "type": "stdio",
      "command": "/absolute/path/from/which/gitea-mcp",
      "args": [],
      "env": ["GITEA_BASE_URL=https://gitea.example.com", "GITEA_TOKEN=<your token>"]
    }
  }
}
```

Docs: [opencode-ai-opencode.mintlify.app/features/mcp-integration](https://opencode-ai-opencode.mintlify.app/features/mcp-integration)

Any MCP client launches the server the same way: as a subprocess, talking over stdio — no port to open, no service to keep running.

## Available tools

| Tool | Description |
| --- | --- |
| `gitea_list_repos` | List or search repositories accessible to the authenticated user |
| `gitea_list_issues` | List issues in a repository, filtered by state |
| `gitea_create_issue` | Create an issue with a title, body, and existing labels |
| `gitea_list_pull_requests` | List pull requests in a repository, filtered by state |
| `gitea_create_pull_request` | Open a pull request from one branch into another |
| `gitea_get_file_content` | Read a file's content and current blob SHA |
| `gitea_create_or_update_file` | Create or update a file as a single commit |
| `gitea_list_commits` | List commit history, optionally scoped to a file path |

## Scope

This is a first pass covering the core workflow — repos, issues, PRs, file read/write, and commit history. Branch management, releases, label administration, webhooks, and org-level operations aren't implemented yet. The plan is to expand once this core set proves out in real use rather than building everything speculatively up front.

## Testing

`tests/test_gitea_mcp.py` exercises all 8 tools against a real Gitea instance — no mocking of the Gitea API.

> [!WARNING]
> Point this at a disposable scratch repo, never a real project repo. The write tests create and clean up issues, pull requests, branches, and files as part of running.

```bash
pip install -e ".[dev]"
export GITEA_BASE_URL="https://gitea.example.com"
export GITEA_TOKEN="<your token>"
export TEST_REPO_OWNER="<owner of your scratch repo>"   # defaults to "dmc"
export TEST_REPO_NAME="<name of your scratch repo>"     # defaults to "gitea-mcp-test-repo"
pytest tests/ -v
```
