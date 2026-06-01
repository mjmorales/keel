"""Unit tests for keel_cli.imports extraction and boundary matching."""

from keel_cli.imports import extract_imports, import_targets


class TestExtractPython:
    def test_retains_full_dotted_module(self):
        imports = extract_imports("from pkg.sub import x\n", "python")
        assert imports == ["pkg.sub"]

    def test_plain_import_retains_dotted(self):
        imports = extract_imports("import pkg.sub.mod\n", "python")
        assert imports == ["pkg.sub.mod"]

    def test_import_as_strips_alias(self):
        imports = extract_imports("import pkg.sub as p\n", "python")
        assert imports == ["pkg.sub"]

    def test_relative_from_import_skipped(self):
        imports = extract_imports("from . import x\n", "python")
        assert imports == []

    def test_relative_dotted_from_import_skipped(self):
        imports = extract_imports("from .sub import x\n", "python")
        assert imports == []

    def test_relative_plain_import_skipped(self):
        # `import .x` is not valid Python but guard against producing a token.
        imports = extract_imports("import .x\n", "python")
        assert imports == []

    def test_multiple_imports_one_line(self):
        imports = extract_imports("import os, sys.path\n", "python")
        assert imports == ["os", "sys.path"]


class TestExtractGdscript:
    def test_strips_res_scheme(self):
        imports = extract_imports('var x = preload("res://segments/foo/bar.gd")\n', "gdscript")
        assert imports == ["segments/foo/bar.gd"]

    def test_load_call(self):
        imports = extract_imports('var x = load("res://addons/godot_http/client.gd")\n', "gdscript")
        assert imports == ["addons/godot_http/client.gd"]


class TestImportTargets:
    def test_gdscript_cross_segment_path(self):
        # GDScript preload normalized to a path matches a segment path.
        assert import_targets("segments/foo", "segments/foo/bar.gd")

    def test_python_dotted_matches_slash_path(self):
        assert import_targets("pkg/sub", "pkg.sub")

    def test_python_dotted_child_matches(self):
        assert import_targets("pkg/sub", "pkg.sub.mod")

    def test_boundary_no_false_prefix_match(self):
        # `api` must not match `apiclient` (the C2 unbounded-startswith bug).
        assert not import_targets("api", "apiclient")

    def test_boundary_exact_match(self):
        assert import_targets("api", "api")

    def test_boundary_child_match(self):
        assert import_targets("api", "api/client")
        assert import_targets("api", "api.client")

    def test_rust_double_colon_separator(self):
        assert import_targets("std/fs", "std::fs")

    def test_unrelated_no_match(self):
        assert not import_targets("pkg/sub", "other/thing")
