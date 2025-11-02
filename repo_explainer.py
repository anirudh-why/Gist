#!/usr/bin/env python
from __future__ import annotations

"""
Minimal interactive runner with only two prompts:

1) Choose mode: Ingest new repo (1) or Use existing collection (2)
2) Provide GitHub repo URL (for mode 1) or provide existing Chroma dir + collection (for mode 2)

Behavior:
- Mode 1: Runs Steps 1–3 with sensible defaults, then prints two example questions.
- Mode 2: Skips directly to using an existing collection, then prints two example questions.

Notes:
- Embeddings are created with the 'all-MiniLM-L6-v2' model.
- Generation (Step 5) is intended to use Groq by default (e.g., llama-3.1-8b-instant) via scripts/run_generation.py.
  This script does not run generation; it simply prepares data and shows example questions.
"""

import os
import sys
from typing import Optional, Set


def _load_env() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore[import-not-found]
        load_dotenv()
    except Exception:
        pass


def _prompt(msg: str, default: Optional[str] = None) -> str:
    suffix = f" {default}" if default is not None else ""
    val = input(f"{msg}{': ' if not suffix else f' [{default}]: '} ").strip()
    if not val and default is not None:
        return default
    return val


def _ingest_chunk_embed(repo_url: str) -> tuple[str, str]:
    """Run Steps 1–3 for the given repo URL with fixed defaults.

    Returns (chroma_dir, collection)
    """
    # Defer imports to avoid global dependency costs
    from scripts.run_pipeline import ingest_repo, chunk_files, store_embeddings

    # Defaults
    token = os.getenv("GITHUB_TOKEN")
    slug = repo_url.replace("https://github.com/", "").rstrip("/")
    repo_name = slug.split("/")[-1] if slug else "repo"
    out_raw = f"data/raw_{slug.replace('/', '_')}"
    chunks_out = f"data/chunks_{slug.replace('/', '_')}.jsonl"
    chroma_dir = f"./chroma_db_{repo_name}"
    collection = f"{repo_name}_sbert"

    # Filters and parameters
    include_exts: Optional[Set[str]] = None  # auto
    exclude_paths: Optional[Set[str]] = {"node_modules", "dist", ".cache", "build", ".git", ".venv", "venv"}
    max_size = 1_000_000
    chunk_size = 1000
    overlap = 200
    embed_model = "sentence-transformers/all-MiniLM-L6-v2"
    batch_size = 64
    use_dummy_embeddings = False

    # Wire excludes into ingest_repo hook
    ingest_repo._path_excludes = exclude_paths  # type: ignore[attr-defined]

    print("\n✅ Fetching repo files...")
    fetched = ingest_repo(repo_url, out_raw, token, max_size, include_exts)
    if fetched == 0:
        print("No files fetched; aborting.")
        sys.exit(2)

    print("✅ Splitting into chunks...")
    chunks_count = chunk_files(out_raw, slug, chunks_out, chunk_size, overlap)
    if chunks_count == 0:
        print("No chunks produced; aborting.")
        sys.exit(3)

    print("✅ Creating embeddings with all-MiniLM-L6-v2...")
    store_embeddings(chunks_out, chroma_dir, collection, embed_model, batch_size, use_dummy_embeddings)
    print(f"✅ Stored in Chroma DB (collection: {collection})")

    return chroma_dir, collection


def main() -> int:
    # Ensure imports work
    here = os.path.abspath(os.path.dirname(__file__))
    sys.path.insert(0, here)
    sys.path.insert(0, os.path.join(here, "src"))

    _load_env()

    print("Choose mode:")
    print("1) Ingest new GitHub repo")
    print("2) Use existing collection")
    mode = _prompt("Select [1/2]", "1")

    if mode == "1":
        repo_url = _prompt("Enter GitHub repo URL")
        chroma_dir, collection = _ingest_chunk_embed(repo_url)
    else:
        chroma_dir = _prompt("Enter Chroma DB directory", "./chroma_db")
        # Try to list collections for convenience; fall back to manual input
        try:
            import chromadb  # type: ignore[import-not-found]
            client = chromadb.PersistentClient(path=chroma_dir)
            colls = client.list_collections()
            options = [c.name for c in colls]
            if options:
                print("\nCollections found:")
                for i, name in enumerate(options, start=1):
                    print(f"  {i}) {name}")
                sel = input("Select a collection by number (or press Enter to type manually): ").strip()
                if sel.isdigit() and 1 <= int(sel) <= len(options):
                    collection = options[int(sel) - 1]
                else:
                    collection = _prompt("Enter Chroma collection name")
            else:
                collection = _prompt("Enter Chroma collection name")
        except Exception:
            collection = _prompt("Enter Chroma collection name")

    # Final guidance with exactly two example questions
    print("\nNow you can ask questions like:")
    print("\u2192 \"What does main.py do?\"")
    print("\u2192 \"Explain the folder structure.\"")

    # Optional Q&A loop (Groq-only, minimal prompts)
    try:
        from retrieval.retriever import query_collection, build_context
        from generation.prompt import allowed_context_chars, format_sources
        from generation.llm import generate_with_openai_compatible
    except Exception as e:
        # Retrieval/generation modules not available; skip Q&A
        return 0

    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        print("\nTip: To get answers now, set GROQ_API_KEY in your environment or .env, then re-run.")
        return 0

    # Fixed, sensible defaults for quick answers
    embed_model = "sentence-transformers/all-MiniLM-L6-v2"
    k = 5
    n_ctx = 4096
    max_tokens = 400
    temperature = 0.3
    top_p = 0.9
    groq_base = os.getenv("GROQ_API_BASE") or "https://api.groq.com/openai"
    groq_model = os.getenv("GROQ_MODEL") or "llama-3.1-8b-instant"

    while True:
        q = input("\nAsk a question (leave blank to finish): ").strip()
        if not q:
            break
        try:
            results = query_collection(
                chroma_dir=chroma_dir,
                collection_name=collection,
                query=q,
                model=embed_model,
                k=k,
                where=None,
            )
            if not results:
                print("No results found for the query.")
                continue
            ctx_chars = allowed_context_chars(n_ctx, max_tokens)
            context_block = build_context(results, max_chars=ctx_chars)
            answer = generate_with_openai_compatible(
                context_block,
                q,
                api_base=groq_base,
                model=groq_model,
                api_key=groq_key,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
            )
            print("\n=== Answer ===\n")
            print(answer)
            print("\n---\nSources:\n")
            for s in format_sources(results):
                print(f"- {s}")
        except Exception as e:
            print(f"Generation failed: {e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
