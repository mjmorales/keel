"""Tests for keel status — summary-only contract reporting (S1)."""

import subprocess
from textwrap import dedent

from click.testing import CliRunner

from keel_cli.main import cli


def _git_init(path):
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=path, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"],
        cwd=path,
        check=True,
    )


def _write_claude_md(project, body):
    keel_dir = project / ".keel"
    keel_dir.mkdir(parents=True, exist_ok=True)
    (keel_dir / "CLAUDE.md").write_text(body, encoding="utf-8")


CLAUDE_MD = dedent("""\
    # Project

    ## Segments

    ### app -- app/svc
    **Language**: python
    **Constraints**: `io-boundary`

    ### core -- core/lib
    **Language**: python
    **Constraints**: `pure-logic`

    ## Other
""")


def test_status_clean(tmp_path):
    _write_claude_md(tmp_path, CLAUDE_MD)
    (tmp_path / "app/svc").mkdir(parents=True)
    (tmp_path / "core/lib").mkdir(parents=True)
    (tmp_path / "core/lib/main.py").write_text("x = 1\n", encoding="utf-8")
    _git_init(tmp_path)

    result = CliRunner().invoke(cli, ["--project", str(tmp_path), "status"])
    assert result.exit_code == 0
    assert "Contracts: CLEAN" in result.output


def test_status_summarizes_violations_without_dumping(tmp_path):
    _write_claude_md(tmp_path, CLAUDE_MD)
    app = tmp_path / "app/svc"
    core = tmp_path / "core/lib"
    app.mkdir(parents=True)
    core.mkdir(parents=True)
    (core / "__init__.py").write_text("", encoding="utf-8")
    (app / "main.py").write_text("from core.lib import x\n", encoding="utf-8")
    _git_init(tmp_path)

    result = CliRunner().invoke(cli, ["--project", str(tmp_path), "status"])
    assert result.exit_code == 0  # status itself does not fail
    assert "violation(s) (run `keel check`)" in result.output
    # status must NOT dump check's per-violation lines or ADR footer.
    assert "[cross-segment]" not in result.output
    assert "file an ADR" not in result.output
