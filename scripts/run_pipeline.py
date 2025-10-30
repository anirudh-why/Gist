"""End-to-end pipeline runner for Steps 1-3.

Usage example:
PYTHONPATH=./src python scripts/run_pipeline.py \
  --repo-url https://github.com/owner/repo \
  --out-raw data/raw_repo --chunks data/chunks_repo.jsonl \
  --chroma-dir ./chroma_db --collection repo_embeddings \
  --use-dummy-embeddings

By default the script will run local Sentence-Transformers embeddings.
If `--use-dummy-embeddings` is passed, the script will insert dummy vectors so you can
validate the pipeline without any ML dependencies.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Optional

# No environment variables are required for local embeddings.

from ingest import github_client, utils, chunker


def ingest_repo(repo_url: str, out_dir: str, token: Optional[str], max_size: int, include_exts: Optional[set]) -> int:
	print("\n--- STEP 1: Ingest repository ---")
	owner, repo = github_client.parse_github_url(repo_url)
	print(f"Owner: {owner}, Repo: {repo}")
	repo_info = github_client.get_repo_info(owner, repo, token=token)
	branch = repo_info.get("default_branch", "main")
	print("Default branch:", branch)

	tree = github_client.get_repo_tree(owner, repo, branch, token=token)
	print(f"Tree entries: {len(tree)}")

	# Use path_excludes if provided via CLI; default excludes are applied
	filtered = github_client.filter_paths(tree, include_exts=include_exts, max_file_size=max_size, path_excludes=ingest_repo._path_excludes if hasattr(ingest_repo, '_path_excludes') else None)
	print(f"Filtered files to fetch: {len(filtered)}")

	utils.ensure_dir(out_dir)
	fetched = 0
	for idx, entry in enumerate(filtered, start=1):
		path = entry.get("path")
		if not path:
			continue
		try:
			text, meta = github_client.fetch_file_text(owner, repo, branch, path, token=token)
			if path.lower().endswith('.ipynb'):
				text = github_client.extract_notebook_text(text)
			out_path = utils.repo_path_to_out_path(out_dir, path)
			utils.safe_write_text(out_path, text)
			fetched += 1
			print(f"[{idx}/{len(filtered)}] Saved: {path} -> {out_path} ({meta.get('fetched_via')})")
		except Exception as e:
			print(f"[{idx}/{len(filtered)}] Failed to fetch {path}: {e}")

	print(f"Ingestion complete: fetched {fetched} files to {out_dir}")
	return fetched


def chunk_files(in_dir: str, repo: str, chunks_out: str, chunk_size: int, overlap: int) -> int:
	print("\n--- STEP 2: Chunking & Preprocessing ---")
	start = time.time()
	count = chunker.chunk_folder(in_dir, repo, chunks_out, chunk_size_tokens=chunk_size, overlap_tokens=overlap)
	elapsed = time.time() - start
	print(f"Chunking complete: wrote {count} chunks to {chunks_out} in {elapsed:.1f}s")
	return count


def store_embeddings(chunks_jsonl: str, chroma_dir: str, collection: str, model: str, batch_size: int, use_dummy: bool) -> int:
	print("\n--- STEP 3: Embedding & Storage ---")
	# Lazy import to avoid requiring packages earlier
	try:
		from ingest import embeddings
		import chromadb
	except Exception as e:
		print("Missing dependencies for embeddings or Chroma:", e)
		print("Install chromadb and sentence-transformers, or use --use-dummy-embeddings.")
		raise

	if use_dummy:
		print("Using dummy embeddings (--use-dummy-embeddings set)")
		# Read chunks and insert dummy vectors into Chroma
		# Prefer the modern PersistentClient which writes to disk.
		fallback_backup = False
		try:
			client = chromadb.PersistentClient(path=chroma_dir)
			try:
				coll = client.create_collection(collection)
			except Exception:
				coll = client.get_collection(collection)
		except Exception as e:
			print("PersistentClient failed (", e, ") — falling back to in-memory + JSONL backup.")
			fallback_backup = True
			client = chromadb.Client()
			coll = client.create_collection(collection)

		cnt = 0
		with open(chunks_jsonl, 'r', encoding='utf-8') as f:
			for line in f:
				rec = line.strip()
				if not rec:
					continue
				obj = __import__('json').loads(rec)
				meta = obj.get('metadata', {})
				repo = meta.get('repo', '')
				file_path = meta.get('file_path', '')
				chunk_index = meta.get('chunk_index', 0)
				rid = f"{repo}::{file_path}::{chunk_index}"
				doc = obj.get('content','')
				# Dummy embedding length 8
				emb = [0.0]*8
				try:
					if not fallback_backup:
						coll.add(ids=[rid], documents=[doc], metadatas=[meta], embeddings=[emb])
					else:
						# Write a JSONL backup record containing the same data so it is
						# recoverable if the Chroma client cannot persist to disk.
						os.makedirs(chroma_dir, exist_ok=True)
						bak_path = os.path.join(chroma_dir, "embeddings_backup.jsonl")
						with open(bak_path, "a", encoding="utf-8") as bf:
							import json as _json
							_bak = {"id": rid, "document": doc, "metadata": meta, "embedding": emb}
							bf.write(_json.dumps(_bak, ensure_ascii=False) + "\n")
					cnt += 1
				except Exception as e:
					print('Failed to add dummy embedding for', rid, e)
		print(f"Inserted {cnt} dummy embeddings into Chroma collection '{collection}' at {chroma_dir}")
		return cnt

	# Otherwise use local Sentence-Transformers provider
	total, collname = embeddings.process_and_store(
		chunks_jsonl,
		chroma_persist_directory=chroma_dir,
		collection_name=collection,
		model=model,
		batch_size=batch_size,
		persist=True,
	)
	print(f"Inserted {total} embeddings into collection: {collname}")
	return total


def main(argv: Optional[list[str]] = None) -> int:
	parser = argparse.ArgumentParser(description="Run Steps 1-3 end-to-end for a GitHub repo")
	parser.add_argument('--repo-url', required=True, help='GitHub repo URL')
	parser.add_argument('--token', default=None, help='GitHub token (optional for private repos)')
	parser.add_argument('--out-raw', default='data/raw_auto', help='Directory to save raw files')
	parser.add_argument('--chunks', default='data/chunks_auto.jsonl', help='Output JSONL for chunks')
	parser.add_argument('--chroma-dir', default='./chroma_db', help='Chroma persist directory')
	parser.add_argument('--collection', default='repo_embeddings', help='Chroma collection name')
	parser.add_argument('--chunk-size', type=int, default=1000, help='Chunk size in tokens (approx)')
	parser.add_argument('--overlap', type=int, default=200, help='Chunk overlap in tokens (approx)')
	parser.add_argument('--model', default='sentence-transformers/all-MiniLM-L6-v2', help='Sentence-Transformers model name (e.g., sentence-transformers/all-MiniLM-L6-v2)')
	parser.add_argument('--batch-size', type=int, default=64, help='Embedding batch size')
	parser.add_argument('--max-size', type=int, default=1_000_000, help='Max file size in bytes to fetch')
	parser.add_argument('--use-dummy-embeddings', action='store_true', help='Insert dummy vectors instead of computing real embeddings')
	parser.add_argument('--extensions', default=None, help='Comma-separated extensions to include')
	parser.add_argument('--exclude-paths', default=None, help='Comma-separated path segments to exclude (e.g. node_modules,.cache)')
	args = parser.parse_args(argv)

	include_exts = None
	if args.extensions:
		include_exts = {e.strip().lower() for e in args.extensions.split(',') if e.strip()}

	# Parse exclude paths and attach to ingest_repo so filter_paths sees it
	if args.exclude_paths:
		exclude_set = {p.strip() for p in args.exclude_paths.split(',') if p.strip()}
		# attach as a private attr to the function to avoid changing many call sites
		ingest_repo._path_excludes = exclude_set
	else:
		ingest_repo._path_excludes = None

	# Step 1
	try:
		fetched = ingest_repo(args.repo_url, args.out_raw, args.token, args.max_size, include_exts)
	except Exception as e:
		print('Ingestion failed:', e)
		return 2

	if fetched == 0:
		print('No files fetched; aborting pipeline')
		return 3

	# Step 2
	chunks_count = chunk_files(args.out_raw, args.repo_url.replace('https://github.com/','').rstrip('/'), args.chunks, args.chunk_size, args.overlap)

	if chunks_count == 0:
		print('No chunks produced; aborting pipeline')
		return 4

	# Step 3
	try:
		emb_count = store_embeddings(args.chunks, args.chroma_dir, args.collection, args.model, args.batch_size, args.use_dummy_embeddings)
	except Exception as e:
		print('Embedding/storage failed:', e)
		return 5

	print('\nPipeline complete!')
	print(f'Files fetched: {fetched}, Chunks: {chunks_count}, Embeddings stored: {emb_count}')
	return 0


if __name__ == '__main__':
	raise SystemExit(main())

