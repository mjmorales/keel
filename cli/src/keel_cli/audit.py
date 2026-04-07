"""keel audit — static drift analysis."""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import click

from keel_cli.ignore import is_suppressed, parse_keelignore, scan_inline_suppressions
from keel_cli.imports import file_language
from keel_cli.parser import parse, resolve_claude_md


@dataclass
class Finding:
    """A single audit finding with structured metadata."""

    rule: str
    file_path: str
    line: int | None
    message: str

    def display(self) -> str:
        if self.line is not None:
            return f"  [{self.rule}] {self.file_path}:{self.line}: {self.message}"
        return f"  [{self.rule}] {self.file_path}: {self.message}"


@click.command()
@click.option(
    "--show-ignored",
    is_flag=True,
    default=False,
    help="Show suppressed findings and their suppression source.",
)
@click.pass_context
def audit(ctx, show_ignored):
    """Run static drift analysis on recent changes."""
    project = ctx.obj["project"]
    project_root = Path(project).resolve()
    claude_md = resolve_claude_md(project)

    if not claude_md.exists():
        click.echo("keel: CLAUDE.md not found.", err=True)
        sys.exit(1)

    contracts = parse(claude_md)
    vocabulary = {v.lower() for v in contracts.vocabulary}

    # Load .keelignore
    keelignore_path = project_root / ".keelignore"
    keelignore_entries = parse_keelignore(keelignore_path)

    # Get recently changed files
    files = set()
    has_parent = (
        subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD~1"],
            capture_output=True,
            cwd=project_root,
        ).returncode
        == 0
    )
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
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    counts: dict[str, int] = {}
    for line in result.stdout.strip().splitlines():
        if line.strip():
            counts[line.strip()] = counts.get(line.strip(), 0) + 1
    hot_files = {f for f, c in counts.items() if c >= 10}

    findings: list[Finding] = []
    all_inline_suppressions = []

    for file_path in sorted(files):
        lang = file_language(file_path)
        if not lang:
            continue

        full_path = project_root / file_path
        if not full_path.exists():
            continue

        content = full_path.read_text(encoding="utf-8", errors="replace")

        # Collect inline suppressions for this file.
        all_inline_suppressions.extend(scan_inline_suppressions(file_path, content))

        # Boolean params
        bool_patterns = {
            "go": r"func\s+\w+\(.*\bbool\b",
            "python": r"def\s+\w+\(.*:\s*bool",
            "typescript": r"(?:function|\w+)\s*\(.*:\s*boolean",
            "rust": r"fn\s+\w+\(.*:\s*bool",
            "gdscript": r"func\s+\w+\(.*:\s*bool",
        }
        pattern = bool_patterns.get(lang)
        if pattern:
            for i, line in enumerate(content.splitlines(), 1):
                if re.search(pattern, line):
                    findings.append(
                        Finding(
                            rule="boolean-param",
                            file_path=file_path,
                            line=i,
                            message="bool parameter \u2014 consider Strategy",
                        )
                    )

        # Switch sprawl (>4 cases)
        if lang == "go":
            for m in re.finditer(r"switch\s", content):
                block = content[m.start() : m.start() + 2000]
                if block.count("case ") > 4:
                    line_num = content[: m.start()].count("\n") + 1
                    findings.append(
                        Finding(
                            rule="switch-sprawl",
                            file_path=file_path,
                            line=line_num,
                            message="switch with many cases \u2014 use Registry",
                        )
                    )
        elif lang in ("python", "rust", "gdscript"):
            for m in re.finditer(r"match\s+\w+", content):
                block = content[m.start() : m.start() + 2000]
                arms = len(re.findall(r"^\s*(?:case\s|.*=>)", block, re.MULTILINE))
                if arms > 4:
                    line_num = content[: m.start()].count("\n") + 1
                    findings.append(
                        Finding(
                            rule="switch-sprawl",
                            file_path=file_path,
                            line=line_num,
                            message=f"match with {arms}+ arms \u2014 use Strategy",
                        )
                    )

        # Naming drift
        if vocabulary:
            for m in re.finditer(
                r"(?:type|struct|class_name|class|interface|enum|func|fn|def|const|var)\s+([A-Z]\w+)",
                content,
            ):
                name = m.group(1)
                words = re.findall(r"[A-Z][a-z]+|[a-z]+", name)
                if len(words) > 1:
                    has_match = any(w.lower() in vocabulary for w in words)
                elif len(words) == 1:
                    has_match = words[0].lower() in vocabulary
                else:
                    has_match = True
                if not has_match:
                    line_num = content[: m.start()].count("\n") + 1
                    findings.append(
                        Finding(
                            rule="naming-drift",
                            file_path=file_path,
                            line=line_num,
                            message=f"'{name}' has no vocabulary match",
                        )
                    )

        # Hot file
        if file_path in hot_files:
            findings.append(
                Finding(
                    rule="hot-file",
                    file_path=file_path,
                    line=None,
                    message="changed frequently \u2014 scrutinize for responsibility creep",
                )
            )

    # Partition findings into active and suppressed.
    active: list[Finding] = []
    suppressed: list[tuple[Finding, str]] = []
    matched_keelignore_lines: set[int] = set()

    for finding in findings:
        is_sup, source = is_suppressed(
            finding.rule,
            finding.file_path,
            finding.line,
            keelignore_entries,
            all_inline_suppressions,
        )
        if is_sup:
            suppressed.append((finding, source))
            # Track which .keelignore entries matched.
            if source and source.startswith(".keelignore:"):
                matched_keelignore_lines.add(int(source.split(":")[1]))
        else:
            active.append(finding)

    # Detect stale .keelignore entries.
    stale_entries = [e for e in keelignore_entries if e.line_number not in matched_keelignore_lines]

    # Output.
    if active:
        click.echo(f"\nkeel audit: {len(active)} finding(s):\n")
        for f in active:
            click.echo(f.display())

    if show_ignored and suppressed:
        click.echo(f"\nSuppressed ({len(suppressed)}):\n")
        for finding, source in suppressed:
            click.echo(f"{finding.display()}  [suppressed by {source}]")

    if stale_entries:
        click.echo(f"\nkeel audit: {len(stale_entries)} stale .keelignore entry(ies):")
        for entry in stale_entries:
            click.echo(
                f"  .keelignore:{entry.line_number}: {entry.rule_pattern} {entry.path_pattern} -- matched no findings"
            )

    if active:
        if suppressed:
            click.echo(f"\n{len(suppressed)} finding(s) suppressed.")
        click.echo("\nSoft findings. Review and address as appropriate.\n")
    elif suppressed:
        click.echo(f"\nkeel audit: No active findings. {len(suppressed)} finding(s) suppressed.")
    else:
        click.echo("keel audit: No drift detected.")
