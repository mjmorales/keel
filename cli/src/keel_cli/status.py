"""keel status — contract compliance overview."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import click

from keel_cli.check import collect_violations
from keel_cli.ledger import load_ledger
from keel_cli.parser import require_contracts, resolve_keel_dir


@click.command()
@click.pass_context
def status(ctx):
    """Show contract compliance overview."""
    project = ctx.obj["project"]
    keel_dir = resolve_keel_dir(project)
    contracts = require_contracts(project)

    click.echo("\n  Keel Status")
    click.echo(f"  {'─' * 50}")

    # Segments
    click.echo(f"\n  Segments ({len(contracts.segments)}):")
    for seg in contracts.segments:
        constraints = ", ".join(seg.constraints)
        click.echo(f"    {seg.name:<20} [{constraints}] ({seg.language})")

    # Vocabulary
    click.echo(f"\n  Vocabulary: {len(contracts.vocabulary)} frozen terms")

    # Forbidden imports
    click.echo(f"  Forbidden imports: {len(contracts.forbidden_imports)} rules")

    # Decision count
    ledger = load_ledger(keel_dir)
    if ledger:
        click.echo(f"  Decisions: {len(ledger)} recorded")
    else:
        click.echo("  Decisions: no ledger found")

    # Source map freshness
    map_path = keel_dir / "map.json"
    if map_path.exists():
        source_map = json.loads(map_path.read_text(encoding="utf-8"))
        totals = source_map.get("totals", {})
        click.echo(
            f"  Source map: {totals.get('source_files', '?')} files, "
            f"{totals.get('test_files', '?')} tests, "
            f"{totals.get('orphan_files', '?')} orphans "
            f"(as of {source_map.get('generated', '?')[:10]})"
        )
    else:
        click.echo("  Source map: not built (run `keel map --rebuild`)")

    # Quick violation check (inline summary only; full report is `keel check`).
    project_root = Path(project).resolve()
    files = _tracked_files(project_root)
    violations = collect_violations(contracts, project_root, files)
    if violations:
        click.echo(f"\n  Contracts: {len(violations)} violation(s) (run `keel check`)")
    else:
        click.echo("\n  Contracts: CLEAN")

    click.echo()


def _tracked_files(project_root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    return [f for f in result.stdout.strip().splitlines() if f]
