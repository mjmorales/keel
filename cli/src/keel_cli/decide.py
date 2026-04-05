"""keel decide — record an architectural decision."""

from __future__ import annotations

import json
import re
import sys
from datetime import date

import click

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

    # Load or create ledger
    if ledger_path.exists():
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    else:
        ledger = []

    # Generate next ID
    if not ledger:
        next_num = 1
    else:
        nums = [int(e["id"].split("-")[0]) for e in ledger if e["id"][0].isdigit()]
        next_num = max(nums) + 1 if nums else 1

    slug = re.sub(r"[^a-z0-9-]", "", summary.lower().replace(" ", "-"))[:40]
    decision_id = f"{next_num:03d}-{slug}"

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
    decision_path = decisions_dir / f"{decision_id}.json"
    full_record = {**entry, "details": {}}
    decision_path.write_text(json.dumps(full_record, indent=2) + "\n", encoding="utf-8")

    click.echo(f"Recorded: {decision_id}")
    click.echo(f"Detail file: .keel/decisions/{decision_id}.json")
    click.echo("Edit the detail file to add context (task, conflict, resolution, affected segments).")
