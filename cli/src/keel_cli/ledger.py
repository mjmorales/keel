"""Decision-ledger access — the single reader/ID-allocator for ledger.json.

Three policies for an absent ledger coexist by design, one function each:

- ``load_ledger`` tolerates absence (returns ``[]``) for read-only callers
  that should degrade gracefully (``status``).
- ``require_ledger`` exits 1 with a canonical message for callers that need a
  ledger to exist (``decisions``).
- ``next_id`` allocates the next sequential decision id for the writer
  (``decide``).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import click

_ID_PREFIX = re.compile(r"^(\d+)-")


def load_ledger(keel_dir: Path) -> list:
    """Return the ledger entries, or ``[]`` if no ledger file exists."""
    ledger_path = keel_dir / "ledger.json"
    if not ledger_path.exists():
        return []
    return json.loads(ledger_path.read_text(encoding="utf-8"))


def require_ledger(keel_dir: Path) -> list:
    """Return the ledger entries, or exit 1 if no ledger file exists."""
    ledger_path = keel_dir / "ledger.json"
    if not ledger_path.exists():
        click.echo("keel: No decision ledger found.", err=True)
        sys.exit(1)
    return json.loads(ledger_path.read_text(encoding="utf-8"))


def next_id(ledger: list, slug: str) -> str:
    """Allocate the next ``NNN-<slug>`` decision id from the ledger.

    Parses the numeric prefix of each existing id, ignoring malformed or
    empty ids, and increments the maximum. Falls back to 1 only when no
    numeric id exists.
    """
    found = []
    for entry in ledger:
        match = _ID_PREFIX.match(entry.get("id", ""))
        if match:
            found.append(int(match.group(1)))
    next_num = max(found) + 1 if found else 1
    return f"{next_num:03d}-{slug}"
