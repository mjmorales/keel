"""keel check — pre-commit contract checker."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import click

from keel_cli.files import iter_source_files
from keel_cli.imports import extract_imports, import_targets
from keel_cli.io_blocklist import is_io_import
from keel_cli.parser import ProjectContracts, require_contracts, segment_for_file


@click.command()
@click.option("--staged", is_flag=True, default=False, help="Check only git staged files.")
@click.pass_context
def check(ctx, staged):
    """Check files against architectural contracts."""
    project = ctx.obj["project"]
    contracts = require_contracts(project)
    if not contracts.segments:
        click.echo("keel: No segments in CLAUDE.md.", err=True)
        sys.exit(1)

    project_root = Path(project).resolve()
    files = _list_files(project_root, staged=staged)
    violations = collect_violations(contracts, project_root, files)

    if violations:
        click.echo(f"\nkeel: {len(violations)} contract violation(s):\n")
        for v in violations:
            click.echo(v)
        click.echo("\nFix violations or file an ADR (FRAMEWORK.md Section 6).\n")
        sys.exit(1)
    else:
        click.echo("keel: No contract violations found.")


def _list_files(project_root: Path, *, staged: bool) -> list[str]:
    """List candidate files: staged additions/modifications or all tracked."""
    if staged:
        cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"]
    else:
        cmd = ["git", "ls-files"]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
    return [f for f in result.stdout.strip().splitlines() if f]


def collect_violations(contracts: ProjectContracts, project_root: Path, files: list[str]) -> list[str]:
    """Return contract-violation messages for ``files`` (pure; no I/O to stdout).

    Shared by ``check`` (which renders + exits on the result) and ``status``
    (which prints only a one-line summary). Test files are skipped.
    """
    violations: list[str] = []
    schema_paths = {s.path for s in contracts.segments if "schema-owning" in s.constraints}

    for file_path, lang, content in iter_source_files(project_root, files=files):
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
                    if import_targets(target, imp):
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
                if import_targets(other.path, imp):
                    violations.append(f"  [cross-segment] {file_path}: imports '{imp}' from '{other.name}'")

    return violations
