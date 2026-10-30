import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


GNANI_API_KEY = _env("GNANI_API_KEY")

# Storage. On a host, point DATA_DIR at a persistent volume so profile links
# (and the QR codes people have shared) survive restarts and redeploys.
DATA_DIR = Path(_env("DATA_DIR") or ROOT / "data")
CACHE_DIR = Path(_env("CACHE_DIR") or ROOT / "out" / "cache")

# Abuse limits for a public deployment: every request here spends Gnani
# credits or LLM tokens.
MAX_ANSWER_SECONDS = int(_env("MAX_ANSWER_SECONDS", "180"))
MAX_LISTEN_SESSIONS = int(_env("MAX_LISTEN_SESSIONS", "4"))
PROFILES_PER_IP_PER_HOUR = int(_env("PROFILES_PER_IP_PER_HOUR", "10"))

STT_URL = "wss://api.vachana.ai/stt/v3/stream"
STT_MODEL = _env("STT_MODEL", "prisma-v3.0")
STT_LANG = _env("STT_LANG", "indic-auto")
STT_SAMPLE_RATE = int(_env("STT_SAMPLE_RATE", "16000"))

# Prisma only emits a transcript once VAD closes a segment. People pause to
# think mid-answer, so allow a little silence, but cap segment length so text
# keeps appearing on screen while they talk.
STT_MIN_SILENCE_MS = _env("STT_MIN_SILENCE_MS", "500")
STT_MAX_SPEECH_S = _env("STT_MAX_SPEECH_S", "10.0")

# Partial transcripts (~every 450 ms while someone speaks). Undocumented, but
# Prisma v3.0 accepts the `x-partials` header and echoes `partials_enabled`.
STT_PARTIALS = _env("STT_PARTIALS", "true").lower() == "true"

# Words Prisma should listen harder for (Prisma v3.0 `x-keyterms` header, max 200).
STT_KEYTERMS = [
    "driver", "electrician", "plumber", "carpenter", "painter", "mason",
    "cook", "chef", "maid", "housekeeping", "nanny", "babysitter",
    "security guard", "watchman", "tailor", "mechanic", "AC repair",
    "delivery", "helper", "gardener", "beautician", "welder", "caretaker",
    "salary", "experience", "license", "two-wheeler", "four-wheeler",
]

TTS_URL = "https://api.vachana.ai/api/v1/tts/inference"
# Timbre v3.0 voices speak all 10 supported languages; v2.5 voices are per-language.
TTS_MODEL = _env("TTS_MODEL", "timbre-v3.0")
TTS_VOICE = _env("TTS_VOICE", "Shivani")
# Voice intros on profile cards match the worker's gender when it can be
# inferred from how they speak about themselves.
TTS_VOICE_MALE = _env("TTS_VOICE_MALE", "Avinash")
TTS_VOICE_FEMALE = _env("TTS_VOICE_FEMALE", "Shivani")

# Any OpenAI-compatible chat completions API (hosted, or self-hosted Evon).
LLM_BASE_URL = _env("LLM_BASE_URL")
LLM_API_KEY = _env("LLM_API_KEY")
LLM_MODEL = _env("LLM_MODEL")


def require_key() -> str:
    if not GNANI_API_KEY:
        raise RuntimeError("GNANI_API_KEY is not set. Copy .env.example to .env and add your key.")
    return GNANI_API_KEY
