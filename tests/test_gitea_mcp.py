"""Live-instance tests for gitea_mcp, per CODING_STANDARDS.md 2.1: these run
against a real Gitea instance, not a mocked _request() boundary.

Requires the same environment gitea_mcp.py itself needs (GITEA_BASE_URL,
GITEA_TOKEN), plus write access to a disposable scratch repo — configured via
TEST_REPO_OWNER / TEST_REPO_NAME, defaulting to the project's standard test
repo (dmc/gitea-mcp-test-repo). Do not point this at a real project repo:
the write-tool tests create issues, files, and pull requests.
"""
import asyncio
import json
import os
import time

import pytest
from pydantic import ValidationError

import gitea_mcp as m

TEST_REPO_OWNER = os.environ.get("TEST_REPO_OWNER", "dmc")
TEST_REPO_NAME = os.environ.get("TEST_REPO_NAME", "gitea-mcp-test-repo")


def run(coro):
    return asyncio.run(coro)


def call(tool, params):
    return json.loads(run(tool(params)))


# --------------------------------------------------------------------------
# Test-only cleanup helpers. gitea_mcp's tool surface has no delete/close
# operations (correctly out of scope for the server), so teardown talks to
# Gitea directly via the same _request() helper the tools use internally —
# this is test arrangement, not something under test.
# --------------------------------------------------------------------------

def _close_issue(number):
    run(m._request("PATCH", f"/repos/{TEST_REPO_OWNER}/{TEST_REPO_NAME}/issues/{number}", json={"state": "closed"}))


def _close_pull_request(number):
    run(m._request("PATCH", f"/repos/{TEST_REPO_OWNER}/{TEST_REPO_NAME}/pulls/{number}", json={"state": "closed"}))


def _delete_file(path, sha):
    run(m._request("DELETE", f"/repos/{TEST_REPO_OWNER}/{TEST_REPO_NAME}/contents/{path}", json={"message": "mcp test cleanup", "sha": sha}))


def _delete_branch(branch):
    run(m._request("DELETE", f"/repos/{TEST_REPO_OWNER}/{TEST_REPO_NAME}/branches/{branch}"))


# --------------------------------------------------------------------------
# Read-only tools
# --------------------------------------------------------------------------

def test_list_repos_happy_path():
    result = call(m.gitea_list_repos, m.ListReposInput())
    assert set(result.keys()) == {"page", "limit", "count", "has_more", "items"}
    assert any(r["full_name"] == f"{TEST_REPO_OWNER}/{TEST_REPO_NAME}" for r in result["items"])


def test_list_repos_query_filters_by_name():
    result = call(m.gitea_list_repos, m.ListReposInput(query=TEST_REPO_NAME))
    assert result["count"] == 1
    assert result["items"][0]["full_name"] == f"{TEST_REPO_OWNER}/{TEST_REPO_NAME}"


def test_list_issues_happy_path_on_empty_repo():
    result = call(
        m.gitea_list_issues,
        m.ListIssuesInput(owner=TEST_REPO_OWNER, repo=TEST_REPO_NAME, state="all"),
    )
    assert set(result.keys()) == {"page", "limit", "count", "has_more", "items"}


def test_list_pull_requests_happy_path_on_empty_repo():
    result = call(
        m.gitea_list_pull_requests,
        m.ListPullRequestsInput(owner=TEST_REPO_OWNER, repo=TEST_REPO_NAME, state="all"),
    )
    assert set(result.keys()) == {"page", "limit", "count", "has_more", "items"}


def test_list_commits_returns_pagination_envelope():
    result = call(
        m.gitea_list_commits,
        m.ListCommitsInput(owner=TEST_REPO_OWNER, repo=TEST_REPO_NAME),
    )
    assert set(result.keys()) == {"page", "limit", "count", "has_more", "items"}
    assert result["count"] >= 1
    first = result["items"][0]
    assert set(first.keys()) == {"sha", "message", "author", "date"}


def test_get_file_content_happy_path_on_readme():
    result = call(
        m.gitea_get_file_content,
        m.GetFileContentInput(owner=TEST_REPO_OWNER, repo=TEST_REPO_NAME, path="README.md"),
    )
    assert result["path"] == "README.md"
    assert isinstance(result["sha"], str) and result["sha"]
    assert isinstance(result["content"], str)


def test_get_file_content_not_found_returns_actionable_error():
    result = run(m.gitea_get_file_content(
        m.GetFileContentInput(owner=TEST_REPO_OWNER, repo=TEST_REPO_NAME, path="this-file-does-not-exist.md")
    ))
    assert result.startswith("Error: not found")


# --------------------------------------------------------------------------
# Input validation (no network — the point is that these never reach Gitea)
# --------------------------------------------------------------------------

def test_list_issues_rejects_invalid_state_before_hitting_api():
    with pytest.raises(ValidationError):
        m.ListIssuesInput(owner=TEST_REPO_OWNER, repo=TEST_REPO_NAME, state="bogus")


def test_list_pull_requests_rejects_invalid_state_before_hitting_api():
    with pytest.raises(ValidationError):
        m.ListPullRequestsInput(owner=TEST_REPO_OWNER, repo=TEST_REPO_NAME, state="bogus")


# --------------------------------------------------------------------------
# Write tools — mutate TEST_REPO_OWNER/TEST_REPO_NAME. Each uses a
# timestamp-unique title/path so repeated runs don't collide.
# --------------------------------------------------------------------------

def test_create_issue_then_appears_in_list():
    title = f"mcp-test-issue-{int(time.time())}"
    created = call(
        m.gitea_create_issue,
        m.CreateIssueInput(owner=TEST_REPO_OWNER, repo=TEST_REPO_NAME, title=title, body="Created by gitea_mcp live test."),
    )
    try:
        assert created["title"] == title
        assert created["state"] == "open"
        assert isinstance(created["number"], int)

        listing = call(
            m.gitea_list_issues,
            m.ListIssuesInput(owner=TEST_REPO_OWNER, repo=TEST_REPO_NAME, state="open"),
        )
        assert any(i["number"] == created["number"] and i["title"] == title for i in listing["items"])
    finally:
        _close_issue(created["number"])


def test_create_or_update_file_roundtrip():
    path = f"mcp-test-{int(time.time())}.md"

    created = call(
        m.gitea_create_or_update_file,
        m.CreateOrUpdateFileInput(owner=TEST_REPO_OWNER, repo=TEST_REPO_NAME, path=path, content="first version\n", message="mcp test: create file"),
    )
    try:
        assert created["action"] == "created"
        assert created["path"] == path

        fetched = call(
            m.gitea_get_file_content,
            m.GetFileContentInput(owner=TEST_REPO_OWNER, repo=TEST_REPO_NAME, path=path),
        )
        assert fetched["content"] == "first version\n"

        updated = call(
            m.gitea_create_or_update_file,
            m.CreateOrUpdateFileInput(
                owner=TEST_REPO_OWNER, repo=TEST_REPO_NAME, path=path,
                content="second version\n", message="mcp test: update file", sha=fetched["sha"],
            ),
        )
        assert updated["action"] == "updated"

        refetched = call(
            m.gitea_get_file_content,
            m.GetFileContentInput(owner=TEST_REPO_OWNER, repo=TEST_REPO_NAME, path=path),
        )
        assert refetched["content"] == "second version\n"
    finally:
        final = call(m.gitea_get_file_content, m.GetFileContentInput(owner=TEST_REPO_OWNER, repo=TEST_REPO_NAME, path=path))
        _delete_file(path, final["sha"])


def test_create_or_update_file_stale_sha_returns_validation_error():
    # Observed live: Gitea's contents-write API returns 422 ("sha does not
    # match") for any sha mismatch, not 409 — confirmed for both a garbage
    # sha and a genuinely stale (previously-valid, now-outdated) one. This
    # is the project's live coverage of the 422 error class.
    path = f"mcp-test-conflict-{int(time.time())}.md"
    call(
        m.gitea_create_or_update_file,
        m.CreateOrUpdateFileInput(owner=TEST_REPO_OWNER, repo=TEST_REPO_NAME, path=path, content="v1\n", message="mcp test: conflict setup"),
    )
    try:
        result = run(m.gitea_create_or_update_file(
            m.CreateOrUpdateFileInput(owner=TEST_REPO_OWNER, repo=TEST_REPO_NAME, path=path, content="v2\n", message="mcp test: stale write", sha="0000000000000000000000000000000000000000")
        ))
        assert result.startswith("Error: validation failed")
        assert "sha does not match" in result
    finally:
        current = call(m.gitea_get_file_content, m.GetFileContentInput(owner=TEST_REPO_OWNER, repo=TEST_REPO_NAME, path=path))
        _delete_file(path, current["sha"])


def test_list_repos_invalid_token_returns_auth_error():
    original = m.HEADERS["Authorization"]
    m.HEADERS["Authorization"] = "token invalid_token_for_test"
    try:
        result = run(m.gitea_list_repos(m.ListReposInput()))
        assert result.startswith("Error: authentication failed")
    finally:
        m.HEADERS["Authorization"] = original


def test_create_pull_request_then_appears_in_list():
    # Branch creation isn't part of gitea_mcp's tool surface (explicitly
    # deferred scope per the spec), so the test arranges its own source
    # branch directly against Gitea's API rather than through a tool.
    branch = f"mcp-test-branch-{int(time.time())}"
    path = f"mcp-test-pr-{int(time.time())}.md"
    run(m._request(
        "POST", f"/repos/{TEST_REPO_OWNER}/{TEST_REPO_NAME}/branches",
        json={"new_branch_name": branch, "old_branch_name": "main"},
    ))

    try:
        call(
            m.gitea_create_or_update_file,
            m.CreateOrUpdateFileInput(owner=TEST_REPO_OWNER, repo=TEST_REPO_NAME, path=path, content="pr test\n", message="mcp test: pr source commit", branch=branch),
        )

        created = call(
            m.gitea_create_pull_request,
            m.CreatePullRequestInput(owner=TEST_REPO_OWNER, repo=TEST_REPO_NAME, title=f"mcp test PR {branch}", head=branch, base="main"),
        )
        try:
            assert created["state"] == "open"
            assert isinstance(created["number"], int)

            listing = call(
                m.gitea_list_pull_requests,
                m.ListPullRequestsInput(owner=TEST_REPO_OWNER, repo=TEST_REPO_NAME, state="open"),
            )
            assert any(p["number"] == created["number"] for p in listing["items"])
        finally:
            _close_pull_request(created["number"])
    finally:
        _delete_branch(branch)
