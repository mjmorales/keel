"""keel tree — ASCII and Graphviz dependency tree."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from keel_cli.parser import resolve_keel_dir


@click.command()
@click.argument("segment", required=False)
@click.option("--dot", is_flag=True, help="Output Graphviz DOT format.")
@click.pass_context
def tree(ctx, segment, dot):
    """Display the dependency tree."""
    project = ctx.obj["project"]
    map_path = resolve_keel_dir(project) / "map.json"

    if not map_path.exists():
        click.echo("keel: map.json not found. Run `keel map --rebuild` first.", err=True)
        sys.exit(1)

    source_map = json.loads(map_path.read_text(encoding="utf-8"))
    segments = source_map.get("segments", {})
    edges = source_map.get("dependency_graph", {}).get("edges", [])

    if dot:
        _render_dot(source_map, segment)
        return

    project_name = source_map.get("project", "project")

    if segment:
        _render_subtree(segment, segments, edges)
    else:
        _render_full_tree(project_name, segments, edges)


def _render_full_tree(project_name: str, segments: dict, edges: list[dict]):
    deps = {name: [] for name in segments}
    rdeps = {name: [] for name in segments}
    for e in edges:
        deps.setdefault(e["from"], []).append(e["to"])
        rdeps.setdefault(e["to"], []).append(e["from"])

    click.echo(f"\n  {project_name}")

    names = sorted(segments.keys())
    for i, name in enumerate(names):
        seg = segments[name]
        is_last = i == len(names) - 1
        prefix = "└── " if is_last else "├── "
        child_prefix = "    " if is_last else "│   "
        constraints = ", ".join(seg.get("constraints", []))

        click.echo(f"  {prefix}{seg['path']} [{constraints}] ({seg['file_count']} files, {seg['test_count']} tests)")

        segment_deps = deps.get(name, [])
        segment_rdeps = rdeps.get(name, [])

        if segment_deps:
            click.echo(f"  {child_prefix}depends on: {', '.join(segment_deps)}")
        if segment_rdeps:
            click.echo(f"  {child_prefix}depended on by: {', '.join(segment_rdeps)}")

    click.echo()


def _render_subtree(name: str, segments: dict, edges: list[dict]):
    if name not in segments:
        click.echo(f"keel: segment '{name}' not found.", err=True)
        return

    seg = segments[name]
    outgoing = [e["to"] for e in edges if e["from"] == name]
    incoming = [e["from"] for e in edges if e["to"] == name]
    constraints = ", ".join(seg.get("constraints", []))

    click.echo(f"\n  {name} [{constraints}]")
    click.echo(f"  Path: {seg['path']}")
    click.echo(f"  Language: {seg['language']}")
    click.echo(f"  Files: {seg['file_count']} source, {seg['test_count']} tests")

    if outgoing:
        click.echo(f"  Depends on:")
        for dep in outgoing:
            weight = next((e["weight"] for e in edges if e["from"] == name and e["to"] == dep), 0)
            click.echo(f"    → {dep} ({weight} imports)")

    if incoming:
        click.echo(f"  Depended on by:")
        for dep in incoming:
            weight = next((e["weight"] for e in edges if e["from"] == dep and e["to"] == name), 0)
            click.echo(f"    ← {dep} ({weight} imports)")

    click.echo()


def _render_dot(source_map: dict, focus: str | None):
    segments = source_map.get("segments", {})
    edges = source_map.get("dependency_graph", {}).get("edges", [])

    click.echo("digraph keel {")
    click.echo('  rankdir=TB;')
    click.echo('  node [shape=box, style=rounded];')

    for name, seg in segments.items():
        constraints = ", ".join(seg.get("constraints", []))
        label = f"{name}\\n[{constraints}]\\n{seg['file_count']} files"
        color = "lightblue" if focus and name == focus else "white"
        click.echo(f'  "{name}" [label="{label}", fillcolor="{color}", style="rounded,filled"];')

    for e in edges:
        click.echo(f'  "{e["from"]}" -> "{e["to"]}" [label="{e["weight"]}"];')

    click.echo("}")
