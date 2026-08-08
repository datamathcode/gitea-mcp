"""
gitea_mcp — a local MCP server for Gitea, built to bypass hosted third-party
gateways (e.g. Composio) entirely. Runs over stdio, talks directly to your
own Gitea instance, and never sends your token or repo data anywhere but
between this process and GITEA_BASE_URL.

Setup:
    export GITEA_BASE_URL="https://gitea.example.com"
    export GITEA_TOKEN="<your Gitea personal access token>"
    python gitea_mcp.py

Add to Claude Desktop's local MCP config (claude_desktop_config.json):
    {
      "mcpServers": {
        "gitea": {
          "command": "python",
          "args": ["/path/to/gitea_mcp.py"],
          "env": {
            "GITEA_BASE_URL": "https://gitea.example.com",
            "GITEA_TOKEN": "<your token>"
          }
        }
      }
    }

Generate a token in Gitea under Settings -> Applications -> Generate New
Token. Scope it to only what this server needs (repo read/write, issue
read/write) rather than an all-scopes token.
"""

import base64
import json
import os
from typing import Annotated, Any, Dict, List, Literal, Optional

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

GITEA_BASE_URL = os.environ.get("GITEA_BASE_URL", "").rstrip("/")
GITEA_TOKEN = os.environ.get("GITEA_TOKEN", "")


def _validate_config() -> None:
    """Raise if required environment configuration is missing.

    Called from main() rather than at import time, so importing this module
    (e.g. for testing) has no side effect — only actually starting the
    server requires GITEA_BASE_URL/GITEA_TOKEN to be set.
    """
    if not GITEA_BASE_URL or not GITEA_TOKEN:
        raise RuntimeError(
            "GITEA_BASE_URL and GITEA_TOKEN must both be set as environment "
            "variables before starting this server. Never hardcode a token "
            "in this file."
        )


API_BASE = f"{GITEA_BASE_URL}/api/v1"
HEADERS = {
    "Authorization": f"token {GITEA_TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

mcp = FastMCP("gitea_mcp")


# --------------------------------------------------------------------------
# Shared HTTP client and error handling
# --------------------------------------------------------------------------

async def _request(method: str, path: str, **kwargs) -> httpx.Response:
    """Centralized request helper — every tool routes through this so auth,
    base URL, and error handling stay in one place rather than duplicated
    per tool."""
    url = f"{API_BASE}{path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(method, url, headers=HEADERS, **kwargs)
        response.raise_for_status()
        return response


def _handle_api_error(e: Exception) -> str:
    """Consistent, actionable error formatting across all tools."""
    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        if status == 404:
            return "Error: not found. Check the owner/repo name and that the resource (issue/PR/file) actually exists."
        if status == 401:
            return "Error: authentication failed. GITEA_TOKEN is missing, expired, or invalid — check it in Gitea under Settings > Applications."
        if status == 403:
            return "Error: permission denied. Your token's scope may not cover this operation — check its granted scopes in Gitea."
        if status == 409:
            return "Error: conflict. For file writes, this usually means the file changed since you last read it — re-fetch it and retry with the current sha."
        if status == 422:
            return f"Error: validation failed — {e.response.text}"
        return f"Error: Gitea API returned status {status}: {e.response.text}"
    if isinstance(e, httpx.TimeoutException):
        return "Error: request to Gitea timed out. Check that the instance is reachable and not overloaded."
    if isinstance(e, httpx.ConnectError):
        return f"Error: could not connect to {GITEA_BASE_URL}. Check the URL and that the instance is up."
    return f"Error: unexpected error ({type(e).__name__}): {e}"


def _paginated(items: List[Dict[str, Any]], page: int, limit: int) -> Dict[str, Any]:
    """Standard pagination envelope, shared across all list tools."""
    return {
        "page": page,
        "limit": limit,
        "count": len(items),
        "has_more": len(items) == limit,
        "items": items,
    }


# --------------------------------------------------------------------------
# Input models
# --------------------------------------------------------------------------

class GiteaBaseModel(BaseModel):
    """Shared Pydantic config for every tool input model."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class PaginationParams(GiteaBaseModel):
    page: int = Field(default=1, description="Page number, starting at 1.", ge=1)
    limit: int = Field(default=20, description="Results per page.", ge=1, le=50)


class ListReposInput(PaginationParams):
    query: Optional[str] = Field(default=None, description="Optional search term to filter repos by name (e.g. 'lemma').")


class RepoRef(GiteaBaseModel):
    owner: str = Field(..., description="Repository owner or organization, e.g. 'david'.", min_length=1)
    repo: str = Field(..., description="Repository name, e.g. 'lemma'.", min_length=1)


class ListIssuesInput(RepoRef, PaginationParams):
    state: Literal["open", "closed", "all"] = Field(default="open", description="Filter by state.")


class CreateIssueInput(RepoRef):
    title: str = Field(..., description="Issue title.", min_length=1, max_length=255)
    body: Optional[str] = Field(default="", description="Issue body/description in Markdown.")
    labels: Optional[List[str]] = Field(default_factory=list, description="Label names to apply, if they already exist in the repo.")


class ListPullRequestsInput(RepoRef, PaginationParams):
    state: Literal["open", "closed", "all"] = Field(default="open", description="Filter by state.")


class CreatePullRequestInput(RepoRef):
    title: str = Field(..., description="Pull request title.", min_length=1, max_length=255)
    head: str = Field(..., description="Source branch containing the changes, e.g. 'feature/x'.", min_length=1)
    base: str = Field(..., description="Target branch the changes merge into, e.g. 'main'.", min_length=1)
    body: Optional[str] = Field(default="", description="Pull request description in Markdown.")


class GetFileContentInput(RepoRef):
    path: str = Field(..., description="File path within the repo, e.g. 'lemma-lab-charter.md'.", min_length=1)
    ref: Optional[str] = Field(default=None, description="Branch, tag, or commit SHA. Defaults to the repo's default branch.")


class CreateOrUpdateFileInput(RepoRef):
    path: str = Field(..., description="File path within the repo to write to.", min_length=1)
    content: Annotated[str, StringConstraints(strip_whitespace=False)] = Field(..., description="Full new file content, as plain text (not base64 — this tool handles encoding). Preserved exactly, including leading/trailing whitespace.")
    message: str = Field(..., description="Commit message.", min_length=1)
    branch: Optional[str] = Field(default=None, description="Branch to commit to. Defaults to the repo's default branch.")
    sha: Optional[str] = Field(default=None, description="Required when updating an existing file — the file's current blob SHA, from get_file_content. Omit when creating a new file.")


class ListCommitsInput(RepoRef, PaginationParams):
    path: Optional[str] = Field(default=None, description="Limit history to commits touching this file path.")


# --------------------------------------------------------------------------
# Tools
# --------------------------------------------------------------------------

@mcp.tool(
    name="gitea_list_repos",
    annotations={"title": "List Gitea Repositories", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
)
async def gitea_list_repos(params: ListReposInput) -> str:
    """List repositories accessible to the authenticated Gitea user, optionally filtered by name.

    Args:
        params (ListReposInput): query (optional search term), page, limit.

    Returns:
        str: JSON with pagination envelope and a list of repos (full_name, description, private, default_branch, updated_at).
    """
    try:
        path = "/repos/search" if params.query else "/user/repos"
        query_params = {"page": params.page, "limit": params.limit}
        if params.query:
            query_params["q"] = params.query
        resp = await _request("GET", path, params=query_params)
        data = resp.json()
        raw_items = data.get("data", data) if isinstance(data, dict) else data
        items = [
            {
                "full_name": r.get("full_name"),
                "description": r.get("description"),
                "private": r.get("private"),
                "default_branch": r.get("default_branch"),
                "updated_at": r.get("updated_at"),
            }
            for r in raw_items
        ]
        return json.dumps(_paginated(items, params.page, params.limit), indent=2)
    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="gitea_list_issues",
    annotations={"title": "List Repository Issues", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
)
async def gitea_list_issues(params: ListIssuesInput) -> str:
    """List issues in a repository, filtered by state.

    Args:
        params (ListIssuesInput): owner, repo, state ('open'/'closed'/'all'), page, limit.

    Returns:
        str: JSON with pagination envelope and a list of issues (number, title, state, created_at, labels).
    """
    try:
        resp = await _request(
            "GET",
            f"/repos/{params.owner}/{params.repo}/issues",
            params={"state": params.state, "page": params.page, "limit": params.limit, "type": "issues"},
        )
        raw_items = resp.json()
        items = [
            {
                "number": i.get("number"),
                "title": i.get("title"),
                "state": i.get("state"),
                "created_at": i.get("created_at"),
                "labels": [l.get("name") for l in i.get("labels", [])],
            }
            for i in raw_items
        ]
        return json.dumps(_paginated(items, params.page, params.limit), indent=2)
    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="gitea_create_issue",
    annotations={"title": "Create an Issue", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": True},
)
async def gitea_create_issue(params: CreateIssueInput) -> str:
    """Create a new issue in a repository.

    Args:
        params (CreateIssueInput): owner, repo, title, body, labels (label names, must already exist in the repo).

    Returns:
        str: JSON with the created issue's number, title, state, and URL.
    """
    try:
        payload = {"title": params.title, "body": params.body}
        resp = await _request("POST", f"/repos/{params.owner}/{params.repo}/issues", json=payload)
        issue = resp.json()
        if params.labels:
            label_resp = await _request("GET", f"/repos/{params.owner}/{params.repo}/labels", params={"limit": 50})
            label_map = {l["name"]: l["id"] for l in label_resp.json()}
            label_ids = [label_map[name] for name in params.labels if name in label_map]
            if label_ids:
                await _request(
                    "PATCH",
                    f"/repos/{params.owner}/{params.repo}/issues/{issue['number']}",
                    json={"labels": label_ids},
                )
        return json.dumps(
            {"number": issue.get("number"), "title": issue.get("title"), "state": issue.get("state"), "html_url": issue.get("html_url")},
            indent=2,
        )
    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="gitea_list_pull_requests",
    annotations={"title": "List Pull Requests", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
)
async def gitea_list_pull_requests(params: ListPullRequestsInput) -> str:
    """List pull requests in a repository, filtered by state.

    Args:
        params (ListPullRequestsInput): owner, repo, state ('open'/'closed'/'all'), page, limit.

    Returns:
        str: JSON with pagination envelope and a list of PRs (number, title, state, head branch, base branch, mergeable).
    """
    try:
        resp = await _request(
            "GET",
            f"/repos/{params.owner}/{params.repo}/pulls",
            params={"state": params.state, "page": params.page, "limit": params.limit},
        )
        raw_items = resp.json()
        items = [
            {
                "number": p.get("number"),
                "title": p.get("title"),
                "state": p.get("state"),
                "head": p.get("head", {}).get("ref"),
                "base": p.get("base", {}).get("ref"),
                "mergeable": p.get("mergeable"),
            }
            for p in raw_items
        ]
        return json.dumps(_paginated(items, params.page, params.limit), indent=2)
    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="gitea_create_pull_request",
    annotations={"title": "Create a Pull Request", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": True},
)
async def gitea_create_pull_request(params: CreatePullRequestInput) -> str:
    """Create a new pull request from one branch into another.

    Args:
        params (CreatePullRequestInput): owner, repo, title, head (source branch), base (target branch), body.

    Returns:
        str: JSON with the created PR's number, title, state, and URL.
    """
    try:
        payload = {"title": params.title, "head": params.head, "base": params.base, "body": params.body}
        resp = await _request("POST", f"/repos/{params.owner}/{params.repo}/pulls", json=payload)
        pr = resp.json()
        return json.dumps(
            {"number": pr.get("number"), "title": pr.get("title"), "state": pr.get("state"), "html_url": pr.get("html_url")},
            indent=2,
        )
    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="gitea_get_file_content",
    annotations={"title": "Read a File from a Repository", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
)
async def gitea_get_file_content(params: GetFileContentInput) -> str:
    """Read a file's content and metadata (including its current SHA, needed for updates).

    Args:
        params (GetFileContentInput): owner, repo, path, ref (branch/tag/commit, optional).

    Returns:
        str: JSON with path, sha, decoded content (text), and size. Content is decoded from base64 automatically.
    """
    try:
        query_params = {"ref": params.ref} if params.ref else {}
        resp = await _request("GET", f"/repos/{params.owner}/{params.repo}/contents/{params.path}", params=query_params)
        data = resp.json()
        raw_content = data.get("content", "")
        decoded = base64.b64decode(raw_content).decode("utf-8", errors="replace") if raw_content else ""
        return json.dumps({"path": data.get("path"), "sha": data.get("sha"), "size": data.get("size"), "content": decoded}, indent=2)
    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="gitea_create_or_update_file",
    annotations={"title": "Create or Update a File (Commit)", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": True},
)
async def gitea_create_or_update_file(params: CreateOrUpdateFileInput) -> str:
    """Create a new file, or update an existing one, as a single commit.

    To update an existing file, first call gitea_get_file_content to get its current
    sha, then pass that sha here — Gitea rejects updates without the correct current
    sha to prevent silently overwriting someone else's concurrent change. Omit sha
    when creating a brand-new file.

    Args:
        params (CreateOrUpdateFileInput): owner, repo, path, content (plain text), message, branch (optional), sha (required for updates).

    Returns:
        str: JSON with the new commit's sha and the file's path.
    """
    try:
        encoded = base64.b64encode(params.content.encode("utf-8")).decode("ascii")
        payload: Dict[str, Any] = {"content": encoded, "message": params.message}
        if params.branch:
            payload["branch"] = params.branch
        if params.sha:
            payload["sha"] = params.sha
        method = "PUT" if params.sha else "POST"
        resp = await _request(method, f"/repos/{params.owner}/{params.repo}/contents/{params.path}", json=payload)
        data = resp.json()
        commit = data.get("commit", {})
        return json.dumps({"path": params.path, "commit_sha": commit.get("sha"), "action": "updated" if params.sha else "created"}, indent=2)
    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="gitea_list_commits",
    annotations={"title": "List Commit History", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
)
async def gitea_list_commits(params: ListCommitsInput) -> str:
    """List recent commits in a repository, optionally scoped to a single file's history.

    Args:
        params (ListCommitsInput): owner, repo, path (optional, limits to commits touching this file), page, limit.

    Returns:
        str: JSON with pagination envelope and a list of commits (sha, message, author, date).
    """
    try:
        query_params: Dict[str, Any] = {"page": params.page, "limit": params.limit}
        if params.path:
            query_params["path"] = params.path
        resp = await _request("GET", f"/repos/{params.owner}/{params.repo}/commits", params=query_params)
        raw_items = resp.json()
        items = []
        for c in raw_items:
            commit_info = c.get("commit", {})
            author_info = commit_info.get("author", {})
            items.append({
                "sha": c.get("sha", "")[:12],
                "message": (commit_info.get("message") or "").split("\n")[0],
                "author": author_info.get("name"),
                "date": author_info.get("date"),
            })
        return json.dumps(_paginated(items, params.page, params.limit), indent=2)
    except Exception as e:
        return _handle_api_error(e)


def main() -> None:
    _validate_config()
    mcp.run()


if __name__ == "__main__":
    main()
