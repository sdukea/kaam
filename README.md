# Kaam

**Speak your skills. Get hired.**

India has hundreds of millions of informal workers (drivers, electricians, cooks,
security guards, domestic workers, tailors) and most have never had a resume.
Many can't write one. All of them can talk.

Kaam interviews a worker by voice, in their own language, and turns what they
say into a clean two-language resume and a shareable card with a voice
introduction that employers can listen to.

Built on [Gnani AI](https://www.gnani.ai) models:

- **Prisma v3.0** (speech-to-text): understands answers in Indian languages and code-mixed speech, even in noisy streets and kitchens
- **Timbre v3.0** (text-to-speech): asks the interview questions out loud in the worker's language and reads profiles to employers

## How it works

1. Pick a language. Kaam asks a few friendly questions out loud: name, work,
   experience, strengths, preferred area and pay, languages spoken.
2. The worker answers naturally. Prisma transcribes each answer live.
3. Kaam turns the answers into a structured resume in English and the worker's
   language, plus a shareable card with a QR code.
4. An employer opens the card and hears the worker's introduction.

## Status

Work in progress for the Great Indian AI Internship Challenge.

- [x] Live microphone → Prisma streaming transcription
- [x] Timbre TTS
- [x] Guided voice interview in Hindi, English, Tamil, Bengali and Marathi
- [ ] Resume generation from interview answers
- [ ] Shareable card with QR code
- [ ] Employer view with voice introduction

## Run it

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env        # then add your Gnani API key
uv sync
uv run uvicorn backend.main:app --reload --port 8000
```

Open http://localhost:8000.

### Command-line tools

```bash
# Stream a recorded answer (16-bit mono WAV, 8 or 16 kHz) and print transcripts
uv run python -m scripts.stream_file answer.wav --lang hi-IN

# Synthesize a line with Timbre
uv run python -m scripts.tts_say "नमस्ते! आपका नाम क्या है?" --lang hi-IN
```

## Architecture

```
Browser mic → AudioWorklet (16 kHz PCM16, 1,024-byte frames)
  → backend WebSocket proxy → Prisma streaming STT → live transcript
Interview questions → Timbre TTS (cached) → played in the browser
Answers (editable) → saved interview → resume + card (in progress)
```

The backend proxies audio because browsers can't set the headers Prisma needs,
and it keeps the API key off the client.

## Data and privacy

Demo profiles use actors and made-up details. Kaam asks for consent before
recording, does not store raw audio, and keeps phone numbers off public cards.
