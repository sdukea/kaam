import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


GNANI_API_KEY = _env("GNANI_API_KEY")

STT_URL = "wss://api.vachana.ai/stt/v3/stream"
STT_MODEL = _env("STT_MODEL", "prisma-v3.0")
STT_LANG = _env("STT_LANG", "indic-auto")
STT_SAMPLE_RATE = int(_env("STT_SAMPLE_RATE", "16000"))

# Prisma only emits a transcript once VAD closes a segment, so keep segments
# short: scam callers talk in long monologues and we can't wait for a pause.
STT_MIN_SILENCE_MS = _env("STT_MIN_SILENCE_MS", "300")
STT_MAX_SPEECH_S = _env("STT_MAX_SPEECH_S", "8.0")

# Words Prisma should listen harder for (Prisma v3.0 `x-keyterms` header, max 200).
STT_KEYTERMS = [
    "CBI", "police", "digital arrest", "arrest warrant", "OTP", "KYC",
    "customs", "parcel", "courier", "Aadhaar", "PAN", "AnyDesk",
    "TeamViewer", "UPI", "RBI", "safe account", "money laundering",
]

TTS_URL = "https://api.vachana.ai/api/v1/tts/inference"
TTS_MODEL = _env("TTS_MODEL", "timbre-v2.5")
TTS_VOICE = _env("TTS_VOICE", "Nalini")


def require_key() -> str:
    if not GNANI_API_KEY:
        raise RuntimeError("GNANI_API_KEY is not set. Copy .env.example to .env and add your key.")
    return GNANI_API_KEY
