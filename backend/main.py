"""Kaam backend.

Proxies browser microphone audio to Prisma (browsers can't set the custom
headers Prisma needs, and this keeps the API key off the client) and relays
transcripts back. Also exposes Timbre TTS so the app can talk to the worker,
stores finished interviews, and turns them into shareable profile cards.
"""

import asyncio
import json
import logging
import re
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config, llm, questions, resume, tts
from .stt import FINAL_EVENTS, PrismaStream

log = logging.getLogger("kaam")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

app = FastAPI(title="Kaam")

AUDIO_CACHE = config.CACHE_DIR / "questions"
INTERVIEWS = config.DATA_DIR / "interviews"
PROFILES = config.DATA_DIR / "profiles"
FRONTEND = config.ROOT / "frontend"
ID_RE = re.compile(r"^[0-9a-f]{10}$")


_profile_requests: dict[str, deque] = defaultdict(deque)
_listen_sessions = 0


def _rate_limit(ip: str, limit: int, window_s: float = 3600) -> None:
    """In-memory sliding window; enough for a single-instance deployment."""
    now = time.monotonic()
    hits = _profile_requests[ip]
    while hits and now - hits[0] > window_s:
        hits.popleft()
    if len(hits) >= limit:
        raise HTTPException(status_code=429, detail="Too many resumes from this network. Try again later.")
    hits.append(now)


def _load(directory, item_id: str) -> dict:
    path = directory / f"{item_id}.json"
    if not ID_RE.match(item_id) or not path.exists():
        raise HTTPException(status_code=404, detail="Not found")
    return json.loads(path.read_text())


def _check_lang(lang: str) -> None:
    if lang not in questions.LANGUAGES:
        raise HTTPException(status_code=404, detail=f"Unsupported language: {lang}")


@app.get("/api/health")
async def health():
    return {"ok": True, "key_configured": bool(config.GNANI_API_KEY)}


@app.get("/api/languages")
async def languages():
    return [{"code": code, **info} for code, info in questions.LANGUAGES.items()]


@app.get("/api/questions/{lang}")
async def interview_questions(lang: str):
    _check_lang(lang)
    return questions.questions_for(lang)


@app.get("/api/questions/{lang}/{index}/audio")
async def question_audio(lang: str, index: int):
    """Spoken question, synthesized once and cached on disk to save credits."""
    _check_lang(lang)
    qs = questions.questions_for(lang)
    if not 0 <= index < len(qs):
        raise HTTPException(status_code=404, detail="No such question")
    path = AUDIO_CACHE / f"{config.TTS_MODEL}-{config.TTS_VOICE}-{lang}-{qs[index]['id']}.wav"
    if not path.exists():
        try:
            audio = await tts.synthesize(qs[index]["text"], lang)
        except (tts.TTSError, RuntimeError) as e:
            raise HTTPException(status_code=502, detail=str(e))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(audio)
    return Response(content=path.read_bytes(), media_type="audio/wav")


class Answer(BaseModel):
    question_id: str = Field(max_length=40)
    question: str = Field(max_length=500)
    transcript: str = Field(max_length=4000)
    detected_languages: list[str] = Field(default=[], max_length=10)


class Interview(BaseModel):
    language: str
    consent: bool
    answers: list[Answer] = Field(min_length=1, max_length=len(questions.QUESTION_IDS))


@app.post("/api/interviews")
async def save_interview(interview: Interview):
    _check_lang(interview.language)
    if not interview.consent:
        raise HTTPException(status_code=400, detail="Consent is required")
    interview_id = uuid.uuid4().hex[:10]
    record = {
        "id": interview_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **interview.model_dump(),
    }
    INTERVIEWS.mkdir(parents=True, exist_ok=True)
    (INTERVIEWS / f"{interview_id}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2))
    return {"id": interview_id}


@app.post("/api/interviews/{interview_id}/profile")
async def create_profile(interview_id: str, request: Request):
    """Write the resume with the LLM and record spoken intros with Timbre."""
    interview = _load(INTERVIEWS, interview_id)
    if (PROFILES / f"{interview_id}.json").exists():
        return _load(PROFILES, interview_id)
    _rate_limit(request.client.host if request.client else "?", config.PROFILES_PER_IP_PER_HOUR)
    lang = interview["language"]
    try:
        profile = await resume.build_profile(interview)
    except llm.LLMError as e:
        raise HTTPException(status_code=502, detail=str(e))

    voice = {"male": config.TTS_VOICE_MALE, "female": config.TTS_VOICE_FEMALE}.get(
        profile["speaker_gender"], config.TTS_VOICE)
    intros = {"en": ("en-IN", profile["intro_en"])}
    if lang != "en-IN":
        intros["native"] = (lang, profile["intro_native"])
    PROFILES.mkdir(parents=True, exist_ok=True)

    async def record_intro(which: str, intro_lang: str, text: str) -> str | None:
        try:
            wav = await tts.synthesize(text, intro_lang, voice=voice)
        except (tts.TTSError, RuntimeError) as e:
            log.warning("Intro TTS failed (%s): %s", which, e)
            return None
        (PROFILES / f"{interview_id}-{which}.wav").write_bytes(wav)
        return f"/api/profiles/{interview_id}/audio/{which}"

    # Sequential: Timbre serves one request per account at a time.
    audio = {}
    for which, (intro_lang, text) in intros.items():
        if text and (url := await record_intro(which, intro_lang, text)):
            audio[which] = url

    record = {
        "id": interview_id,
        "language": lang,
        "language_name": questions.LANGUAGES[lang]["name"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "profile": profile,
        "audio": audio,
    }
    (PROFILES / f"{interview_id}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2))
    return record


@app.get("/api/profiles/{profile_id}")
async def get_profile(profile_id: str):
    return _load(PROFILES, profile_id)


@app.get("/api/profiles/{profile_id}/audio/{which}")
async def profile_audio(profile_id: str, which: str):
    path = PROFILES / f"{profile_id}-{which}.wav"
    if not ID_RE.match(profile_id) or which not in ("en", "native") or not path.exists():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(path, media_type="audio/wav")


@app.get("/p/{profile_id}")
async def profile_page(profile_id: str):
    return FileResponse(FRONTEND / "card.html")


@app.websocket("/ws/listen")
async def listen(browser: WebSocket, lang: str | None = None):
    """Browser sends PCM16 mono audio at STT_SAMPLE_RATE; we send back Prisma events.

    Text frames from the browser: "flush" sends trailing silence so Prisma
    finalizes the last segment, then replies {"type": "flushed"}.
    """
    global _listen_sessions
    await browser.accept()
    if _listen_sessions >= config.MAX_LISTEN_SESSIONS:
        await browser.send_json({"type": "error", "message": "Kaam is busy right now. Please try again in a minute."})
        await browser.close()
        return
    stt_lang = questions.stt_lang_for(lang) if lang in questions.LANGUAGES else config.STT_LANG
    try:
        prisma = PrismaStream(lang=stt_lang)
        await prisma.connect()
    except Exception as e:
        log.warning("Prisma connect failed: %s", e)
        await browser.send_json({"type": "error", "message": "Could not reach the speech service."})
        await browser.close()
        return
    _listen_sessions += 1

    async def browser_to_prisma():
        while True:
            msg = await browser.receive()
            if msg["type"] == "websocket.disconnect":
                return
            if msg.get("bytes"):
                await prisma.send_audio(msg["bytes"])
            elif msg.get("text") == "flush":
                await prisma.flush()
                await browser.send_json({"type": "flushed"})

    async def prisma_to_browser():
        async for event in prisma.events():
            if event.get("type") in FINAL_EVENTS:
                log.info("[%s] %s", event.get("detected_language_code", "?"), event.get("text"))
            await browser.send_json(event)

    tasks = [asyncio.create_task(browser_to_prisma()), asyncio.create_task(prisma_to_browser())]
    try:
        done, _ = await asyncio.wait(tasks, timeout=config.MAX_ANSWER_SECONDS, return_when=asyncio.FIRST_COMPLETED)
        if not done:
            await browser.send_json({"type": "error", "message": "That answer was very long, so listening stopped."})
            await browser.close()
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        _listen_sessions -= 1
        for t in tasks:
            t.cancel()
        await prisma.close()


app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
