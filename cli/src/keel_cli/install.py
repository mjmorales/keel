"""keel install-skill — install the inception skill from a keel repo."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import click


SKILL_NAME = "project-inception"
DEFAULT_DEST = Path.home() / ".claude" / "skills" / SKILL_NAME


@click.command("install-skill")
@click.argument("source", default=".", type=click.Path(exists=True))
@click.option("--dest", default=str(DEFAULT_DEST), help="Installation directory.")
@click.option("--link", is_flag=True, help="Symlink instead of copy (dev mode).")
def install_skill(source, dest, link):
    """Install the keel inception skill into Claude Code.

    SOURCE is the path to the keel repo (defaults to current directory).
    """
    source_path = Path(source).resolve()
    dest_path = Path(dest)
    manifest_path = source_path / "skill.manifest"

    if not manifest_path.exists():
        click.echo(f"keel: skill.manifest not found in {source_path}", err=True)
        sys.exit(1)

    if link:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        if dest_path.is_symlink():
            dest_path.unlink()
        elif dest_path.exists():
            shutil.rmtree(dest_path)
        dest_path.symlink_to(source_path)
        click.echo(f"Linked {source_path} → {dest_path}")
        return

    files = [f.strip() for f in manifest_path.read_text().splitlines() if f.strip()]

    for file_rel in files:
        src = source_path / file_rel
        dst = dest_path / file_rel

        if not src.exists():
            click.echo(f"  skip (missing): {file_rel}", err=True)
            continue

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    click.echo(f"Installed {len(files)} files to {dest_path}")
