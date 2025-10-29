"""Helper utilities for ingestion.

Small convenience helpers used by the ingestion CLI and modules:
- `ensure_dir` creates directories if missing
- `safe_write_text` writes text files safely (creates parents, handles encoding)
- `repo_path_to_out_path` maps a repo-relative path to the output folder while
    preserving directory structure
"""
from __future__ import annotations

import os
from typing import Optional


DEFAULT_TEXT_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".java",
    ".md",
    ".rst",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".html",
    ".css",
    ".sh",
    ".ini",
    ".cfg",
    ".toml",
    ".ipynb",
}


def ensure_dir(path: str) -> None:
    """Create directory if not exists (like mkdir -p).

    This intentionally uses exist_ok=True so repeated runs are safe and
    race conditions when creating directories are handled gracefully.
    """
    os.makedirs(path, exist_ok=True)


def safe_write_text(out_path: str, text: str, encoding: Optional[str] = "utf-8") -> None:
    """Write text to file, creating parent dirs if needed.

    - Ensures parent directories exist before writing.
    - Uses `errors='replace'` to avoid crashes on unexpected encodings; this
      preserves as much text as possible while avoiding exceptions.
    """
    parent = os.path.dirname(out_path)
    if parent:
        ensure_dir(parent)
    with open(out_path, "w", encoding=encoding, errors="replace") as f:
        f.write(text)


def repo_path_to_out_path(out_dir: str, file_path: str) -> str:
    """Convert a repo-relative path (e.g., src/main.py) into an output filename under out_dir.

    This preserves the directory structure so multiple files from different folders don't collide.
    """
    # Normalize Windows backslashes to forward slashes and then join with
    # the output directory so the saved files preserve the repo layout.
    safe_path = file_path.replace("\\", "/")
    return os.path.join(out_dir, safe_path)
