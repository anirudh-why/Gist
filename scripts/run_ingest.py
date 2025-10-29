"""CLI runner to perform Step 1 ingestion for a GitHub repo.

This script orchestrates the Step 1 ingestion flow:

- Parse a GitHub repository URL
- Query repository metadata (default branch)
- Retrieve a recursive file tree
- Filter the tree to text/code files
- Download each file and save it under the output directory while
    preserving the repo folder structure

Notes:
- For public repositories no token is required. For private repositories
    provide a personal access token via --token or set the GITHUB_TOKEN env var.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Optional

from ingest import github_client
from ingest import utils


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest a GitHub repository's text files.")
    parser.add_argument("repo_url", help="GitHub repo URL, e.g. https://github.com/owner/repo")
    parser.add_argument("--out", default="data/raw", help="Output directory to save files")
    parser.add_argument("--token", default=None, help="GitHub personal access token (or set GITHUB_TOKEN env var)")
    parser.add_argument("--max-size", type=int, default=1_000_000, help="Max file size in bytes to fetch")
    parser.add_argument("--extensions", default=None, help="Comma-separated list of extensions to include (e.g. .py,.md)")
    args = parser.parse_args(argv)

    # Prefer explicit token argument, fall back to environment variable if set.
    token = args.token or os.environ.get("GITHUB_TOKEN")

    # Parse the provided repo URL into owner/repo. This validates the input
    # early and gives a clear error message if the URL is malformed.
    try:
        owner, repo = github_client.parse_github_url(args.repo_url)
    except ValueError as e:
        print("Error parsing repo URL:", e)
        return 2

    # Query repository metadata to determine the default branch and other
    # useful information. The default branch is used when constructing raw
    # URLs for file downloads.
    print(f"Fetching repository info for {owner}/{repo}...")
    repo_info = github_client.get_repo_info(owner, repo, token=token)
    branch = repo_info.get("default_branch", "main")
    print(f"Default branch: {branch}")

    # Retrieve a recursive git tree which contains path and size metadata for
    # each file. This is a single API call but the response may be large.
    print("Fetching file tree (this may take a moment for large repos)...")
    tree = github_client.get_repo_tree(owner, repo, branch, token=token)
    print(f"Tree entries: {len(tree)}")

    include_exts = None
    if args.extensions:
        include_exts = {ext.strip().lower() for ext in args.extensions.split(",") if ext.strip()}

    # Apply extension and size filters to the tree to produce a list of
    # candidate files to download. This prevents fetching images, binaries,
    # and extremely large files which aren't useful for text embeddings.
    filtered = github_client.filter_paths(tree, include_exts=include_exts, max_file_size=args.max_size)
    print(f"Filtered files (text/code): {len(filtered)}")

    out_dir = args.out
    start = time.time()
    # Iterate over filtered files and fetch contents one-by-one. We intentionally
    # keep this loop synchronous to make behavior predictable; concurrency can
    # be added later if desired for speed.
    for idx, entry in enumerate(filtered, start=1):
        path = entry.get("path")
        if not path:
            continue
        try:
            # Download the file content. The fetch function will try raw
            # URLs first and fall back to the API (required for private repos).
            text, meta = github_client.fetch_file_text(owner, repo, branch, path, token=token)
            # For notebooks, extract the readable markdown/code into a single
            # text blob so downstream chunking can handle it.
            if path.lower().endswith(".ipynb"):
                text = github_client.extract_notebook_text(text)
            # Map the repo path to an output path that preserves folder layout
            out_path = utils.repo_path_to_out_path(out_dir, path)
            utils.safe_write_text(out_path, text)
            print(f"[{idx}/{len(filtered)}] Saved: {path} -> {out_path} ({meta.get('fetched_via')})")
        except Exception as e:
            # Continue on errors but report them so the user can inspect failures.
            print(f"[{idx}/{len(filtered)}] Failed to fetch {path}: {e}")

    elapsed = time.time() - start
    print(f"Done. Wrote {len(filtered)} files to {out_dir} in {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
