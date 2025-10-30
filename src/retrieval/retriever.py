"""Retrieval utilities (Step 4: the R in RAG).

This module embeds a user query with the same local Sentence-Transformers model
used for documents, searches a Chroma collection for the most similar chunks,
and returns ranked results plus a helper to build a context block.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ingest.embeddings import embed_texts_sbert


def embed_query(query: str, model: str = "sentence-transformers/all-MiniLM-L6-v2") -> List[float]:
    """Embed a single query string into a vector using the local model."""
    if not query or not query.strip():
        raise ValueError("Query is empty")
    vecs = embed_texts_sbert([query.strip()], model=model)
    return vecs[0]


def query_collection(
    chroma_dir: str,
    collection_name: str,
    query: str,
    *,
    model: str = "sentence-transformers/all-MiniLM-L6-v2",
    k: int = 5,
    where: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Query a Chroma collection by semantic similarity.

    Returns a list of {id, document, metadata, distance} sorted by similarity.
    """
    # Import chromadb lazily to avoid hard failure if not installed in analysis tools
    try:
        import chromadb  # type: ignore[import-not-found]
    except Exception as e:
        raise RuntimeError("The `chromadb` package is required. Install with `pip install chromadb`.") from e

    # Create or open the persistent client
    client = chromadb.PersistentClient(path=chroma_dir)
    coll = client.get_collection(name=collection_name)

    qvec = embed_query(query, model=model)

    # Use explicit query_embeddings because we provide our own vectors
    if where:
        resp = coll.query(query_embeddings=[qvec], n_results=k, where=where)
    else:
        resp = coll.query(query_embeddings=[qvec], n_results=k)

    ids = resp.get("ids", [[]])[0] if resp.get("ids") else []
    docs = resp.get("documents", [[]])[0] if resp.get("documents") else []
    metas = resp.get("metadatas", [[]])[0] if resp.get("metadatas") else []
    dists = resp.get("distances", [[]])[0] if resp.get("distances") else [None] * len(ids)

    results: List[Dict[str, Any]] = []
    for _id, _doc, _meta, _dist in zip(ids, docs, metas, dists):
        results.append({
            "id": _id,
            "document": _doc,
            "metadata": _meta,
            "distance": _dist,
        })
    return results


def build_context(results: List[Dict[str, Any]], max_chars: int = 8000) -> str:
    """Format retrieved results into a single context string with separators.

    Truncates to approximately `max_chars` total characters.
    """
    parts: List[str] = []
    total = 0
    for i, r in enumerate(results, start=1):
        meta = r.get("metadata", {}) or {}
        file_path = meta.get("file_path", "")
        repo = meta.get("repo", "")
        chunk_index = meta.get("chunk_index", None)
        header = f"[CTX #{i}] {repo} :: {file_path} :: chunk {chunk_index}"
        body = r.get("document", "")
        block = f"{header}\n{body}".strip()
        if total + len(block) + 2 > max_chars:
            break
        parts.append(block)
        total += len(block) + 2
    return "\n\n---\n\n".join(parts)
