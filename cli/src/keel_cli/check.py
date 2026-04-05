"""keel check — pre-commit contract checker."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import click

from keel_cli.imports import extract_imports, file_language
from keel_cli.io_blocklist import is_io_import
from keel_cli.parser import parse, resolve_claude_md, segment_for_file


@click.command()
@click.option("--staged", is_flag=True, default=False, help="Check only git staged files.")
@click.pass_context
def check(ctx, staged):
    """Check files against architectural contracts."""
    project = ctx.obj["project"]
    claude_md = resolve_claude_md(project)

    if not claude_md.exists():
        click.echo("keel: CLAUDE.md not found. Run keel inception first.", err=True)
        sys.exit(1)

    contracts = parse(claude_md)
    if not contracts.segments:
        click.echo("keel: No segments in CLAUDE.md.", err=True)
        sys.exit(1)

    project_root = Path(project).resolve()

    if staged:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        files = [f for f in result.stdout.strip().splitlines() if f]
    else:
        result = subprocess.run(
            ["git", "ls-files"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        files = [f for f in result.stdout.strip().splitlines() if f]

    violations = []
    schema_paths = {s.path for s in contracts.segments if "schema-owning" in s.constraints}

    for file_path in files:
        lang = file_language(file_path)
        if not lang:
            continue

        full_path = project_root / file_path
        if not full_path.exists():
            continue

        content = full_path.read_text(encoding="utf-8", errors="replace")
        imports = extract_imports(content, lang)
        seg = segment_for_file(contracts, file_path)
        if not seg:
            continue

        # Forbidden imports
        for fi in contracts.forbidden_imports:
            if fi.segment != seg.name:
                continue
            targets = [t.strip() for t in fi.must_not_import.split(",")]
            for imp in imports:
                for target in targets:
                    if imp == target or imp.startswith(target + "/") or imp.startswith(target + "."):
                        violations.append(f"  [forbidden-import] {file_path}: imports '{imp}' ({fi.reason})")

        # I/O in pure-logic
        if "pure-logic" in seg.constraints:
            for imp in imports:
                if is_io_import(lang, imp):
                    violations.append(f"  [io-in-pure-logic] {file_path}: imports I/O package '{imp}'")

        # Cross-segment imports
        for other in contracts.segments:
            if other.name == seg.name or other.path in schema_paths:
                continue
            for imp in imports:
                if imp.startswith(other.path) or imp.startswith(other.path.rstrip("/").replace("/", ".")):
                    violations.append(f"  [cross-segment] {file_path}: imports '{imp}' from '{other.name}'")

    if violations:
        click.echo(f"\nkeel: {len(violations)} contract violation(s):\n")
        for v in violations:
            click.echo(v)
        click.echo("\nFix violations or file an ADR (FRAMEWORK.md Section 6).\n")
        sys.exit(1)
    else:
        click.echo("keel: No contract violations found.")
