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


# The single-line comment token per language. Scanning only a language's real
# token avoids misreading e.g. SQL's "--" inside a "//"-commented language.
_COMMENT_TOKEN_BY_LANG = {
    "python": "#",
    "gdscript": "#",
    "typescript": "//",
    "go": "//",
    "rust": "//",
    "sql": "--",
    "lua": "--",
}

# Fallback token lookup by file extension, used when the caller does not pass an
# explicit language (keeps scan_inline_suppressions usable from path alone).
_COMMENT_TOKEN_BY_EXT = {
    ".py": "#",
    ".gd": "#",
    ".ts": "//",
    ".tsx": "//",
    ".js": "//",
    ".jsx": "//",
    ".go": "//",
    ".rs": "//",
    ".sql": "--",
    ".lua": "--",
}

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

        # Guard 1 already rejected lines lacking any "--", so here a line ending
        # in " --" is precisely the empty-reason case.
        if line.endswith(" --"):
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


def scan_inline_suppressions(file_path: str, content: str, lang: str | None = None) -> list[InlineSuppression]:
    """Scan source file content for inline keel:ignore directives.

    Scans only the language's single-line comment token (e.g. '#' for Python,
    '//' for Go/TS, '--' for SQL). ``lang`` is resolved against the known
    language tokens; when omitted, the token is derived from the file extension.
    Lines whose language/extension is unknown are skipped.
    Returns one InlineSuppression per valid directive found.
    Directives missing '-- <reason>' are silently skipped.
    """
    token = _comment_token(file_path, lang)
    if token is None:
        return []

    suppressions: list[InlineSuppression] = []

    for line_number, line in enumerate(content.splitlines(), 1):
        # Find comment portion of the line.
        comment = _extract_comment(line, token)
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


def _comment_token(file_path: str, lang: str | None) -> str | None:
    """Resolve the single-line comment token for a file.

    Prefers an explicit ``lang``; falls back to the file extension. Returns None
    for unknown languages so callers can skip files keel cannot comment-scan.
    """
    if lang is not None:
        return _COMMENT_TOKEN_BY_LANG.get(lang)
    return _COMMENT_TOKEN_BY_EXT.get(Path(file_path).suffix.lower())


def _extract_comment(line: str, token: str) -> str | None:
    """Extract the comment portion of a line for a given comment token, if any.

    NOTE: not string-literal aware — a token inside a string/char literal is
    treated as a comment start. Acceptable here because the only consumer
    matches the narrow keel:ignore directive, which would not appear in strings.
    """
    stripped = line.strip()
    # Full-line comment.
    if stripped.startswith(token):
        return stripped[len(token) :]
    # Trailing comment: take the last occurrence on the line.
    idx = line.rfind(token)
    if idx > 0:
        return line[idx + len(token) :]
    return None
