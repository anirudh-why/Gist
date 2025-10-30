"""CLI to run the Step 2 chunker over a folder of raw files.

Example:
PYTHONPATH=./src python scripts/run_chunker.py --in data/raw_blogapp --repo anirudh-why/blogapp --out data/chunks_blogapp.jsonl
"""
from __future__ import annotations

import argparse
import os
import sys

from ingest import chunker


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Chunk raw repo files into JSONL chunks for embeddings.")
    parser.add_argument("--in", dest="input_dir", default="data/raw", help="Directory with raw files (from Step 1)")
    parser.add_argument("--repo", required=True, help="Repo name to record in metadata (e.g., owner/repo)")
    parser.add_argument("--out", dest="output", default="data/chunks.jsonl", help="Output JSONL file path")
    parser.add_argument("--chunk-size", type=int, default=1000, help="Chunk size in tokens (approx)")
    parser.add_argument("--overlap", type=int, default=200, help="Chunk overlap in tokens (approx)")
    args = parser.parse_args(argv)

    input_dir = args.input_dir
    if not os.path.isdir(input_dir):
        print(f"Input directory not found: {input_dir}")
        return 2

    print(f"Chunking files in {input_dir} -> {args.output} (repo={args.repo})")
    count = chunker.chunk_folder(input_dir, args.repo, args.output, chunk_size_tokens=args.chunk_size, overlap_tokens=args.overlap)
    print(f"Wrote {count} chunks to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
