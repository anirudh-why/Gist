# GitHub Repo Ingestor (Step 1)

This small Python package implements Step 1: Data Ingestion Layer (Fetching GitHub Repo).

What it does

- Parse a GitHub repository URL to owner/repo
- Fetch repo metadata and file tree (via GitHub REST API)
- Filter to text/code files (by extension and size)
- Download raw file contents (supports raw URL and API contents endpoint)
- Extract text from Jupyter notebooks (basic)
- Save results to disk as plain text files under `data/raw/`

Usage

Run the CLI script in `scripts/run_ingest.py`:

```bash
python scripts/run_ingest.py https://github.com/owner/repo --out data/raw --token YOUR_GITHUB_TOKEN
```

If the repo is public, `--token` is optional. For private repos, provide a token with repo access.

Files created

- `src/ingest/github_client.py` — main logic for fetching files
- `src/ingest/utils.py` — helper functions
- `scripts/run_ingest.py` — lightweight CLI

Requirements

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Step 5 — Generation Layer (Groq-only)

This project now uses Groq exclusively for generation through their OpenAI-compatible endpoint. Local GGUF models and other API backends have been removed from the default path to keep things simple and reliable.

Context trimming: the CLI approximates token budget using a 4 chars/token heuristic and trims retrieved chunks to fit `--n-ctx` minus `--max-tokens` for the answer.

Groq usage and best-practices
--------------------------------

- Groq Cloud requires an API key. Do NOT hard-code this key into your repository.
- Preferred workflow:
  1. Create a Groq API key in the Groq dashboard.
  2. Export it into your shell environment (recommended) instead of passing it on the command line:

```bash
export GROQ_API_KEY="gsk_..."
```

  3. Run the generation CLI and the code will prefer the `GROQ_API_KEY` env var if `--groq-key` is not provided:

```bash
PYTHONPATH=./src python scripts/run_generation.py \
  --chroma-dir ./chroma_db_handy \
  --collection handy_sbert \
  --query "How are settings stored and updated?" \
  --groq-model llama-3.1-8b-instant \
  --k 5 --max-tokens 400 --temperature 0.3 --show-sources
```

Notes:
- If you must pass the key on the command line (less secure), you can still use `--groq-key`, but avoid checking it into files or shell history.
- Add `GROQ_API_KEY` to your OS secret store or CI secret variables instead of a plaintext file.

Security reminder: never commit secrets, and rotate keys if they are exposed.

## Interactive end-to-end runner

Prefer entering details at runtime? Use the interactive script to orchestrate Steps 1–5 without long CLI flags.

Quick start (it will prompt you):

```bash
python scripts/run_interactive.py
```

What it supports
- Option 1: Ingest a new GitHub repo (Steps 1–3), then ask a question (Steps 4–5)
- Option 2: Use an existing Chroma collection and ask questions directly
- Backend: Groq (default and only path in the minimal workflow)

Tips
- For Groq, set GROQ_API_KEY in your environment or .env.
- For Hugging Face, set HF_TOKEN in your environment or .env.
- For OpenAI-compatible servers, you can provide base/model at prompt; OPENAI_API_KEY is read if present.
