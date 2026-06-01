"""Source-file discovery and test classification.

Single pipeline for ``git listing -> language filter -> exists() ->
read_text -> classify`` so ``map``, ``check``, and ``audit`` agree on which
files are source and which are tests.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterator, Literal

from keel_cli.imports import file_language

# Path segments that mark a directory of tests.
_TEST_DIRS = ("tests", "__tests__")


def classify_kind(file_path: str) -> Literal["test", "source"]:
    """Classify a file as a test or source by its name and path segments.

    Covers ``test_*``, ``*_test``, ``*.test.*``, ``*.spec.*`` filenames and
    any path under a ``tests/`` or ``__tests__/`` directory.
    """
    path = Path(file_path)
    if any(part in _TEST_DIRS for part in path.parts[:-1]):
        return "test"

    name = path.name
    stem = path.stem
    if stem.startswith("test_") or stem.endswith("_test"):
        return "test"
    if ".test." in name or ".spec." in name:
        return "test"
    return "source"


def _git_tracked(project_root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    return [f for f in result.stdout.strip().splitlines() if f]


def iter_source_files(
    project_root: Path,
    *,
    mode: Literal["tracked"] = "tracked",
    files: list[str] | None = None,
) -> Iterator[tuple[str, str, str]]:
    """Yield ``(rel_path, language, content)`` for each source (non-test) file.

    ``mode="tracked"`` lists files via ``git ls-files``. Pass an explicit
    ``files`` list to discover from an arbitrary set (e.g. audit's diff union);
    when ``files`` is given, ``mode`` is ignored.

    Files are filtered to known languages, must exist on disk, and are read
    with ``errors="replace"``. Test files are skipped.
    """
    if files is None:
        if mode == "tracked":
            files = _git_tracked(project_root)
        else:  # pragma: no cover - guarded by Literal type
            raise ValueError(f"unknown mode: {mode}")

    for file_path in files:
        language = file_language(file_path)
        if not language:
            continue
        if classify_kind(file_path) == "test":
            continue
        full_path = project_root / file_path
        if not full_path.exists():
            continue
        content = full_path.read_text(encoding="utf-8", errors="replace")
        yield file_path, language, content
