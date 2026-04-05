"""keel map — build and display the living source map."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import click

from keel_cli.imports import LANG_BY_EXT, extract_imports, file_language
from keel_cli.parser import parse, resolve_claude_md, resolve_keel_dir, segment_for_file


@click.command("map")
@click.option("--rebuild", is_flag=True, help="Rebuild the source map from current project state.")
@click.option("--json-output", "json_out", is_flag=True, help="Output raw JSON.")
@click.pass_context
def map_cmd(ctx, rebuild, json_out):
    """Build and display the project source map."""
    project = ctx.obj["project"]
    keel_dir = resolve_keel_dir(project)
    map_path = keel_dir / "map.json"

    if rebuild or not map_path.exists():
        source_map = _build_map(project)
        map_path.parent.mkdir(parents=True, exist_ok=True)
        map_path.write_text(json.dumps(source_map, indent=2) + "\n", encoding="utf-8")
        click.echo("Source map written to .keel/map.json")
    else:
        source_map = json.loads(map_path.read_text(encoding="utf-8"))

    if json_out:
        click.echo(json.dumps(source_map, indent=2))
        return

    # Formatted output
    totals = source_map.get("totals", {})
    click.echo(f"\n  Project: {source_map.get('project', '?')}")
    click.echo(f"  Generated: {source_map.get('generated', '?')}\n")

    click.echo(f"  {'Segment':<20} {'Path':<25} {'Lang':<12} {'Constraints':<30} {'Files':>5} {'Tests':>5}")
    click.echo(f"  {'─' * 20} {'─' * 25} {'─' * 12} {'─' * 30} {'─' * 5} {'─' * 5}")

    for name, seg in source_map.get("segments", {}).items():
        constraints = ", ".join(seg.get("constraints", []))
        files = seg["file_count"]
        tests = seg["test_count"]
        click.echo(f"  {name:<20} {seg['path']:<25} {seg['language']:<12} {constraints:<30} {files:>5} {tests:>5}")

    edges = source_map.get("dependency_graph", {}).get("edges", [])
    if edges:
        click.echo("\n  Dependencies:")
        for e in edges:
            click.echo(f"    {e['from']} → {e['to']} ({e['weight']} imports)")

    orphans = source_map.get("orphan_files", [])
    if orphans:
        click.echo(f"\n  Orphan files ({len(orphans)}):")
        for f in orphans[:10]:
            click.echo(f"    {f}")
        if len(orphans) > 10:
            click.echo(f"    ... and {len(orphans) - 10} more")

    click.echo(
        f"\n  Totals: {totals.get('segments', 0)} segments, "
        f"{totals.get('source_files', 0)} source, "
        f"{totals.get('test_files', 0)} tests, "
        f"{totals.get('cross_segment_edges', 0)} edges, "
        f"{totals.get('orphan_files', 0)} orphans\n"
    )


def _build_map(project: str) -> dict:
    claude_md = resolve_claude_md(project)
    if not claude_md.exists():
        click.echo("keel: CLAUDE.md not found.", err=True)
        sys.exit(1)

    contracts = parse(claude_md)
    project_root = Path(project).resolve()

    segments: dict[str, dict] = {}
    edges: list[dict] = []
    orphan_files: list[str] = []

    for seg in contracts.segments:
        segments[seg.name] = {
            "path": seg.path,
            "language": seg.language,
            "constraints": list(seg.constraints),
            "files": [],
            "file_count": 0,
            "test_count": 0,
        }

    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )

    for file_path in result.stdout.strip().splitlines():
        if not file_path or Path(file_path).suffix.lower() not in LANG_BY_EXT:
            continue

        seg = segment_for_file(contracts, file_path)
        if not seg:
            orphan_files.append(file_path)
            continue

        full_path = project_root / file_path
        if not full_path.exists():
            continue

        lang = file_language(file_path)
        content = full_path.read_text(encoding="utf-8", errors="replace")
        imports = extract_imports(content, lang) if lang else []
        stem = Path(file_path).stem
        kind = "test" if (stem.startswith("test_") or stem.endswith("_test") or stem.endswith(".test")) else "source"

        seg_data = segments.get(seg.name)
        if seg_data:
            seg_data["files"].append({"path": file_path, "kind": kind})
            if kind == "test":
                seg_data["test_count"] += 1
            else:
                seg_data["file_count"] += 1

        for imp in imports:
            for other in contracts.segments:
                if other.name == seg.name:
                    continue
                if imp.startswith(other.path):
                    edges.append({"from": seg.name, "to": other.name})

    # Deduplicate edges
    seen: set[tuple[str, str]] = set()
    segment_edges = []
    for e in edges:
        key = (e["from"], e["to"])
        if key not in seen:
            seen.add(key)
            weight = sum(1 for x in edges if x["from"] == key[0] and x["to"] == key[1])
            segment_edges.append({"from": key[0], "to": key[1], "weight": weight})

    return {
        "version": 1,
        "generated": datetime.now(timezone.utc).isoformat(),
        "project": project_root.name,
        "segments": segments,
        "dependency_graph": {"edges": segment_edges},
        "orphan_files": orphan_files,
        "totals": {
            "segments": len(segments),
            "source_files": sum(s["file_count"] for s in segments.values()),
            "test_files": sum(s["test_count"] for s in segments.values()),
            "cross_segment_edges": len(segment_edges),
            "orphan_files": len(orphan_files),
        },
    }
