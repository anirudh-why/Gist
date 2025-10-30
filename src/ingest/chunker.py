"""Preprocessing and chunking utilities for repository text files.

This module implements Step 2 of the pipeline: clean files, split them into
semantically useful chunks, and attach metadata so the chunks are ready for
embedding.

Design goals:
- Keep implementation dependency-free (no external NLP/tokenizer). Use a
  character-based approximation for tokens (1 token ~= 4 characters) which is
  sufficient for chunk sizing and overlap.
- Provide file-type aware splitting for common repo files: code, markdown,
  JSON/YAML/configs.
"""
from __future__ import annotations

import json
import os
import re
from typing import Dict, Iterable, List, Optional

from . import utils


# Approximate token -> char conversion (very rough): 1 token ~= 4 chars
TOKEN_TO_CHAR = 4


def normalize_text(text: str) -> str:
    """Normalize whitespace and line endings.

    Keep indentation (important for code) but collapse multiple blank lines.
    """
    if text is None:
        return ""
    # Normalize CRLF to LF
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Strip trailing spaces on each line but preserve indentation
    lines = [line.rstrip() for line in text.split("\n")]
    # Collapse runs of 3+ blank lines into 2
    out_lines = []
    blank_run = 0
    for line in lines:
        if line.strip() == "":
            blank_run += 1
        else:
            blank_run = 0
        if blank_run > 2:
            # keep at most two blank lines
            continue
        out_lines.append(line)
    return "\n".join(out_lines).strip()


def detect_file_type(path: str) -> str:
    """Return a simple file type string based on the path/extension."""
    ext = os.path.splitext(path)[1].lower()
    if ext in {".md", ".rst"}:
        return "markdown"
    if ext in {".py", ".js", ".ts", ".java", ".go", ".rb"}:
        return "code"
    if ext in {".json", ".yaml", ".yml", ".toml", ".ini"}:
        return "config"
    if ext == ".ipynb":
        return "notebook"
    # default fallback
    return "text"


def chunk_by_char(text: str, chunk_size_tokens: int = 1000, overlap_tokens: int = 200) -> List[str]:
    """Chunk text by character count using a token->char heuristic.

    Returns a list of text chunks with the requested overlap.
    """
    if not text:
        return []
    chunk_size = chunk_size_tokens * TOKEN_TO_CHAR
    overlap = overlap_tokens * TOKEN_TO_CHAR
    if chunk_size <= 0:
        raise ValueError("chunk_size_tokens must be positive")

    chunks: List[str] = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        if end >= text_len:
            break
        # advance start by chunk_size - overlap
        start = max(0, end - overlap)
    return [c.strip() for c in chunks if c.strip()]


def split_code_by_defs(text: str, lang: str = "python") -> List[str]:
    """Attempt to split code into logical blocks (functions/classes).

    This is heuristic-based and conservative: if no matches are found we
    fallback to a simple char-based chunking.
    """
    if not text:
        return []
    lines = text.split("\n")
    blocks: List[List[str]] = []
    current: List[str] = []

    # Choose a simple regex that matches common function/class starts for
    # the language family. Keep it conservative to avoid breaking code in the
    # middle of expressions.
    if lang == "python":
        starter_re = re.compile(r"^\s*(def |class )")
    else:
        # JS/TS/Java-like
        starter_re = re.compile(r"^\s*(function |class |const |let |var |export )")

    for line in lines:
        if starter_re.match(line) and current:
            # start of a new top-level block: push the current
            blocks.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append(current)

    # Convert blocks to text
    block_texts = ["\n".join(b).strip() for b in blocks if "\n".join(b).strip()]
    # If we only detected one giant block, fallback to char-based chunking
    if len(block_texts) <= 1:
        return chunk_by_char(text)
    return block_texts


def chunk_file(content: str, repo: str, file_path: str, *,
               chunk_size_tokens: int = 1000, overlap_tokens: int = 200) -> List[Dict]:
    """Process a single file's content and return list of chunk dicts.

    Each chunk dict has keys: 'content' and 'metadata' (repo, file_path, file_type, chunk_index)
    """
    text = normalize_text(content)
    file_type = detect_file_type(file_path)
    chunks: List[str] = []

    if file_type == "markdown":
        # Split by markdown headers first, then chunk each section
        parts = re.split(r"(?m)^#{1,6}\s+", text)
        # Simpler approach: chunk each part conservatively
        for part in parts:
            if part.strip():
                chunks.extend(chunk_by_char(part, chunk_size_tokens, overlap_tokens))
    elif file_type == "code":
        # Try to split by defs/classes heuristically
        ext = os.path.splitext(file_path)[1].lower()
        lang = "python" if ext == ".py" else "js"
        code_blocks = split_code_by_defs(text, lang=lang)
        for block in code_blocks:
            chunks.extend(chunk_by_char(block, chunk_size_tokens, overlap_tokens))
    elif file_type == "notebook":
        # Notebook content should already be pre-extracted to plain text by Step 1
        chunks = chunk_by_char(text, chunk_size_tokens, overlap_tokens)
    else:
        # text/config/other
        chunks = chunk_by_char(text, chunk_size_tokens, overlap_tokens)

    out: List[Dict] = []
    for i, chunk in enumerate(chunks):
        if not chunk.strip():
            continue
        meta = {
            "repo": repo,
            "file_path": file_path,
            "file_type": file_type,
            "chunk_index": i,
        }
        out.append({"content": chunk, "metadata": meta})
    return out


def chunk_folder(input_dir: str, repo: str, output_path: str, *,
                 chunk_size_tokens: int = 1000, overlap_tokens: int = 200) -> int:
    """Walk an input directory, chunk files, and write JSONL to output_path.

    Returns the number of chunks written.
    """
    count = 0
    utils.ensure_dir(os.path.dirname(output_path) or ".")
    with open(output_path, "w", encoding="utf-8") as out_f:
        for root, _, files in os.walk(input_dir):
            for fn in files:
                rel_dir = os.path.relpath(root, input_dir)
                rel_path = os.path.join(rel_dir, fn) if rel_dir != "." else fn
                src_path = os.path.join(root, fn)
                try:
                    with open(src_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                except Exception:
                    # Skip files we can't read as text
                    continue
                chunks = chunk_file(content, repo, rel_path, chunk_size_tokens=chunk_size_tokens, overlap_tokens=overlap_tokens)
                for chunk in chunks:
                    out_f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
                    count += 1
    return count
