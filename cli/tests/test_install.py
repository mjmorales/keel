"""Tests for keel install-skill — transactional, directory-aware copy."""

from click.testing import CliRunner

from keel_cli.main import cli


def _make_source(root, manifest_entries, files):
    """Create a fake skill repo with a skill.manifest and the given files.

    manifest_entries: lines written to skill.manifest.
    files: mapping of relative path -> content for files to actually create.
            A relative path ending in "/" creates a directory with one child.
    """
    for rel, content in files.items():
        if rel.endswith("/"):
            d = root / rel
            d.mkdir(parents=True, exist_ok=True)
            (d / "child.txt").write_text(content)
        else:
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
    (root / "skill.manifest").write_text("\n".join(manifest_entries) + "\n")


def test_count_reflects_copied_not_manifest(tmp_path):
    src = tmp_path / "repo"
    src.mkdir()
    # Manifest lists two entries but only one exists on disk.
    _make_source(src, ["present.txt", "absent.txt"], {"present.txt": "x"})
    dest = tmp_path / "dest"

    result = CliRunner().invoke(cli, ["install-skill", str(src), "--dest", str(dest)])
    assert result.exit_code == 0, result.output
    assert "Installed 1 files" in result.output
    assert "skip (missing): absent.txt" in result.output
    assert (dest / "present.txt").read_text() == "x"


def test_directory_manifest_entry_copied(tmp_path):
    src = tmp_path / "repo"
    src.mkdir()
    _make_source(src, ["assets/"], {"assets/": "data"})
    dest = tmp_path / "dest"

    result = CliRunner().invoke(cli, ["install-skill", str(src), "--dest", str(dest)])
    assert result.exit_code == 0, result.output
    assert "Installed 1 files" in result.output
    assert (dest / "assets" / "child.txt").read_text() == "data"


def test_overwrite_populated_dest_requires_confirm(tmp_path):
    src = tmp_path / "repo"
    src.mkdir()
    _make_source(src, ["a.txt"], {"a.txt": "new"})
    dest = tmp_path / "dest"
    dest.mkdir()
    (dest / "old.txt").write_text("old")

    # Decline the confirmation prompt -> dest untouched.
    result = CliRunner().invoke(cli, ["install-skill", str(src), "--dest", str(dest)], input="n\n")
    assert result.exit_code == 0
    assert "Aborted." in result.output
    assert (dest / "old.txt").exists()
    assert not (dest / "a.txt").exists()


def test_link_confirms_before_removing_real_dir(tmp_path):
    src = tmp_path / "repo"
    src.mkdir()
    _make_source(src, ["a.txt"], {"a.txt": "x"})
    dest = tmp_path / "dest"
    dest.mkdir()
    (dest / "old.txt").write_text("old")

    result = CliRunner().invoke(cli, ["install-skill", str(src), "--dest", str(dest), "--link"], input="n\n")
    assert result.exit_code == 0
    assert "Aborted." in result.output
    assert (dest / "old.txt").exists()
