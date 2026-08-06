"""Strict-schema model calls, cached to disk by (prompt, schema, model, run_tag).
A warm cache replays the whole analysis offline with no network calls; cache/ is
committed to the repo on purpose.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parent.parent
CACHE = BACKEND / "cache"
CACHE.mkdir(parents=True, exist_ok=True)

load_dotenv(BACKEND / ".env")


class NoAPIKey(Exception):
    """Raised on a cache miss when no API key is configured."""


def model_name() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4.1")


def api_key() -> str | None:
    return os.getenv("OPENAI_API_KEY")


def cache_stats() -> dict:
    files = list(CACHE.glob("*.json"))
    prompt = completion = 0
    for f in files:
        usage = json.loads(f.read_text()).get("usage", {})
        prompt += usage.get("prompt", 0)
        completion += usage.get("completion", 0)
    return {"entries": len(files), "prompt_tokens": prompt, "completion_tokens": completion}


def chat_json(system: str, user: str, schema: dict, schema_name: str,
              temperature: float = 0.0, run_tag: str = ""):
    """Return (parsed_response, "cache" | "api")."""
    key = hashlib.sha256(json.dumps(
        [system, user, schema, model_name(), temperature, run_tag],
        sort_keys=True).encode()).hexdigest()[:20]
    path = CACHE / f"{schema_name}_{key}.json"

    if path.exists():
        return json.loads(path.read_text())["parsed"], "cache"

    if not api_key():
        raise NoAPIKey(
            f"cache miss for {schema_name} and no OPENAI_API_KEY set. "
            f"Copy backend/.env.example to backend/.env, or run with the committed cache intact."
        )

    from openai import OpenAI
    resp = OpenAI(api_key=api_key()).chat.completions.create(
        model=model_name(), temperature=temperature,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format={"type": "json_schema",
                         "json_schema": {"name": schema_name, "strict": True, "schema": schema}},
    )
    raw = resp.choices[0].message.content
    parsed = json.loads(raw)
    path.write_text(json.dumps({
        "parsed": parsed, "raw": raw, "model": model_name(),
        "temperature": temperature, "run_tag": run_tag,
        "usage": {"prompt": resp.usage.prompt_tokens,
                  "completion": resp.usage.completion_tokens},
    }, indent=2))
    return parsed, "api"
