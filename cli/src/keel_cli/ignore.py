"""Audit finding suppression via .keelignore and inline comments."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class IgnoreEntry:
    """A single .keelignore entry."""

    rule_pattern: str
    path_pattern: str
    reason: str
    line_number: int


@dataclass(frozen=True)
class InlineSuppression:
    """An inline keel:ignore comment found in source code."""

    rule: str
    reason: str
    file_path: str
    line_number: int


# Comment prefixes that can contain keel:ignore directives.
_COMMENT_PREFIXES = ("#", "//", "--")

# Regex to extract keel:ignore directive from a comment.
_INLINE_RE = re.compile(r"keel:ignore\s+(\S+)\s+--\s+(.+)")


def parse_keelignore(path: Path) -> list[IgnoreEntry]:
    """Parse a .keelignore file into a list of ignore entries.

    Format per line: <rule-regex> <path-regex> -- <reason>
    Lines starting with # are comments. Blank lines are skipped.
    Entries missing '-- <reason>' are invalid and skipped with a warning.
    """
    if not path.exists():
        return []

    entries: list[IgnoreEntry] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if " -- " not in line and not line.endswith(" --"):
            print(
                f"keel: .keelignore:{line_number}: missing reason (need '-- <reason>'), skipping",
                file=sys.stderr,
            )
            continue

        if line.endswith(" --") or " -- " not in line:
            print(
                f"keel: .keelignore:{line_number}: empty reason after '--', skipping",
                file=sys.stderr,
            )
            continue

        body, reason = line.split(" -- ", 1)
        reason = reason.strip()
        if not reason:
            print(
                f"keel: .keelignore:{line_number}: empty reason after '--', skipping",
                file=sys.stderr,
            )
            continue

        parts = body.split()
        if len(parts) < 2:
            print(
                f"keel: .keelignore:{line_number}: need '<rule-regex> <path-regex>', skipping",
                file=sys.stderr,
            )
            continue

        rule_pattern = parts[0]
        path_pattern = parts[1]

        entries.append(
            IgnoreEntry(
                rule_pattern=rule_pattern,
                path_pattern=path_pattern,
                reason=reason,
                line_number=line_number,
            )
        )

    return entries


def scan_inline_suppressions(file_path: str, content: str) -> list[InlineSuppression]:
    """Scan source file content for inline keel:ignore directives.

    Detects directives in comment tokens (#, //, --) on any line.
    Returns one InlineSuppression per valid directive found.
    Directives missing '-- <reason>' are silently skipped.
    """
    suppressions: list[InlineSuppression] = []

    for line_number, line in enumerate(content.splitlines(), 1):
        # Find comment portion of the line.
        comment = _extract_comment(line)
        if comment is None:
            continue

        match = _INLINE_RE.search(comment)
        if match:
            suppressions.append(
                InlineSuppression(
                    rule=match.group(1),
                    reason=match.group(2).strip(),
                    file_path=file_path,
                    line_number=line_number,
                )
            )

    return suppressions


def is_suppressed(
    finding_rule: str,
    finding_path: str,
    finding_line: int | None,
    keelignore_entries: list[IgnoreEntry],
    inline_suppressions: list[InlineSuppression],
) -> tuple[bool, str | None]:
    """Check if a finding is suppressed by .keelignore or inline comment.

    Returns (True, source_description) if suppressed, (False, None) otherwise.
    Checks .keelignore entries first, then inline suppressions.
    Inline suppressions match on same line or immediately preceding line.
    """
    # Check .keelignore entries (regex match on rule + path).
    for entry in keelignore_entries:
        if re.search(entry.rule_pattern, finding_rule) and re.search(entry.path_pattern, finding_path):
            return True, f".keelignore:{entry.line_number}"

    # Check inline suppressions (exact rule, same or preceding line).
    if finding_line is not None:
        for sup in inline_suppressions:
            if sup.file_path != finding_path:
                continue
            if sup.rule != finding_rule:
                continue
            if sup.line_number == finding_line or sup.line_number == finding_line - 1:
                return True, f"inline:{sup.file_path}:{sup.line_number}"

    return False, None


def _extract_comment(line: str) -> str | None:
    """Extract the comment portion of a line, if any."""
    stripped = line.strip()
    for prefix in _COMMENT_PREFIXES:
        # Full-line comment.
        if stripped.startswith(prefix):
            return stripped[len(prefix) :]
        # Trailing comment: find the last occurrence outside of strings.
        idx = line.rfind(prefix)
        if idx > 0:
            return line[idx + len(prefix) :]
    return None
