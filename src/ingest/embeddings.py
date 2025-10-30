"""Embedding generation and Chroma storage utilities (Step 3).

This module reads chunk JSONL output (from Step 2), obtains embeddings via
Sentence-Transformers (local), and stores vectors+metadata in a local Chroma collection.

Usage notes:
- Install dependencies from requirements.txt (chromadb, sentence-transformers).
"""
from __future__ import annotations

import json
import os
import time
from typing import Dict, Iterable, List, Optional, Tuple, Any

# No environment variable loading required for local embeddings.


def load_jsonl_chunks(path: str) -> List[Dict]:
    """Read a JSONL file produced by the chunker and return a list of chunk dicts."""
    out: List[Dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


# OpenAI integration removed; using Sentence-Transformers only.


_SBERT_MODEL_CACHE: Dict[str, Any] = {}

def embed_texts_sbert(texts: List[str], model: str = "sentence-transformers/all-MiniLM-L6-v2") -> List[List[float]]:
    """Embed texts using a local Sentence-Transformers model.

    Returns a list of vector lists (floats) in the same order as `texts`.
    """
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as _np
    except Exception as e:
        raise RuntimeError("The `sentence-transformers` package is required. Install with `pip install sentence-transformers`.") from e

    # Cache model instance across calls
    if model not in _SBERT_MODEL_CACHE:
        _SBERT_MODEL_CACHE[model] = SentenceTransformer(model)
    st_model = _SBERT_MODEL_CACHE[model]
    # Encode returns numpy arrays; convert to Python lists of floats
    vecs = st_model.encode(texts, batch_size=max(8, min(64, len(texts))), convert_to_numpy=True, normalize_embeddings=False)
    if hasattr(vecs, 'tolist'):
        return vecs.tolist()
    # Fallback if it returns list of arrays
    return [(_v.tolist() if hasattr(_v, 'tolist') else list(_v)) for _v in vecs]


def batchify(iterable: Iterable, batch_size: int):
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def process_and_store(jsonl_path: str,
                      chroma_persist_directory: str = "./chroma_db",
                      collection_name: str = "repo_embeddings",
                      model: str = "sentence-transformers/all-MiniLM-L6-v2",
                      batch_size: int = 64,
                      persist: bool = True) -> Tuple[int, str]:
    """Main entry: read chunks, embed them in batches, and store in Chroma.

    Returns (count_of_embeddings, collection_name).
    """
    # Lazy import chromadb to provide an informative error if missing
    try:
        import chromadb
    except Exception as e:
        raise RuntimeError("The `chromadb` package is required. Install with `pip install chromadb`.") from e

    chunks = load_jsonl_chunks(jsonl_path)
    total = 0

    # Prepare Chroma client and collection.
    # Prefer the modern PersistentClient which writes to disk at the given path.
    # If that fails (e.g., due to environment issues), fall back to in-memory client
    # and write a JSONL backup so embeddings are not lost.
    fallback_backup = False
    try:
        client = chromadb.PersistentClient(path=chroma_persist_directory)
        try:
            collection = client.create_collection(name=collection_name)
        except Exception:
            collection = client.get_collection(name=collection_name)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("PersistentClient failed (%s); falling back to in-memory client and JSONL backup at %s", e, chroma_persist_directory)
        fallback_backup = True
        client = chromadb.Client()
        collection = client.create_collection(name=collection_name)

    ids: List[str] = []
    metadatas: List[Dict] = []
    docs: List[str] = []
    embeddings_all: List[List[float]] = []

    # Prepare records: id, doc, metadata
    for idx, rec in enumerate(chunks):
        meta = rec.get("metadata", {})
        repo = meta.get("repo", "")
        file_path = meta.get("file_path", "")
        chunk_index = meta.get("chunk_index", idx)
        # deterministic id
        rid = f"{repo}::{file_path}::{chunk_index}"
        ids.append(rid)
        metadatas.append(meta)
        docs.append(rec.get("content", ""))

    # Batch embedding + insert to avoid memory spikes
    for batch_idx, doc_batch in enumerate(batchify(list(zip(ids, docs, metadatas)), batch_size)):
        batch_ids, batch_docs, batch_metas = zip(*doc_batch)
        texts = list(batch_docs)
        # Obtain embeddings via local Sentence-Transformers
        # If a non-sbert name was passed, default to MiniLM
        if not (model.startswith("sentence-transformers/") or model == "all-MiniLM-L6-v2"):
            model = "sentence-transformers/all-MiniLM-L6-v2"
        embeddings = embed_texts_sbert(texts, model=model)
        # Add to Chroma collection (or write backup if persistent backend unavailable)
        if not fallback_backup:
            collection.add(ids=list(batch_ids), documents=list(batch_docs), metadatas=list(batch_metas), embeddings=embeddings)
            total += len(batch_docs)
        else:
            # Write backup records to a JSONL file so vectors are not lost
            os.makedirs(chroma_persist_directory, exist_ok=True)
            bak_path = os.path.join(chroma_persist_directory, "embeddings_backup.jsonl")
            with open(bak_path, "a", encoding="utf-8") as bf:
                for _id, _doc, _meta, _emb in zip(batch_ids, batch_docs, batch_metas, embeddings):
                    bf.write(json.dumps({"id": _id, "document": _doc, "metadata": _meta, "embedding": _emb}, ensure_ascii=False) + "\n")
            total += len(batch_docs)
        # No explicit persist() required with PersistentClient; it manages on-disk state.
        # small sleep to avoid bursting API too fast in some environments
        time.sleep(0.01)

    return total, collection_name
