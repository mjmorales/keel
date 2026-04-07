"""Language-specific import extraction."""

from __future__ import annotations

import re
from pathlib import Path

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
                imports.append(mod.strip().split(" as ")[0].split(".")[0])
        elif stripped.startswith("from "):
            m = re.match(r"from\s+(\S+)\s+import", stripped)
            if m:
                imports.append(m.group(1).split(".")[0])
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
    for match in re.finditer(r"""(?:preload|load)\(\s*["'](res://[^"']+)["']\s*\)""", content):
        imports.append(match.group(1))
    return imports


_EXTRACTORS = {
    "go": _extract_go,
    "python": _extract_python,
    "typescript": _extract_typescript,
    "rust": _extract_rust,
    "gdscript": _extract_gdscript,
}
