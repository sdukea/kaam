"""Stream a WAV file to Prisma in real time and print transcripts.

    uv run python -m scripts.stream_file answer.wav

The WAV must be 16-bit mono at 8 or 16 kHz. Convert anything else with:

    ffmpeg -i input.m4a -ac 1 -ar 16000 -sample_fmt s16 answer.wav
"""

import argparse
import asyncio
import time
import wave

from backend.stt import PrismaStream, stream_pcm_file


def read_wav(path: str) -> tuple[bytes, int]:
    with wave.open(path, "rb") as w:
        if w.getnchannels() != 1 or w.getsampwidth() != 2:
            raise SystemExit(f"{path}: need 16-bit mono WAV (see ffmpeg command in this file's docstring)")
        rate = w.getframerate()
        if rate not in (8000, 16000):
            raise SystemExit(f"{path}: sample rate {rate} Hz; resample to 16000 or 8000")
        return w.readframes(w.getnframes()), rate


async def main(path: str, lang: str | None) -> None:
    pcm, rate = read_wav(path)
    print(f"Streaming {len(pcm) / 2 / rate:.1f}s of audio at {rate} Hz…")
    kwargs = {"sample_rate": rate}
    if lang:
        kwargs["lang"] = lang

    async with PrismaStream(**kwargs) as stream:
        start = time.monotonic()

        async def printer():
            async for event in stream.events():
                kind = event.get("type")
                if kind == "transcript":
                    t = time.monotonic() - start
                    lang_code = event.get("detected_language_code", "")
                    print(f"[{t:6.1f}s] {lang_code:>6} | {event.get('text', '')}")
                elif kind == "error":
                    print(f"ERROR: {event.get('message')}")
                elif kind == "connected":
                    print(f"Connected: {event}")

        printer_task = asyncio.create_task(printer())
        await stream_pcm_file(stream, pcm)
        # Give Prisma a moment to return the last segment.
        await asyncio.sleep(3)
        printer_task.cancel()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("wav")
    parser.add_argument("--lang", help="e.g. hi-IN, ta-IN, 'hi-IN,en-IN' (default: STT_LANG from .env)")
    args = parser.parse_args()
    asyncio.run(main(args.wav, args.lang))
