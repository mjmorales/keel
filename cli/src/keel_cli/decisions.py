"""keel decisions — view the decision ledger."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from keel_cli.parser import resolve_keel_dir


@click.command()
@click.option(
    "--type",
    "dtype",
    help="Filter by type (friction, amendment, vocabulary, pattern, segment).",
)
@click.option("--since", help="Filter by date (YYYY-MM-DD).")
@click.option("--detail", help="Show full details for a specific decision ID.")
@click.pass_context
def decisions(ctx, dtype, since, detail):
    """View the architectural decision ledger."""
    project = ctx.obj["project"]
    keel_dir = resolve_keel_dir(project)
    ledger_path = keel_dir / "ledger.json"

    if not ledger_path.exists():
        click.echo("keel: No decision ledger found.", err=True)
        sys.exit(1)

    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))

    if detail:
        _show_detail(keel_dir, detail)
        return

    entries = ledger
    if dtype:
        entries = [e for e in entries if e.get("type") == dtype]
    if since:
        entries = [e for e in entries if e.get("date", "") >= since]

    if not entries:
        click.echo("keel: No matching decisions.")
        return

    click.echo(f"\n  Decision Ledger ({len(entries)} entries):\n")

    for entry in reversed(entries):
        click.echo(f"  [{entry['id']}] {entry['date']} ({entry['type']})")
        click.echo(f"    {entry['summary']}")
        if entry.get("supersedes"):
            click.echo(f"    supersedes: {entry['supersedes']}")
        click.echo()

    # Totals by type
    type_counts: dict[str, int] = {}
    for e in ledger:
        t = e.get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
    parts = [f"{c} {t}" for t, c in sorted(type_counts.items())]
    click.echo(f"  Total: {len(ledger)} decisions ({', '.join(parts)})")
    click.echo()


def _show_detail(keel_dir: Path, decision_id: str):
    decisions_dir = keel_dir / "decisions"

    # Try exact match first, then prefix match
    candidates = list(decisions_dir.glob(f"{decision_id}*.json"))
    if not candidates:
        click.echo(f"keel: Decision '{decision_id}' not found.", err=True)
        return

    decision = json.loads(candidates[0].read_text(encoding="utf-8"))
    click.echo(f"\n  Decision: {decision['id']}")
    click.echo(f"  Type: {decision['type']}")
    click.echo(f"  Date: {decision['date']}")
    click.echo(f"  Summary: {decision['summary']}")
    click.echo(f"  Approved by: {decision.get('approved_by', '?')}")

    if decision.get("supersedes"):
        click.echo(f"  Supersedes: {decision['supersedes']}")

    details = decision.get("details", {})
    if details:
        click.echo("\n  Details:")
        for key, value in details.items():
            if isinstance(value, list):
                click.echo(f"    {key}:")
                for item in value:
                    click.echo(f"      - {item}")
            else:
                click.echo(f"    {key}: {value}")

    click.echo()
