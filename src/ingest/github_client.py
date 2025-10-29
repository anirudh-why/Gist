"""GitHub ingestion utilities for Step 1 (data ingestion).

This module provides small, focused helpers used by the ingestion CLI.

Responsibilities:
- Parse a GitHub repository URL into (owner, repo)
- Query GitHub for repository metadata and a recursive git tree
- Filter the tree to text/code files we want to ingest
- Download file contents via the fast raw URL (public) or the API (private/fallback)
- Extract useful text from notebooks (.ipynb)

Design notes:
- Keep helpers synchronous and dependency-light so behavior is explicit.
- For private repositories, pass a personal access token (PAT) via the `token` parameter
    to increase the rate limit and allow access to private content.
"""
from __future__ import annotations

import base64
import json
import logging
import os
from typing import Dict, List, Optional, Tuple

import requests

log = logging.getLogger(__name__)

# Common user-agent
HEADERS = {"User-Agent": "repo-ingestor/1.0"}


def parse_github_url(url: str) -> Tuple[str, str]:
    """Parse a GitHub repo URL and return (owner, repo).

    Accepts e.g.:
    - https://github.com/psf/requests
    - https://github.com/psf/requests/
    - git@github.com:psf/requests.git
    - https://github.com/psf/requests.git

    Raises ValueError if the URL doesn't look like a GitHub repo URL.
    """
    # Keep the original for informative error messages
    original = url
    # Normalize whitespace around the URL
    url = url.strip()
    # Handle git@github.com:owner/repo.git
    if url.startswith("git@github.com:"):
        path = url.split(":", 1)[1]
    else:
        # Remove scheme
        if url.startswith("https://") or url.startswith("http://"):
            parts = url.split("github.com/", 1)
            if len(parts) != 2:
                raise ValueError(f"Not a valid GitHub URL: {original}")
            path = parts[1]
        else:
            # maybe owner/repo
            path = url

    path = path.rstrip("/\n")
    if path.endswith(".git"):
        path = path[: -len(".git")]

    parts = path.split("/")
    if len(parts) < 2:
        raise ValueError(f"Could not parse owner/repo from URL: {original}")

    owner, repo = parts[0], parts[1]
    return owner, repo


def get_repo_info(owner: str, repo: str, token: Optional[str] = None) -> Dict:
    """Return repository metadata from GitHub API (public endpoint).

    Returns JSON with keys such as `default_branch`, `description`, `language`.
    """
    # Query the repository endpoint to learn the default branch and metadata.
    # Public repos do not require authentication but providing a token increases
    # rate limits and allows access to private repositories.
    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = HEADERS.copy()
    if token:
        headers["Authorization"] = f"token {token}"
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()


def get_repo_tree(owner: str, repo: str, branch: str, token: Optional[str] = None) -> List[Dict]:
    """Fetch the recursive git tree for the given branch.

    Returns a list of tree entries with keys: path, mode, type, sha, size (optional), url
    """
    # Use the git/trees API with recursive=1 to retrieve a flat list of all
    # files (blobs) and directories (trees) for the branch. This can return
    # a large payload for big repositories.
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    headers = HEADERS.copy()
    if token:
        headers["Authorization"] = f"token {token}"
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    data = r.json()
    tree = data.get("tree", [])
    return tree


TEXT_EXTENSIONS = {
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


def is_text_file(path: str, include_exts: Optional[set] = None) -> bool:
    ext = os.path.splitext(path)[1].lower()
    if include_exts is None:
        return ext in TEXT_EXTENSIONS
    return ext in include_exts


def filter_paths(tree: List[Dict], include_exts: Optional[set] = None, max_file_size: int = 1_000_000) -> List[Dict]:
    """Filter tree entries to text files and reasonable size.

    Parameters
    - tree: output from get_repo_tree
    - include_exts: optional set of extensions to include (e.g., {'.py', '.md'})
    - max_file_size: skip files with size > this many bytes (if size available in tree entry)
    """
    # Build a filtered list of tree entries we intend to fetch.
    # Only include blobs (actual file contents). Exclude directories and other
    # git objects.
    filtered = []
    for entry in tree:
        if entry.get("type") != "blob":
            # not a file
            continue
        path = entry.get("path", "")
        # Extension-based filtering is fast and typically accurate enough
        # to exclude binary assets like images or compiled artifacts.
        if not is_text_file(path, include_exts):
            continue
        # If the git tree provided a size, use it to skip very large files.
        size = entry.get("size")
        if size is not None and size > max_file_size:
            log.debug("Skipping large file %s (%s bytes)", path, size)
            continue
        filtered.append(entry)
    return filtered


def fetch_file_text(owner: str, repo: str, branch: str, path: str, token: Optional[str] = None) -> Tuple[str, Dict]:
    """Fetch file contents as text.

    Strategy:
    1. Try raw.githubusercontent.com URL (fast, works for public files)
    2. If that fails (404 or 403), and token provided, use /repos/{owner}/{repo}/contents/{path} API

    Returns (text, metadata)
    metadata contains: { 'fetched_via': 'raw'|'api', 'encoding'?: ... }
    """
    # First attempt: fetch the raw file via raw.githubusercontent.com which
    # is fast and suitable for public repositories.
    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
    headers = HEADERS.copy()
    try:
        r = requests.get(raw_url, headers=headers, timeout=15)
        if r.status_code == 200:
            # Use requests' detected encoding for best-effort decoding.
            r.encoding = r.apparent_encoding or "utf-8"
            return r.text, {"fetched_via": "raw"}
        else:
            log.debug("Raw fetch failed for %s: %s", raw_url, r.status_code)
    except requests.RequestException as e:
        # Log and fall through to the API-based fetch below.
        log.debug("Raw fetch exception for %s: %s", raw_url, e)

    # Try API endpoint (works for private repos when token is provided)
    # Fallback: use the GitHub contents API. This supports private repos when
    # an authorization token is provided and always returns structured JSON.
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
    headers = HEADERS.copy()
    if token:
        headers["Authorization"] = f"token {token}"
    r = requests.get(api_url, headers=headers, timeout=15)
    r.raise_for_status()
    data = r.json()
    if data.get("encoding") == "base64" and "content" in data:
        content_b64 = data["content"]
        # content may include newlines; decode robustly
        content_bytes = base64.b64decode(content_b64)
        try:
            text = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            # Fall back to latin-1 to avoid crashes; callers can handle
            # any decoding artifacts later.
            text = content_bytes.decode("latin-1")
        return text, {"fetched_via": "api", "encoding": "base64"}
    elif isinstance(data, dict) and data.get("type") == "file" and "content" in data:
        # Some API responses may return content in plain text already.
        text = data["content"]
        return text, {"fetched_via": "api"}
    else:
        # Not a file or unknown format
        raise RuntimeError(f"Unexpected content response for {path}")


def extract_notebook_text(nb_content: str) -> str:
    """Extract text from a notebook JSON string by joining code and markdown cell sources."""
    try:
        nb = json.loads(nb_content)
    except Exception:
        return ""
    parts = []
    for cell in nb.get("cells", []):
        cell_type = cell.get("cell_type")
        src = cell.get("source", [])
        if isinstance(src, list):
            src_text = "".join(src)
        else:
            src_text = str(src)
        # Add a tiny header per cell so downstream processors can tell apart
        # markdown vs code. This helps when chunking or building context.
        parts.append(f"# {cell_type} cell\n" + src_text)
    return "\n\n".join(parts)
