#!/usr/bin/env python
from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, List, Optional

from retrieval.retriever import query_collection, build_context
from generation.prompt import allowed_context_chars, format_sources
# generation LLM helpers are imported lazily depending on API choice


def main() -> None:
    # Optional: load environment variables from a .env file if present
    try:
        from dotenv import load_dotenv  # type: ignore[import-not-found]
        load_dotenv()
    except Exception:
        pass
    p = argparse.ArgumentParser(description="Step 5: Generate an explanation from retrieved context using Groq (OpenAI-compatible endpoint).")
    p.add_argument("--chroma-dir", required=True, help="Path to Chroma persistent directory")
    p.add_argument("--collection", required=True, help="Chroma collection name")
    p.add_argument("--query", required=True, help="Student's question")
    p.add_argument("--k", type=int, default=5, help="Top-k chunks to retrieve")
    p.add_argument("--file-type", default=None, help="Optional filter by file_type metadata (e.g., code, markdown)")
    p.add_argument("--embed-model", default="sentence-transformers/all-MiniLM-L6-v2", help="Embedding model name for query (must match collection)")

    # LLM settings
    p.add_argument("--n-ctx", type=int, default=4096, help="Approximate LLM context size (tokens) used to trim context")
    p.add_argument("--max-tokens", type=int, default=400, help="Max new tokens to generate")
    p.add_argument("--temperature", type=float, default=0.3, help="Sampling temperature")
    p.add_argument("--top-p", type=float, default=0.9, help="Top-p nucleus sampling")
    p.add_argument("--repeat-penalty", type=float, default=1.1, help="Repeat penalty (if supported by API)")

    p.add_argument("--show-sources", action="store_true", help="Print a Sources section with file paths")

    # Groq API only (default backend)
    p.add_argument("--api-base", default=None, help="Groq OpenAI-compatible API base (default: https://api.groq.com/openai)")
    p.add_argument("--groq-model", default="llama-3.1-8b-instant", help="Groq model name/id (default: llama-3.1-8b-instant)")
    p.add_argument("--groq-key", default=None, help="Groq API key (or set GROQ_API_KEY env var)")

    args = p.parse_args()

    where: Optional[Dict[str, Any]] = None
    if args.file_type:
        where = {"file_type": args.file_type}

    # Retrieve
    results = query_collection(
        chroma_dir=args.chroma_dir,
        collection_name=args.collection,
        query=args.query,
        model=args.embed_model,
        k=args.k,
        where=where,
    )

    if not results:
        print("No results found for the query.")
        sys.exit(0)

    # Build context trimmed to fit model context window
    ctx_chars = allowed_context_chars(args.n_ctx, args.max_tokens)
    context_block = build_context(results, max_chars=ctx_chars)

    # Generate with Groq (only)
    groq_key = args.groq_key or os.getenv("GROQ_API_KEY")
    if not groq_key:
        print("Error: Missing Groq API key. Provide --groq-key or set GROQ_API_KEY in the environment.")
        sys.exit(2)
    from generation.llm import generate_with_openai_compatible
    groq_base = args.api_base or "https://api.groq.com/openai"
    explanation = generate_with_openai_compatible(
        context_block,
        args.query,
        api_base=groq_base,
        model=args.groq_model,
        api_key=groq_key,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        top_p=args.top_p,
    )

    # Output
    print("\n=== Explanation ===\n")
    print(explanation)

    if args.show_sources:
        print("\n---\nSources:\n")
        for s in format_sources(results):
            print(f"- {s}")


if __name__ == "__main__":
    main()
