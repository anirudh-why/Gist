"""CLI to embed chunks and store them in a Chroma collection (local embeddings).

Example:
PYTHONPATH=./src python scripts/run_embeddings.py --in data/chunks_blogapp.jsonl --chroma-dir ./chroma_db --collection blogapp --model sentence-transformers/all-MiniLM-L6-v2
"""
from __future__ import annotations

import argparse
import os
import sys

from ingest import embeddings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create embeddings for chunk JSONL and store in Chroma.")
    parser.add_argument("--in", dest="input", required=True, help="Input JSONL file from chunker")
    parser.add_argument("--chroma-dir", dest="chroma_dir", default="./chroma_db", help="Chroma persist directory")
    parser.add_argument("--collection", dest="collection", default="repo_embeddings", help="Chroma collection name")
    parser.add_argument("--model", dest="model", default="sentence-transformers/all-MiniLM-L6-v2", help="Sentence-Transformers model name (e.g., sentence-transformers/all-MiniLM-L6-v2)")
    parser.add_argument("--batch-size", dest="batch_size", type=int, default=64, help="Embedding batch size")
    args = parser.parse_args(argv)

    input_file = args.input
    if not os.path.isfile(input_file):
        print(f"Input file not found: {input_file}")
        return 2

    print(f"Embedding {input_file} -> Chroma dir {args.chroma_dir}, collection {args.collection}")
    try:
        count, coll = embeddings.process_and_store(input_file, chroma_persist_directory=args.chroma_dir, collection_name=args.collection, model=args.model, batch_size=args.batch_size, persist=True)
    except Exception as e:
        print("Failed to create embeddings:", e)
        return 3

    print(f"Wrote {count} embeddings into collection: {coll}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
