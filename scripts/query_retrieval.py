"""Query a Chroma collection using local Sentence-Transformers embeddings (Step 4).

Example:
PYTHONPATH=./src python scripts/query_retrieval.py \
  --chroma-dir ./chroma_db_handy \
  --collection handy_sbert \
  --model sentence-transformers/all-MiniLM-L6-v2 \
  --k 5 \
  --query "How does the app handle settings?"
"""
from __future__ import annotations

import argparse
import os
from typing import Optional, Dict, Any

from retrieval.retriever import query_collection, build_context


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Semantic retrieval from a Chroma collection (local embeddings)")
    p.add_argument("--chroma-dir", required=True, help="Chroma persist directory")
    p.add_argument("--collection", required=True, help="Chroma collection name")
    p.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2", help="Sentence-Transformers model path/name")
    p.add_argument("--k", type=int, default=5, help="Top-K results to return")
    p.add_argument("--file-type", dest="file_type", default=None, help="Optional metadata filter by file_type (e.g., code, markdown, config)")
    p.add_argument("--query", required=True, help="User query text")
    p.add_argument("--max-context-chars", type=int, default=8000, help="Max characters to include in the combined context output")
    args = p.parse_args(argv)

    where: Optional[Dict[str, Any]] = None
    if args.file_type:
        where = {"file_type": args.file_type}

    results = query_collection(
        chroma_dir=args.chroma_dir,
        collection_name=args.collection,
        query=args.query,
        model=args.model,
        k=args.k,
        where=where,
    )

    print(f"Retrieved {len(results)} results\n")
    for i, r in enumerate(results, start=1):
        meta = r.get("metadata", {}) or {}
        print(f"[{i}] id={r.get('id')} distance={r.get('distance')} file={meta.get('file_path')} type={meta.get('file_type')} chunk={meta.get('chunk_index')}")

    print("\n--- Context Preview ---\n")
    context = build_context(results, max_chars=args.max_context_chars)
    print(context)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
