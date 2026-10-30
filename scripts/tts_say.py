"""Synthesize a line with Timbre and save it as WAV.

    uv run python -m scripts.tts_say "नमस्ते! आपका नाम क्या है?" --lang hi-IN
"""

import argparse
import asyncio
import time
from pathlib import Path

from backend import tts


async def main(text: str, lang: str, voice: str | None, out: Path) -> None:
    start = time.monotonic()
    kwargs = {"voice": voice} if voice else {}
    audio = await tts.synthesize(text, lang, **kwargs)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(audio)
    print(f"Wrote {out} ({len(audio) / 1024:.0f} KB) in {time.monotonic() - start:.2f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("text")
    parser.add_argument("--lang", default="hi-IN")
    parser.add_argument("--voice", help="Timbre voice, e.g. Shivani, Avinash, Lakshmi (v3.0)")
    parser.add_argument("--out", type=Path, default=Path("out/tts.wav"))
    args = parser.parse_args()
    asyncio.run(main(args.text, args.lang, args.voice, args.out))
