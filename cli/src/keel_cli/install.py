"""keel install-skill — install the inception skill from a keel repo."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import click

SKILL_NAME = "project-inception"
DEFAULT_DEST = Path.home() / ".claude" / "skills" / SKILL_NAME
BUNDLED_DATA = Path(__file__).parent / "data"


@click.command("install-skill")
@click.argument("source", default=None, required=False, type=click.Path(exists=True))
@click.option("--dest", default=str(DEFAULT_DEST), help="Installation directory.")
@click.option("--link", is_flag=True, help="Symlink instead of copy (dev mode).")
def install_skill(source, dest, link):
    """Install the keel inception skill into Claude Code.

    SOURCE is the path to a keel repo. Defaults to bundled package data.
    """
    source_path = Path(source).resolve() if source else BUNDLED_DATA
    dest_path = Path(dest)
    manifest_path = source_path / "skill.manifest"

    if not manifest_path.exists():
        click.echo(f"keel: skill.manifest not found in {source_path}", err=True)
        sys.exit(1)

    if link:
        if source is None:
            click.echo("keel: --link requires an explicit SOURCE path", err=True)
            sys.exit(1)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        if dest_path.is_symlink():
            dest_path.unlink()
        elif dest_path.exists():
            if not click.confirm(f"keel: {dest_path} exists and will be removed. Continue?"):
                click.echo("Aborted.")
                return
            shutil.rmtree(dest_path)
        dest_path.symlink_to(source_path)
        click.echo(f"Linked {source_path} → {dest_path}")
        return

    files = [f.strip() for f in manifest_path.read_text().splitlines() if f.strip()]

    # Confirm before overwriting a populated real destination.
    if dest_path.exists() and not dest_path.is_symlink() and any(dest_path.iterdir()):
        if not click.confirm(f"keel: {dest_path} is not empty and will be overwritten. Continue?"):
            click.echo("Aborted.")
            return

    # Stage every entry into a temp dir adjacent to dest, then move atomically
    # onto dest only after all copies succeed — a mid-loop failure never leaves a
    # half-installed skill. (Transactional install pattern.)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".keel-install-", dir=dest_path.parent))
    try:
        copied = 0
        for file_rel in files:
            src = source_path / file_rel
            staged = staging / file_rel

            if not src.exists():
                click.echo(f"  skip (missing): {file_rel}", err=True)
                continue

            staged.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(src, staged, dirs_exist_ok=True)
            else:
                shutil.copy2(src, staged)
            copied += 1

        # Replace dest with the fully-staged tree.
        if dest_path.is_symlink() or dest_path.is_file():
            dest_path.unlink()
        elif dest_path.is_dir():
            shutil.rmtree(dest_path)
        shutil.move(str(staging), str(dest_path))
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    click.echo(f"Installed {copied} files to {dest_path}")
