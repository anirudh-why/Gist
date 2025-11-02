#!/usr/bin/env python
from __future__ import annotations

"""
Interactive end-to-end runner for Steps 1–5.

What this does
- Option A: Ingest a new GitHub repo (Steps 1–3), then ask a question (Steps 4–5)
- Option B: Use an existing Chroma collection and ask a question directly

Backends supported for generation:
- Groq (OpenAI-compatible endpoint at https://api.groq.com/openai)
- Hugging Face Inference API
- Any OpenAI-compatible server (LM Studio, vLLM, etc.)

Secrets
- Loads environment variables from a .env file if available via python-dotenv
- GROQ_API_KEY / HF_TOKEN / OPENAI_API_KEY are read automatically when relevant
"""

import os
import sys
from typing import Optional, Dict, Any, List


def _load_env() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore[import-not-found]
        load_dotenv()
    except Exception:
        pass


def _prompt(msg: str, default: Optional[str] = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    val = input(f"{msg}{suffix}: ").strip()
    if not val and default is not None:
        return default
    return val


def _yes_no(msg: str, default_yes: bool = True) -> bool:
    default = "Y/n" if default_yes else "y/N"
    val = input(f"{msg} ({default}): ").strip().lower()
    if not val:
        return default_yes
    return val in {"y", "yes"}


def _split_csv(val: str) -> Optional[set[str]]:
    if not val:
        return None
    parts = {p.strip() for p in val.split(',') if p.strip()}
    return parts or None


def run_ingest_chunk_embed(repo_url: str,
                           out_raw: str,
                           chunks_out: str,
                           chroma_dir: str,
                           collection: str,
                           *,
                           token: Optional[str],
                           include_exts: Optional[set[str]],
                           exclude_paths: Optional[set[str]],
                           max_size: int,
                           chunk_size: int,
                           overlap: int,
                           embed_model: str,
                           batch_size: int,
                           use_dummy_embeddings: bool) -> None:
    # Import pipeline helpers dynamically
    from scripts.run_pipeline import ingest_repo, chunk_files, store_embeddings

    # Attach excludes for filter_paths via the same pattern used in run_pipeline
    ingest_repo._path_excludes = exclude_paths  # type: ignore[attr-defined]

    fetched = ingest_repo(repo_url, out_raw, token, max_size, include_exts)
    if fetched == 0:
        print("No files fetched; aborting.")
        sys.exit(3)

    repo_slug = repo_url.replace('https://github.com/', '').rstrip('/')
    chunks_count = chunk_files(out_raw, repo_slug, chunks_out, chunk_size, overlap)
    if chunks_count == 0:
        print('No chunks produced; aborting.')
        sys.exit(4)

    store_embeddings(chunks_out, chroma_dir, collection, embed_model, batch_size, use_dummy_embeddings)


def run_retrieve_and_generate(chroma_dir: str,
                              collection: str,
                              query: str,
                              *,
                              k: int,
                              embed_model: str,
                              n_ctx: int,
                              max_tokens: int,
                              temperature: float,
                              top_p: float,
                              backend: str,
                              api_base: Optional[str] = None,
                              api_model: Optional[str] = None,
                              api_key: Optional[str] = None,
                              show_sources: bool = True) -> None:
    from retrieval.retriever import query_collection, build_context
    from generation.prompt import allowed_context_chars, format_sources

    where = None  # could be extended to filter by file_type interactively
    results = query_collection(
        chroma_dir=chroma_dir,
        collection_name=collection,
        query=query,
        model=embed_model,
        k=k,
        where=where,
    )

    if not results:
        print("No results found for the query.")
        return

    ctx_chars = allowed_context_chars(n_ctx, max_tokens)
    context_block = build_context(results, max_chars=ctx_chars)

    if backend == "groq":
        base = api_base or "https://api.groq.com/openai"
        key = api_key or os.getenv("GROQ_API_KEY")
        model = api_model or _prompt("Groq model", "llama-3.1-8b-instant")
        if not key:
            print("GROQ_API_KEY is required for Groq.")
            return
        from generation.llm import generate_with_openai_compatible
        explanation = generate_with_openai_compatible(
            context_block, query, api_base=base, model=model, api_key=key,
            temperature=temperature, max_tokens=max_tokens, top_p=top_p,
        )
    elif backend == "hf":
        model = api_model or _prompt("HF model id", "google/gemma-2-9b-it")
        token = api_key or os.getenv("HF_TOKEN")
        if not token:
            print("HF_TOKEN is required for Hugging Face Inference API.")
            return
        from generation.llm import generate_with_hf_inference
        explanation = generate_with_hf_inference(
            context_block, query, model=model, token=token,
            temperature=temperature, max_tokens=max_tokens, top_p=top_p,
        )
    elif backend == "openai-compatible":
        base = api_base or _prompt("API base (e.g., http://localhost:1234)")
        model = api_model or _prompt("API model id", "gpt-4o-mini")
        key = api_key or os.getenv("OPENAI_API_KEY")
        from generation.llm import generate_with_openai_compatible
        explanation = generate_with_openai_compatible(
            context_block, query, api_base=base, model=model, api_key=key,
            temperature=temperature, max_tokens=max_tokens, top_p=top_p,
        )
    else:
        print("Unknown backend; choose groq, hf, or openai-compatible.")
        return

    print("\n=== Explanation ===\n")
    print(explanation)
    if show_sources:
        print("\n---\nSources:\n")
        for s in format_sources(results):
            print(f"- {s}")


def main() -> int:
    # Ensure imports can find project modules when run directly
    here = os.path.abspath(os.path.dirname(__file__))
    root = os.path.dirname(here)
    sys.path.insert(0, root)      # for scripts.* imports
    sys.path.insert(0, os.path.join(root, 'src'))  # for src.* imports

    _load_env()

    print("Interactive RAG Runner (Steps 1–5)")
    print("=================================")
    print("Choose a mode:")
    print("  1) Ingest a new GitHub repo (Steps 1–3), then ask a question (Steps 4–5)")
    print("  2) Use an existing Chroma collection and ask a question (Steps 4–5)")
    mode = _prompt("Select 1 or 2", "2")

    # Common defaults
    embed_model = _prompt("Embedding model", "sentence-transformers/all-MiniLM-L6-v2")
    k = int(_prompt("Top-K to retrieve", "5"))
    n_ctx = int(_prompt("Approx LLM context size (n_ctx)", "4096"))
    max_tokens = int(_prompt("Max new tokens", "400"))
    temperature = float(_prompt("Temperature", "0.3"))
    top_p = float(_prompt("Top-p", "0.9"))
    show_sources = _yes_no("Show sources?", True)

    if mode == "1":
        # Ingestion path
        repo_url = _prompt("GitHub repo URL (https://github.com/owner/repo)")
        token = os.getenv("GITHUB_TOKEN") or _prompt("GitHub token (optional, blank for public)", "")
        token = token or None

        default_slug = repo_url.replace('https://github.com/', '').rstrip('/') if repo_url else "repo"
        out_raw = _prompt("Directory for raw files", f"data/raw_{default_slug.replace('/', '_')}")
        chunks_out = _prompt("Chunks JSONL path", f"data/chunks_{default_slug.replace('/', '_')}.jsonl")
        chroma_dir = _prompt("Chroma DB directory", f"./chroma_db_{default_slug.split('/')[-1]}")
        collection = _prompt("Chroma collection name", f"{default_slug.split('/')[-1]}_sbert")

        include_exts = _split_csv(_prompt("Include extensions (csv, blank=auto)", ""))
        exclude_paths = _split_csv(_prompt("Exclude paths (csv)", "node_modules,dist,.cache,build,.git"))
        max_size = int(_prompt("Max file size (bytes)", "1000000"))
        chunk_size = int(_prompt("Chunk size (tokens, approx)", "1000"))
        overlap = int(_prompt("Chunk overlap (tokens, approx)", "200"))
        batch_size = int(_prompt("Embedding batch size", "64"))
        use_dummy_embeddings = _yes_no("Use dummy embeddings? (for quick dry-run)", False)

        print("\n--- Running Steps 1–3 ---")
        run_ingest_chunk_embed(
            repo_url=repo_url,
            out_raw=out_raw,
            chunks_out=chunks_out,
            chroma_dir=chroma_dir,
            collection=collection,
            token=token,
            include_exts=include_exts,
            exclude_paths=exclude_paths,
            max_size=max_size,
            chunk_size=chunk_size,
            overlap=overlap,
            embed_model=embed_model,
            batch_size=batch_size,
            use_dummy_embeddings=use_dummy_embeddings,
        )

        query = _prompt("Enter your question")

    else:
        # Use existing collection
        chroma_dir = _prompt("Chroma DB directory", "./chroma_db")
        collection = _prompt("Chroma collection name")
        query = _prompt("Enter your question")

    print("\nChoose a generation backend:")
    print("  1) Groq (recommended)")
    print("  2) Hugging Face Inference API")
    print("  3) OpenAI-compatible server")
    bsel = _prompt("Select 1/2/3", "1")
    if bsel == "1":
        backend = "groq"
        api_base = os.getenv("GROQ_API_BASE") or "https://api.groq.com/openai"
        api_model = _prompt("Groq model", "llama-3.1-8b-instant")
        api_key = os.getenv("GROQ_API_KEY") or _prompt("Groq API key (or leave blank to use env)", "") or None
    elif bsel == "2":
        backend = "hf"
        api_base = None
        api_model = _prompt("HF model id", "google/gemma-2-9b-it")
        api_key = os.getenv("HF_TOKEN") or _prompt("HF token (or leave blank to use env)", "") or None
    else:
        backend = "openai-compatible"
        api_base = _prompt("API base (e.g., http://localhost:1234)")
        api_model = _prompt("API model id", "gpt-4o-mini")
        api_key = os.getenv("OPENAI_API_KEY") or _prompt("API key (optional)", "") or None

    print("\n--- Generating answer (Step 5) ---")
    run_retrieve_and_generate(
        chroma_dir=chroma_dir,
        collection=collection,
        query=query,
        k=k,
        embed_model=embed_model,
        n_ctx=n_ctx,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        backend=backend,
        api_base=api_base,
        api_model=api_model,
        api_key=api_key,
        show_sources=show_sources,
    )

    # Optionally loop for another question with same collection
    while _yes_no("Ask another question with the same collection?", False):
        query = _prompt("Enter your question")
        run_retrieve_and_generate(
            chroma_dir=chroma_dir,
            collection=collection,
            query=query,
            k=k,
            embed_model=embed_model,
            n_ctx=n_ctx,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            backend=backend,
            api_base=api_base,
            api_model=api_model,
            api_key=api_key,
            show_sources=show_sources,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
