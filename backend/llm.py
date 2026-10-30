"""Minimal client for any OpenAI-compatible chat completions API.

Works with hosted providers and self-hosted servers (vLLM, Ollama, etc.),
including Gnani's open-weights Evon served behind an OpenAI-compatible
endpoint. Configure LLM_BASE_URL, LLM_API_KEY and LLM_MODEL in .env.
"""

import json
import re

import httpx

from . import config


class LLMError(RuntimeError):
    pass


async def complete_json(system: str, user: str, temperature: float = 0.2) -> dict:
    if not config.LLM_BASE_URL or not config.LLM_MODEL:
        raise LLMError("LLM is not configured. Set LLM_BASE_URL, LLM_API_KEY and LLM_MODEL in .env.")
    payload = {
        "model": config.LLM_MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }
    headers = {"Content-Type": "application/json"}
    if config.LLM_API_KEY:
        headers["Authorization"] = f"Bearer {config.LLM_API_KEY}"
    url = config.LLM_BASE_URL.rstrip("/") + "/chat/completions"
    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(url, json=payload, headers=headers)
    if resp.status_code != 200:
        raise LLMError(f"LLM request failed ({resp.status_code}): {resp.text[:300]}")
    try:
        content = resp.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as e:
        raise LLMError(f"Unexpected LLM response: {resp.text[:300]}") from e
    return _parse_json(content)


def _parse_json(text: str) -> dict:
    """Parse a JSON object, tolerating code fences or text around it."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    raise LLMError(f"LLM did not return JSON: {text[:300]}")
