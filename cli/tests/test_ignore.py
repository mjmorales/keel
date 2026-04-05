"""Unit tests for keel_cli.ignore module."""

from textwrap import dedent

from keel_cli.ignore import (
    IgnoreEntry,
    InlineSuppression,
    is_suppressed,
    parse_keelignore,
    scan_inline_suppressions,
)


class TestParseKeelignore:
    def test_valid_entries(self, tmp_path):
        keelignore = tmp_path / ".keelignore"
        keelignore.write_text(
            dedent("""\
            boolean-param  ^payments/.*\\.py$  -- legacy adapter
            switch-sprawl  ^cli/dispatch  -- inherently branchy
        """)
        )
        entries = parse_keelignore(keelignore)
        assert len(entries) == 2
        assert entries[0].rule_pattern == "boolean-param"
        assert entries[0].path_pattern == r"^payments/.*\.py$"
        assert entries[0].reason == "legacy adapter"
        assert entries[0].line_number == 1
        assert entries[1].rule_pattern == "switch-sprawl"
        assert entries[1].line_number == 2

    def test_comments_and_blanks(self, tmp_path):
        keelignore = tmp_path / ".keelignore"
        keelignore.write_text(
            dedent("""\
            # This is a comment

            boolean-param  ^src/  -- valid entry
            # Another comment
        """)
        )
        entries = parse_keelignore(keelignore)
        assert len(entries) == 1
        assert entries[0].rule_pattern == "boolean-param"
        assert entries[0].line_number == 3

    def test_missing_reason_skipped(self, tmp_path, capsys):
        keelignore = tmp_path / ".keelignore"
        keelignore.write_text("boolean-param ^src/\n")
        entries = parse_keelignore(keelignore)
        assert len(entries) == 0
        captured = capsys.readouterr()
        assert "missing reason" in captured.err

    def test_empty_reason_skipped(self, tmp_path, capsys):
        keelignore = tmp_path / ".keelignore"
        keelignore.write_text("boolean-param ^src/ --\n")
        entries = parse_keelignore(keelignore)
        assert len(entries) == 0
        captured = capsys.readouterr()
        assert "empty reason" in captured.err

    def test_missing_path_skipped(self, tmp_path, capsys):
        keelignore = tmp_path / ".keelignore"
        keelignore.write_text("boolean-param -- no path here\n")
        entries = parse_keelignore(keelignore)
        assert len(entries) == 0
        captured = capsys.readouterr()
        assert "need" in captured.err

    def test_nonexistent_file(self, tmp_path):
        entries = parse_keelignore(tmp_path / "missing")
        assert entries == []


class TestScanInlineSuppressions:
    def test_python_hash_comment(self):
        content = "def create(urgent: bool):  # keel:ignore boolean-param -- tracked in PROJ-1\n"
        sups = scan_inline_suppressions("app.py", content)
        assert len(sups) == 1
        assert sups[0].rule == "boolean-param"
        assert sups[0].reason == "tracked in PROJ-1"
        assert sups[0].file_path == "app.py"
        assert sups[0].line_number == 1

    def test_go_slash_comment(self):
        content = "func Do(flag bool) { // keel:ignore boolean-param -- legacy API\n"
        sups = scan_inline_suppressions("main.go", content)
        assert len(sups) == 1
        assert sups[0].rule == "boolean-param"

    def test_preceding_line(self):
        content = dedent("""\
            # keel:ignore boolean-param -- will refactor
            def create(urgent: bool):
        """)
        sups = scan_inline_suppressions("app.py", content)
        assert len(sups) == 1
        assert sups[0].line_number == 1

    def test_missing_reason_skipped(self):
        content = "def create(urgent: bool):  # keel:ignore boolean-param\n"
        sups = scan_inline_suppressions("app.py", content)
        assert len(sups) == 0

    def test_sql_double_dash_comment(self):
        content = "-- keel:ignore naming-drift -- generated column\n"
        sups = scan_inline_suppressions("schema.sql", content)
        assert len(sups) == 1
        assert sups[0].rule == "naming-drift"

    def test_no_directives(self):
        content = "def create(name: str):\n    pass\n"
        sups = scan_inline_suppressions("app.py", content)
        assert len(sups) == 0


class TestIsSuppressed:
    def test_suppressed_by_keelignore(self):
        entries = [IgnoreEntry("boolean-param", r"^payments/", "legacy", 1)]
        suppressed, source = is_suppressed("boolean-param", "payments/api.py", 10, entries, [])
        assert suppressed is True
        assert source == ".keelignore:1"

    def test_suppressed_by_keelignore_regex(self):
        entries = [IgnoreEntry("boolean.*", r".*\.py$", "all booleans in python", 5)]
        suppressed, source = is_suppressed("boolean-param", "src/app.py", 3, entries, [])
        assert suppressed is True

    def test_suppressed_by_inline_same_line(self):
        inline = [InlineSuppression("boolean-param", "tracked", "app.py", 10)]
        suppressed, source = is_suppressed("boolean-param", "app.py", 10, [], inline)
        assert suppressed is True
        assert source == "inline:app.py:10"

    def test_suppressed_by_inline_preceding_line(self):
        inline = [InlineSuppression("boolean-param", "tracked", "app.py", 9)]
        suppressed, source = is_suppressed("boolean-param", "app.py", 10, [], inline)
        assert suppressed is True
        assert source == "inline:app.py:9"

    def test_not_suppressed_wrong_rule(self):
        entries = [IgnoreEntry("switch-sprawl", r".*", "reason", 1)]
        suppressed, source = is_suppressed("boolean-param", "app.py", 10, entries, [])
        assert suppressed is False
        assert source is None

    def test_not_suppressed_wrong_path(self):
        entries = [IgnoreEntry("boolean-param", r"^payments/", "reason", 1)]
        suppressed, source = is_suppressed("boolean-param", "src/app.py", 10, entries, [])
        assert suppressed is False

    def test_not_suppressed_inline_wrong_line(self):
        inline = [InlineSuppression("boolean-param", "tracked", "app.py", 5)]
        suppressed, source = is_suppressed("boolean-param", "app.py", 10, [], inline)
        assert suppressed is False

    def test_hot_file_no_line(self):
        entries = [IgnoreEntry("hot-file", r"^data/", "expected churn", 1)]
        suppressed, source = is_suppressed("hot-file", "data/cache.py", None, entries, [])
        assert suppressed is True

    def test_keelignore_checked_before_inline(self):
        entries = [IgnoreEntry("boolean-param", r".*", "config", 3)]
        inline = [InlineSuppression("boolean-param", "inline reason", "app.py", 10)]
        suppressed, source = is_suppressed("boolean-param", "app.py", 10, entries, inline)
        assert suppressed is True
        assert source == ".keelignore:3"
