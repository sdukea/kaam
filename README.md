# Kavach

A live scam-call shield for Indian languages. Put a call on speaker, and Kavach
listens, understands Hinglish and regional-language scam scripts as they unfold,
and warns you out loud before money changes hands.

Built on [Gnani AI](https://www.gnani.ai) models:

- **Prisma v3.0** (speech-to-text): real-time streaming transcription with automatic Indian-language detection
- **Timbre** (text-to-speech): spoken warnings in the caller's language

## Status

Work in progress for the Great Indian AI Internship Challenge.

- [x] Live microphone → Prisma streaming transcription in the browser
- [x] Timbre TTS endpoint and voice test
- [x] Synthetic call scripts for testing (`data/scripts/`)
- [ ] Scam detection engine
- [ ] Spoken warnings
- [ ] Family-voice warnings
- [ ] Post-call summary and reporting help

## Run it

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env        # then add your Gnani API key
uv sync
uv run uvicorn backend.main:app --reload --port 8000
```

Open http://localhost:8000, click **Start listening**, and speak (or play a call on speaker).

### Command-line tools

```bash
# Stream a recorded call (16-bit mono WAV, 8 or 16 kHz) and print transcripts
uv run python -m scripts.stream_file call.wav

# Synthesize a line with Timbre
uv run python -m scripts.tts_say "रुकिए! यह कॉल धोखा है।" --lang hi-IN
```

## How it works

```
Phone on speaker → browser mic → AudioWorklet (16 kHz PCM16, 1,024-byte frames)
  → backend WebSocket proxy → Prisma streaming STT
  → transcripts back to the browser
```

The backend proxies the audio because browsers can't set the headers Prisma
needs, and it keeps the API key off the client.

## Data and privacy

All test calls are staged with synthetic scripts. No real call recordings,
phone numbers, account numbers, Aadhaar or PAN data are used. Kavach does not
store audio.
