"""keel status — contract compliance overview."""

from __future__ import annotations

import json
import sys

import click

from keel_cli.parser import parse, resolve_claude_md, resolve_keel_dir


@click.command()
@click.pass_context
def status(ctx):
    """Show contract compliance overview."""
    project = ctx.obj["project"]
    keel_dir = resolve_keel_dir(project)
    claude_md = resolve_claude_md(project)

    if not claude_md.exists():
        click.echo("keel: Not a keel-governed project (no .keel/CLAUDE.md).", err=True)
        sys.exit(1)

    contracts = parse(claude_md)

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
    ledger_path = keel_dir / "ledger.json"
    if ledger_path.exists():
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
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

    # Quick violation check (inline, no subprocess)
    click.echo("\n  Running contract check...")
    from keel_cli.check import check

    try:
        ctx.invoke(check)
        click.echo("  Contracts: CLEAN")
    except SystemExit as e:
        if e.code:
            click.echo("  Contracts: VIOLATIONS FOUND (see output above)")
        else:
            click.echo("  Contracts: CLEAN")

    click.echo()
