from __future__ import annotations

from typing import Any, Dict, Optional
import time as _time

from .prompt import build_system_prompt, format_user_prompt


def generate_with_openai_compatible(
    context_block: str,
    user_query: str,
    *,
    api_base: str,
    model: str,
    api_key: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 400,
    top_p: float = 0.9,
    extra_headers: Optional[Dict[str, str]] = None,
) -> str:
    """Call an OpenAI-compatible Chat Completions API.

    Works with local servers like LM Studio or self-hosted vLLM/Ollama (when exposing
    an OpenAI-compatible endpoint), as well as hosted providers with a key.
    """
    import json as _json
    import requests as _requests

    system_msg = build_system_prompt()
    user_msg = format_user_prompt(context_block, user_query)

    url = api_base.rstrip("/") + "/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "gist-rag/1.0 (+https://github.com/anirudh-why/Gist)",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if extra_headers:
        headers.update(extra_headers)

    payload: Dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
    }
    # Simple retry on transient failures (429, 5xx)
    attempts = 0
    backoff = 1.0
    while True:
        attempts += 1
        try:
            resp = _requests.post(url, headers=headers, json=payload, timeout=120)
            if resp.status_code in (429, 500, 502, 503, 504):
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:500]}")
            resp.raise_for_status()
            break
        except Exception as e:
            if attempts >= 3:
                # Include server error body to help diagnose endpoint/base/model issues
                try:
                    body = resp.text  # type: ignore[name-defined]
                except Exception:
                    body = str(e)
                raise RuntimeError(f"OpenAI-compatible request failed after {attempts} attempts: {e}\nURL: {url}\nResponse: {body}") from e
            _time.sleep(backoff)
            backoff *= 2
    data = resp.json()
    try:
        return (data["choices"][0]["message"]["content"] or "").strip()
    except Exception:
        # Fallback: return serialized response
        try:
            return _json.dumps(data, ensure_ascii=False)[:4000]
        except Exception:
            return str(data)
