"""keel audit — static drift analysis."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import click

from keel_cli.parser import parse, segment_for_file, resolve_claude_md
from keel_cli.imports import file_language


@click.command()
@click.pass_context
def audit(ctx):
    """Run static drift analysis on recent changes."""
    project = ctx.obj["project"]
    project_root = Path(project).resolve()
    claude_md = resolve_claude_md(project)

    if not claude_md.exists():
        click.echo("keel: CLAUDE.md not found.", err=True)
        sys.exit(1)

    contracts = parse(claude_md)
    vocabulary = {v.lower() for v in contracts.vocabulary}

    # Get recently changed files
    files = set()
    # Check if HEAD~1 exists before diffing against it
    has_parent = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD~1"],
        capture_output=True, cwd=project_root,
    ).returncode == 0
    diff_cmds = [["git", "diff", "--name-only"]]
    if has_parent:
        diff_cmds.insert(0, ["git", "diff", "--name-only", "HEAD~1..HEAD"])
    for cmd in diff_cmds:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
        files.update(f for f in result.stdout.strip().splitlines() if f)

    if not files:
        click.echo("keel audit: No changed files.")
        return

    # Hot files (changed >10 times in 30 days)
    result = subprocess.run(
        ["git", "log", "--name-only", "--pretty=format:", "--since=30 days ago"],
        capture_output=True, text=True, cwd=project_root,
    )
    counts: dict[str, int] = {}
    for line in result.stdout.strip().splitlines():
        if line.strip():
            counts[line.strip()] = counts.get(line.strip(), 0) + 1
    hot_files = {f for f, c in counts.items() if c >= 10}

    findings = []

    for file_path in sorted(files):
        lang = file_language(file_path)
        if not lang:
            continue

        full_path = project_root / file_path
        if not full_path.exists():
            continue

        content = full_path.read_text(encoding="utf-8", errors="replace")

        # Boolean params
        bool_patterns = {
            "go": r"func\s+\w+\(.*\bbool\b",
            "python": r"def\s+\w+\(.*:\s*bool",
            "typescript": r"(?:function|\w+)\s*\(.*:\s*boolean",
            "rust": r"fn\s+\w+\(.*:\s*bool",
        }
        pattern = bool_patterns.get(lang)
        if pattern:
            for i, line in enumerate(content.splitlines(), 1):
                if re.search(pattern, line):
                    findings.append(f"  [boolean-param] {file_path}:{i}: bool parameter — consider Strategy")

        # Switch sprawl (>4 cases)
        if lang == "go":
            for m in re.finditer(r"switch\s", content):
                block = content[m.start():m.start() + 2000]
                if block.count("case ") > 4:
                    line = content[:m.start()].count("\n") + 1
                    findings.append(f"  [switch-sprawl] {file_path}:{line}: switch with many cases — use Registry")
        elif lang in ("python", "rust"):
            for m in re.finditer(r"match\s+\w+", content):
                block = content[m.start():m.start() + 2000]
                arms = len(re.findall(r"^\s*(?:case\s|.*=>)", block, re.MULTILINE))
                if arms > 4:
                    line = content[:m.start()].count("\n") + 1
                    findings.append(f"  [switch-sprawl] {file_path}:{line}: match with {arms}+ arms — use Strategy")

        # Naming drift
        if vocabulary:
            for m in re.finditer(r"(?:type|struct|class|interface|enum|func|fn|def|const|var)\s+([A-Z]\w+)", content):
                name = m.group(1)
                words = re.findall(r"[A-Z][a-z]+|[a-z]+", name)
                if len(words) > 1 and not any(w.lower() in vocabulary for w in words):
                    line = content[:m.start()].count("\n") + 1
                    findings.append(f"  [naming-drift] {file_path}:{line}: '{name}' has no vocabulary match")

        # Hot file
        if file_path in hot_files:
            findings.append(f"  [hot-file] {file_path}: changed frequently — scrutinize for responsibility creep")

    if findings:
        click.echo(f"\nkeel audit: {len(findings)} finding(s):\n")
        for f in findings:
            click.echo(f)
        click.echo("\nSoft findings. Review and address as appropriate.\n")
    else:
        click.echo("keel audit: No drift detected.")
