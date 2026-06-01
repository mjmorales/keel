"""keel decide — record an architectural decision."""

from __future__ import annotations

import json
import re
import sys
from datetime import date

import click

from keel_cli.ledger import load_ledger, next_id
from keel_cli.parser import resolve_keel_dir

VALID_TYPES = ("friction", "amendment", "vocabulary", "pattern", "segment", "inception")


@click.command()
@click.argument("dtype", metavar="TYPE")
@click.argument("summary")
@click.option("--supersedes", help="ID of the decision this supersedes.")
@click.pass_context
def decide(ctx, dtype, summary, supersedes):
    """Record an architectural decision.

    TYPE: friction | amendment | vocabulary | pattern | segment
    """
    project = ctx.obj["project"]
    keel_dir = resolve_keel_dir(project)

    if dtype not in VALID_TYPES:
        click.echo(
            f"Invalid type '{dtype}'. Must be one of: {', '.join(VALID_TYPES)}",
            err=True,
        )
        sys.exit(1)

    ledger_path = keel_dir / "ledger.json"
    decisions_dir = keel_dir / "decisions"

    ledger = load_ledger(keel_dir)

    slug = re.sub(r"[^a-z0-9-]", "", summary.lower().replace(" ", "-"))[:40]
    decision_id = next_id(ledger, slug)

    # Never clobber a hand-edited detail file: a reset id (e.g. ledger lost its
    # numeric ids) must not overwrite an existing 001-*.json on disk.
    decision_path = decisions_dir / f"{decision_id}.json"
    if decision_path.exists():
        click.echo(
            f"keel: Decision file already exists: {decision_path}. Refusing to overwrite.",
            err=True,
        )
        sys.exit(1)

    entry = {
        "id": decision_id,
        "type": dtype,
        "date": date.today().isoformat(),
        "summary": summary,
        "approved_by": "human",
        "supersedes": supersedes,
    }

    # Write to ledger
    ledger.append(entry)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")

    # Write full decision file
    decisions_dir.mkdir(parents=True, exist_ok=True)
    full_record = {**entry, "details": {}}
    decision_path.write_text(json.dumps(full_record, indent=2) + "\n", encoding="utf-8")

    click.echo(f"Recorded: {decision_id}")
    click.echo(f"Detail file: .keel/decisions/{decision_id}.json")
    click.echo("Edit the detail file to add context (task, conflict, resolution, affected segments).")
