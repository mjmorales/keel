"""End-to-end tests for keel check contract enforcement.

These cover the import-normalization layer (P1): cross-segment, forbidden,
and io-in-pure-logic detection across the languages whose extractors were
previously inert (Python, GDScript).
"""

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


def _run_check(project):
    return CliRunner().invoke(cli, ["--project", str(project), "check"])


CLAUDE_MD = dedent("""\
    # Project

    ## Segments

    ### foo -- segments/foo
    **Language**: gdscript
    **Constraints**: `pure-logic`

    ### bar -- segments/bar
    **Language**: gdscript
    **Constraints**: `io-boundary`

    ### core -- core/lib
    **Language**: python
    **Constraints**: `pure-logic`

    ## Other
""")


class TestCrossSegment:
    def test_gdscript_preload_cross_segment_detected(self, tmp_path):
        _write_claude_md(tmp_path, CLAUDE_MD)
        foo = tmp_path / "segments/foo"
        bar = tmp_path / "segments/bar"
        foo.mkdir(parents=True)
        bar.mkdir(parents=True)
        (bar / "thing.gd").write_text("extends Node\n", encoding="utf-8")
        (foo / "main.gd").write_text('var t = preload("res://segments/bar/thing.gd")\n', encoding="utf-8")
        _git_init(tmp_path)

        result = _run_check(tmp_path)
        assert result.exit_code == 1
        assert "[cross-segment]" in result.output
        assert "segments/foo/main.gd" in result.output

    def test_python_dotted_cross_segment_detected(self, tmp_path):
        body = dedent("""\
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
        _write_claude_md(tmp_path, body)
        app = tmp_path / "app/svc"
        core = tmp_path / "core/lib"
        app.mkdir(parents=True)
        core.mkdir(parents=True)
        (core / "__init__.py").write_text("", encoding="utf-8")
        (app / "main.py").write_text("from core.lib import x\n", encoding="utf-8")
        _git_init(tmp_path)

        result = _run_check(tmp_path)
        assert result.exit_code == 1
        assert "[cross-segment]" in result.output
        assert "app/svc/main.py" in result.output

    def test_boundary_no_false_match(self, tmp_path):
        # segment path `api` must not match import `apiclient`.
        body = dedent("""\
            # Project

            ## Segments

            ### api -- api
            **Language**: python
            **Constraints**: `io-boundary`

            ### web -- web
            **Language**: python
            **Constraints**: `pure-logic`

            ## Other
        """)
        _write_claude_md(tmp_path, body)
        (tmp_path / "api").mkdir(parents=True)
        web = tmp_path / "web"
        web.mkdir(parents=True)
        (web / "main.py").write_text("import apiclient\n", encoding="utf-8")
        _git_init(tmp_path)

        result = _run_check(tmp_path)
        assert result.exit_code == 0
        assert "[cross-segment]" not in result.output


class TestRelativeImports:
    def test_relative_import_no_spurious_violation(self, tmp_path):
        body = dedent("""\
            # Project

            ## Segments

            ### core -- core/lib
            **Language**: python
            **Constraints**: `pure-logic`

            ## Other
        """)
        _write_claude_md(tmp_path, body)
        core = tmp_path / "core/lib"
        core.mkdir(parents=True)
        (core / "main.py").write_text("from . import helper\n", encoding="utf-8")
        _git_init(tmp_path)

        result = _run_check(tmp_path)
        assert result.exit_code == 0
        assert "No contract violations" in result.output
