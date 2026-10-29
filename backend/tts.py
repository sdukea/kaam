"""Gnani Timbre text-to-speech (REST)."""

import httpx

from . import config


class TTSError(RuntimeError):
    pass


async def synthesize(
    text: str,
    language: str = "hi-IN",
    voice: str = config.TTS_VOICE,
    model: str = config.TTS_MODEL,
    sample_rate: int = 24000,
) -> bytes:
    """Return WAV audio for `text`. Write numbers as words for best results."""
    payload = {
        "text": text,
        "voice": voice,
        "model": model,
        "language": language,
        "speed": 1.0,
        "audio_config": {
            "sample_rate": sample_rate,
            "num_channels": 1,
            "sample_width": 2,
            "encoding": "linear_pcm",
            "container": "wav",
        },
    }
    headers = {"X-API-Key-ID": config.require_key(), "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(config.TTS_URL, json=payload, headers=headers)
    if resp.status_code != 200:
        raise TTSError(f"TTS failed ({resp.status_code}): {resp.text[:300]}")
    return resp.content
