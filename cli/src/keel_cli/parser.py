"""Parse a project CLAUDE.md into structured data.

Reads the Keel-generated CLAUDE.md format and extracts segments,
constraints, import rules, and vocabulary.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Segment:
    name: str
    path: str
    language: str
    constraints: tuple[str, ...]


@dataclass(frozen=True)
class ForbiddenImport:
    segment: str
    must_not_import: str
    reason: str


@dataclass(frozen=True)
class ProjectContracts:
    segments: tuple[Segment, ...]
    forbidden_imports: tuple[ForbiddenImport, ...]
    vocabulary: tuple[str, ...]


def parse(claude_md_path: Path) -> ProjectContracts:
    """Parse a CLAUDE.md file and return structured contract data."""
    text = claude_md_path.read_text(encoding="utf-8")
    return ProjectContracts(
        segments=_parse_segments(text),
        forbidden_imports=_parse_forbidden_imports(text),
        vocabulary=_parse_vocabulary(text),
    )


def segment_for_file(contracts: ProjectContracts, file_path: str) -> Segment | None:
    """Determine which segment a file belongs to by its path."""
    for seg in sorted(contracts.segments, key=lambda s: len(s.path), reverse=True):
        if file_path.startswith(seg.path):
            return seg
    return None


def resolve_keel_dir(project: str) -> Path:
    """Resolve the .keel directory from a project root."""
    return Path(project).resolve() / ".keel"


def resolve_claude_md(project: str) -> Path:
    """Resolve the CLAUDE.md path from a project root."""
    return resolve_keel_dir(project) / "CLAUDE.md"


def _parse_segments(text: str) -> tuple[Segment, ...]:
    segments = []
    for match in re.finditer(r"^### (.+?) -- (.+?)$", text, re.MULTILINE):
        name = match.group(1).strip()
        path = match.group(2).strip()
        start = match.end()
        next_heading = re.search(r"^##[# ]", text[start:], re.MULTILINE)
        block = text[start : start + next_heading.start()] if next_heading else text[start:]

        lang_match = re.search(r"\*\*Language\*\*:\s*(.+?)$", block, re.MULTILINE)
        language = lang_match.group(1).strip() if lang_match else ""

        cons_match = re.search(r"\*\*Constraints\*\*:\s*(.+?)$", block, re.MULTILINE)
        constraints = tuple(c.strip().strip("`") for c in cons_match.group(1).split(",")) if cons_match else ()

        segments.append(Segment(name=name, path=path, language=language, constraints=constraints))
    return tuple(segments)


def _parse_forbidden_imports(text: str) -> tuple[ForbiddenImport, ...]:
    results = []
    in_table = False
    for line in text.splitlines():
        if "Must Not Import" in line and "Segment" in line:
            in_table = True
            continue
        if in_table and line.startswith("|"):
            if set(line.strip()) <= {"|", "-", " "}:
                continue
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) >= 3:
                results.append(
                    ForbiddenImport(
                        segment=cells[0],
                        must_not_import=cells[1],
                        reason=cells[2],
                    )
                )
        elif in_table and not line.startswith("|"):
            in_table = False
    return tuple(results)


def _parse_vocabulary(text: str) -> tuple[str, ...]:
    results = []
    in_table = False
    for line in text.splitlines():
        if "| Term" in line and "Kind" in line and "Owner" in line:
            in_table = True
            continue
        if in_table and line.startswith("|"):
            if set(line.strip()) <= {"|", "-", " "}:
                continue
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if cells:
                results.append(cells[0])
        elif in_table and not line.startswith("|"):
            in_table = False
    return tuple(results)
