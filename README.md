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
