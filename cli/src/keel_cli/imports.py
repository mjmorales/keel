"""Language-specific import extraction and boundary matching.

Normalization contract
-----------------------
Every extractor emits import tokens that are *comparable against a segment's
filesystem path* (``Segment.path``, e.g. ``cli/src`` or ``segments/foo``).
Two conventions coexist in the emitted tokens:

- Path-style, slash-separated (Go, TypeScript, GDScript). GDScript ``res://``
  URIs are stripped to a project-relative path so ``preload("res://segments/foo/bar.gd")``
  becomes ``segments/foo/bar.gd``.
- Module-style, dot- or ``::``-separated (Python, Rust). Python tokens retain
  the *full* dotted module (``pkg.sub.mod``) — they are NOT truncated to the
  top-level package — so dotted segment paths can match.

``import_targets`` is the single boundary predicate that reconciles both
conventions: it treats ``.``, ``::`` and ``/`` as equivalent separators before
comparing, so the same token stream feeds the cross-segment matcher, the
forbidden-import matcher, and the I/O blocklist (`io_blocklist.is_io_import`).
"""

from __future__ import annotations

import re
from pathlib import Path

_SEPARATORS = re.compile(r"::|[./]")


def _normalize(token: str) -> str:
    """Collapse module/path separators (``.``, ``::``, ``/``) to ``/``."""
    return _SEPARATORS.sub("/", token).strip("/")


def import_targets(prefix: str, imp: str) -> bool:
    """Return True if import ``imp`` targets the module/path ``prefix``.

    Boundary-aware: ``api`` matches ``api`` and ``api/client`` but NOT
    ``apiclient``. Separator-agnostic: ``pkg.sub`` matches path ``pkg/sub``.
    """
    p = _normalize(prefix)
    i = _normalize(imp)
    return i == p or i.startswith(p + "/")


LANG_BY_EXT: dict[str, str] = {
    ".go": "go",
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "typescript",
    ".jsx": "typescript",
    ".rs": "rust",
    ".gd": "gdscript",
}


def file_language(file_path: str) -> str | None:
    """Determine language from file extension."""
    return LANG_BY_EXT.get(Path(file_path).suffix.lower())


def extract_imports(content: str, language: str) -> list[str]:
    """Extract imported packages from source code."""
    extractor = _EXTRACTORS.get(language)
    return extractor(content) if extractor else []


def _extract_go(content: str) -> list[str]:
    imports = []
    for match in re.finditer(r'import\s+"([^"]+)"', content):
        imports.append(match.group(1))
    for block in re.finditer(r"import\s*\((.*?)\)", content, re.DOTALL):
        for line in block.group(1).splitlines():
            m = re.search(r'"([^"]+)"', line.strip())
            if m:
                imports.append(m.group(1))
    return imports


def _extract_python(content: str) -> list[str]:
    imports = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("import "):
            for mod in stripped.removeprefix("import ").split(","):
                mod = mod.strip().split(" as ")[0]
                if mod.startswith("."):  # relative import; not segment-comparable
                    continue
                imports.append(mod)
        elif stripped.startswith("from "):
            m = re.match(r"from\s+(\S+)\s+import", stripped)
            if m:
                module = m.group(1)
                if module.startswith("."):  # relative import; not segment-comparable
                    continue
                imports.append(module)
    return imports


def _extract_typescript(content: str) -> list[str]:
    imports = []
    for match in re.finditer(r"""(?:import|from)\s+['"]([@\w/.-]+)['"]""", content):
        imports.append(match.group(1))
    for match in re.finditer(r"""require\(['"]([@\w/.-]+)['"]\)""", content):
        imports.append(match.group(1))
    return imports


def _extract_rust(content: str) -> list[str]:
    imports = []
    for match in re.finditer(r"use\s+([\w:]+)", content):
        imports.append(match.group(1))
    for match in re.finditer(r"extern\s+crate\s+(\w+)", content):
        imports.append(match.group(1))
    return imports


def _extract_gdscript(content: str) -> list[str]:
    imports = []
    for match in re.finditer(r"""(?:preload|load)\(\s*["']res://([^"']+)["']\s*\)""", content):
        # Strip the res:// scheme so the remaining token is a project-relative path.
        imports.append(match.group(1))
    return imports


_EXTRACTORS = {
    "go": _extract_go,
    "python": _extract_python,
    "typescript": _extract_typescript,
    "rust": _extract_rust,
    "gdscript": _extract_gdscript,
}
