"""Unit tests for keel_cli.files classification and source iteration."""

import subprocess

from keel_cli.files import classify_kind, iter_source_files


class TestClassifyKind:
    def test_test_prefix(self):
        assert classify_kind("pkg/test_thing.py") == "test"

    def test_test_suffix(self):
        assert classify_kind("pkg/thing_test.go") == "test"

    def test_dot_test_infix(self):
        assert classify_kind("src/thing.test.ts") == "test"

    def test_dot_spec_infix(self):
        assert classify_kind("src/thing.spec.ts") == "test"

    def test_tests_dir(self):
        assert classify_kind("pkg/tests/thing.py") == "test"

    def test_double_underscore_tests_dir(self):
        assert classify_kind("src/__tests__/thing.ts") == "test"

    def test_plain_source(self):
        assert classify_kind("pkg/thing.py") == "source"

    def test_tests_substring_in_filename_is_not_a_dir(self):
        # `tests` only counts as a directory segment, not a filename fragment.
        assert classify_kind("pkg/contests.py") == "source"


class TestIterSourceFiles:
    def test_skips_test_files(self, tmp_path):
        (tmp_path / "thing.py").write_text("x = 1\n", encoding="utf-8")
        (tmp_path / "test_thing.py").write_text("x = 1\n", encoding="utf-8")
        (tmp_path / "notes.md").write_text("hi\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)

        yielded = list(iter_source_files(tmp_path, mode="tracked"))
        paths = [p for p, _, _ in yielded]
        assert paths == ["thing.py"]
        assert yielded[0][1] == "python"
        assert yielded[0][2] == "x = 1\n"

    def test_explicit_file_list_overrides_mode(self, tmp_path):
        (tmp_path / "a.py").write_text("a = 1\n", encoding="utf-8")
        (tmp_path / "b.py").write_text("b = 1\n", encoding="utf-8")

        paths = [p for p, _, _ in iter_source_files(tmp_path, files=["a.py"])]
        assert paths == ["a.py"]

    def test_skips_missing_and_unknown_language(self, tmp_path):
        (tmp_path / "a.py").write_text("a = 1\n", encoding="utf-8")
        paths = [p for p, _, _ in iter_source_files(tmp_path, files=["a.py", "gone.py", "readme.md"])]
        assert paths == ["a.py"]
