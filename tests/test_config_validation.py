"""Unit tests for gitea_mcp's config validation.

Unlike test_gitea_mcp.py, these need no network access and no live Gitea
instance — they test the extracted _validate_config() function directly,
without invoking main()/mcp.run() (which would block on the stdio server
loop). Importing gitea_mcp here works with no environment variables set at
all, which is itself the property this refactor exists to guarantee.
"""
import pytest

import gitea_mcp as m


def _set_config(base_url, token):
    m.GITEA_BASE_URL = base_url
    m.GITEA_TOKEN = token


@pytest.fixture(autouse=True)
def _restore_config():
    """Snapshot GITEA_BASE_URL/GITEA_TOKEN and restore them after each test.

    pytest runs fixture teardown (the code after yield) even when the test
    body raises, so a test can't leak a mutated config into the next one —
    same guarantee the old per-test try/finally blocks provided.
    """
    original = (m.GITEA_BASE_URL, m.GITEA_TOKEN)
    yield
    _set_config(*original)


def test_validate_config_raises_when_both_missing():
    _set_config("", "")
    with pytest.raises(RuntimeError, match="GITEA_BASE_URL and GITEA_TOKEN"):
        m._validate_config()


def test_validate_config_raises_when_only_token_missing():
    _set_config("https://gitea.example.com", "")
    with pytest.raises(RuntimeError, match="GITEA_BASE_URL and GITEA_TOKEN"):
        m._validate_config()


def test_validate_config_raises_when_only_base_url_missing():
    _set_config("", "some-token")
    with pytest.raises(RuntimeError, match="GITEA_BASE_URL and GITEA_TOKEN"):
        m._validate_config()


def test_validate_config_passes_when_both_present():
    _set_config("https://gitea.example.com", "some-token")
    m._validate_config()
