"""Install smoke test for gitea_mcp's packaging.

Builds and installs the package into an isolated virtualenv, then invokes
the *installed* gitea-mcp command as a subprocess with GITEA_BASE_URL/
GITEA_TOKEN deliberately unset, asserting it fails fast with the expected
configuration error. This is the one test that exercises pyproject.toml's
packaging metadata (entry point registration, declared dependencies)
end-to-end — a broken [project.scripts] entry or a missing dependency
declaration wouldn't be caught by test_config_validation.py's direct,
in-process unit tests.

Slower than the rest of the suite (creates a venv, installs real
dependencies from PyPI) — run on its own with:
    pytest tests/test_install_smoke.py -v
"""
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INSTALL_TIMEOUT_S = 180
RUN_TIMEOUT_S = 15


def test_installed_command_fails_fast_without_config(tmp_path):
    venv_dir = tmp_path / "venv"
    subprocess.run(
        [sys.executable, "-m", "venv", str(venv_dir)],
        check=True, timeout=INSTALL_TIMEOUT_S,
    )
    venv_python = venv_dir / "bin" / "python3"
    venv_gitea_mcp = venv_dir / "bin" / "gitea-mcp"

    subprocess.run(
        [str(venv_python), "-m", "pip", "install", "--quiet", str(PROJECT_ROOT)],
        check=True, timeout=INSTALL_TIMEOUT_S,
    )
    assert venv_gitea_mcp.exists(), "pip install did not produce a gitea-mcp command"

    env_without_config = {"PATH": "/usr/bin:/bin"}
    result = subprocess.run(
        [str(venv_gitea_mcp)],
        capture_output=True, text=True, timeout=RUN_TIMEOUT_S,
        env=env_without_config,
    )

    assert result.returncode != 0
    assert "GITEA_BASE_URL and GITEA_TOKEN must both be set" in result.stderr
