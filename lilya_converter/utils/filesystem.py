"""Filesystem helpers for deterministic conversion writes."""

from __future__ import annotations

import shutil
from pathlib import Path


def iter_files(root: Path) -> list[Path]:
    """Collect non-hidden files under `root` in sorted order.

    Args:
        root: Directory root to traverse.

    Returns:
        A sorted list of file paths.
    """
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        if any(part.startswith(".") for part in path.relative_to(root).parts):
            continue
        files.append(path)
    return files


def safe_write(path: Path, content: str) -> None:
    """Write text content to a file, creating parent directories.

    Args:
        path: Output file path.
        content: Text content to write using UTF-8 encoding.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def copy_file(source: Path, target: Path) -> None:
    """Copy a file while ensuring parent directories exist.

    Args:
        source: Source file path.
        target: Destination file path.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
