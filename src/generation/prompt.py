from __future__ import annotations

from typing import Any, Dict, List

# Rough heuristic: ~4 characters per token
TOKEN_TO_CHAR = 4


def build_system_prompt() -> str:
    return (
        "You are a helpful assistant who explains codebases to students.\n"
        "Focus on clarity and simple language.\n"
        "Highlight key files, functions, and architecture decisions.\n"
        "If something is unclear from the context, say so and suggest where to look."
    )


def format_user_prompt(context_block: str, user_query: str) -> str:
    return (
        "Here is some context from a GitHub repository:\n"
        "<CONTEXT>\n" + context_block.strip() + "\n</CONTEXT>\n\n"
        "The student's question: " + user_query.strip() + "\n\n"
        "Please explain clearly what's going on, using simple language and pointing out key files,\n"
        "functions, and architecture as needed. If code is referenced, mention file paths."
    )


def allowed_context_chars(n_ctx: int, max_answer_tokens: int, prompt_overhead_tokens: int = 400) -> int:
    """Compute an approximate character budget for the retrieved context.

    We reserve some tokens for the system/user prompt and the model's answer.
    """
    ctx_tokens_for_context = max(256, n_ctx - max_answer_tokens - prompt_overhead_tokens)
    return max(1024, ctx_tokens_for_context * TOKEN_TO_CHAR)


def format_sources(results: List[Dict[str, Any]]) -> List[str]:
    """Create a deduplicated list of human-readable sources from retrieval results."""
    seen = set()
    out: List[str] = []
    for r in results:
        meta = (r.get("metadata") or {})
        repo = meta.get("repo", "")
        path = meta.get("file_path", "")
        label = f"{repo} :: {path}" if repo else path
        if label and label not in seen:
            seen.add(label)
            out.append(label)
    return out
