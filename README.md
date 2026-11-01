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
- [x] Resume generation from interview answers
- [x] Shareable card with QR code, WhatsApp sharing and image download
- [x] Spoken introduction in the worker's language and in English
- [ ] Contact requests that keep the worker's number private
- [ ] Photo on the card

## Run it

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env        # then add your Gnani API key and LLM settings
uv sync
uv run uvicorn backend.main:app --reload --port 8000
```

Open http://localhost:8000.

The resume writer uses any OpenAI-compatible chat completions API. Set
`LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL` in `.env` (see `.env.example`).

### Command-line tools

```bash
# Stream a recorded answer (16-bit mono WAV, 8 or 16 kHz) and print transcripts
uv run python -m scripts.stream_file answer.wav --lang hi-IN

# Synthesize a line with Timbre
uv run python -m scripts.tts_say "नमस्ते! आपका नाम क्या है?" --lang hi-IN
```

## Deploy

The repo includes a `Dockerfile` and a Render Blueprint (`render.yaml`). It
runs on any container host with WebSocket support.

**Storage.** Profiles must outlive restarts, because people share card links
and QR codes. Either mount a persistent volume at `/data`, or set the `S3_*`
variables to use any S3-compatible bucket (Cloudflare R2, Backblaze B2, AWS S3).

### Render (free plan)

Free Render services wipe their disk on restart and sleep after 15 minutes
without traffic, so this setup uses a bucket for storage and an uptime monitor
to keep the service awake.

1. Create a bucket and an access key with read/write access to it.
2. In Render: **New → Blueprint**, pick this repository, and fill in the
   secrets it asks for (`GNANI_API_KEY`, `LLM_*`, `S3_*`).
3. Add an uptime monitor (e.g. UptimeRobot) that requests
   `https://<your-app>.onrender.com/api/health?deep=1` every 5 minutes. This
   keeps the service awake and emails you if storage, keys or the app fail.

The plain `/api/health` stays green when storage is down, so the host won't
restart-loop; `?deep=1` reports the real state for alerts.

**Limits.** Public deployments are protected by a few configurable limits:
at most 4 simultaneous interviews, 3 minutes per answer, and 10 new resumes
per network per hour. Rebuilding an existing profile returns the saved one.

## Architecture

```
Browser mic → AudioWorklet (16 kHz PCM16, 1,024-byte frames)
  → backend WebSocket proxy → Prisma streaming STT → live transcript
Interview questions → Timbre TTS (cached) → played in the browser
Answers (editable) → LLM → structured two-language profile
  → Timbre spoken intros (worker's language + English)
  → shareable card at /p/<id> with QR code
```

Timbre serves one request per account at a time, so the backend queues all
speech synthesis through a single lock and retries on rate limits.

The backend proxies audio because browsers can't set the headers Prisma needs,
and it keeps the API key off the client.

## Data and privacy

Demo profiles use actors and made-up details. Kaam asks for consent before
recording, does not store raw audio, and keeps phone numbers off public cards.
